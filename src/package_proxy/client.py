from __future__ import annotations

import builtins
import importlib.abc
import importlib.util
import os
import sys

from .api import ProxyApi


class ModuleFinder(importlib.abc.MetaPathFinder):
    def __init__(self, proxy_target):
        self._proxy_target = proxy_target
        self._proxy_api: ProxyApi | None = None

    def find_spec(self, fullname, path, target=None):
        if fullname == self._proxy_target or fullname.startswith(self._proxy_target + "."):
            if self._proxy_api is None:
                self._proxy_api = self._get_api_impl(self._proxy_target)
            spec = importlib.util.spec_from_loader(fullname,
                                                   ModuleLoader(fullname, self._proxy_api))
            return spec
        return None

    @staticmethod
    def _get_api_impl(proxy_target: str) -> ProxyApi:
        api_class_name = os.environ.get("PACKAGE_PROXY_API_IMPL")
        if api_class_name is None:
            raise ImportError(f"No proxy implementation class defined in PACKAGE_PROXY_API_IMPL")

        module_name, _, cls_name = api_class_name.rpartition('.')
        if module_name:
            api_module = __import__(module_name, fromlist=[cls_name])
            api_cls = getattr(api_module, cls_name, None)
        else:
            api_cls = globals().get(api_class_name)

        if api_cls is not None:
            return api_cls(proxy_target)
        else:
            raise ImportError(f"ProxyApi Implementation class {api_class_name!r} not found")


class ModuleLoader(importlib.abc.Loader):
    def __init__(self, fullname, api):
        self._fullname = fullname
        self._proxy_api = api

    def create_module(self, spec):
        proxy_id = self._proxy_api.get_module(self._fullname)
        proxy_mod = _ModuleProxy(self._fullname, self._proxy_api, proxy_id)
        return proxy_mod

    def exec_module(self, module):
        pass


class _ModuleProxy:

    def __init__(self, name: str, proxy_api: ProxyApi, proxy_id: str) -> None:
        object.__setattr__(self, "_proxy_api", proxy_api)
        object.__setattr__(self, "_proxy_id", proxy_id)
        object.__setattr__(self, "__name__", name)
        object.__setattr__(self, "__loader__", ModuleLoader)
        object.__setattr__(self, "__builtins__", builtins.__dict__)

    def __getattr__(self, item):

        if item in ['__spec__']:
            return None

        attr = self._proxy_api.get_attr(self._proxy_id, item)

        if isinstance(attr, type):
            proxy_cls = type(item, (), {
                "__module__": self.__name__,
                "__new__": lambda cls, *args, **kwargs : _Proxy(self._proxy_api, self._proxy_id, item, *args, **kwargs),
            })
            object.__setattr__(self, item, proxy_cls)
            return proxy_cls

        if callable(attr):
            _callable = lambda *args, **kwargs : self._proxy_api.call(self._proxy_id, item, *args, **kwargs)
            object.__setattr__(self, item, _callable)
            return _callable

        if item in ["__package__", "__path__"]:
            object.__setattr__(self, item, attr)

        return attr

    def __setattr__(self, key, value):
        object.__setattr__(self, key, value)

    def __getattribute__(self, name):
        # if name in ["__dict__"]:
        #     return self._proxy_api.get_attr(self.proxy_id, name)
        # else:
        return object.__getattribute__(self, name)


class _Proxy:

    def __new__(cls, proxy_api, parent_id, cls_name, *args, **kwargs):

        if not hasattr(cls, "_proxy_api"):
            cls._proxy_api = proxy_api
        instance = object.__new__(cls)

        proxy_id = proxy_api.create_object(parent_id, cls_name, *args, **kwargs)
        object.__setattr__(instance, "_proxy_id", proxy_id)

        return instance

    def __getattr__(self, item):
        attr = self._proxy_api.get_attr(self._proxy_id, item)

        if isinstance(attr, type):
            proxy_api = self._proxy_api
            cls_name = item
            proxy_cls = type(cls_name, (), {
                "__module__": self.__module__.__name__,
                "__new__": lambda cls_self, *args, **kwargs: _Proxy(proxy_api, cls_name, *args, **kwargs),
            })
            object.__setattr__(self.__class__, item, proxy_cls)
            return proxy_cls

        if callable(attr):
            func_name = item
            _callable = lambda *args, **kwargs : self._proxy_api.call(self._proxy_id, func_name, *args, **kwargs)
            object.__setattr__(self, func_name, _callable)
            return _callable

        return attr

    def __setattr__(self, key, value):
        self._proxy_api.set_attr(self._proxy_id, key, value)


target_package = os.environ.get("PACKAGE_PROXY_TARGET")
if not any(isinstance(f, ModuleFinder) for f in sys.meta_path):
    finder = ModuleFinder(proxy_target=target_package)
    sys.meta_path.insert(0, finder)
