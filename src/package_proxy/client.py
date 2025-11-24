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
        proxy_mod = _ProxyModule(self._fullname, self._proxy_api, proxy_id)
        return proxy_mod

    def exec_module(self, module):
        pass


class _ProxyModule:

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
            proxy_cls = type(
                attr.__name__,
                (),
                {
                    "_proxy_api": self._proxy_api,
                    "__module__": self.__name__,
                    "__new__": lambda cls, *args, **kwargs: ProxyObject(cls._proxy_api,  cls._proxy_api.create_object(attr, *args, **kwargs)),
                    "__getattr__": lambda this, name: this._proxy_api.get_class_attr(attr, name),
                }
            )
            # Replace in this module so future access is fast
            object.__setattr__(self, attr.__name__, proxy_cls)
            return proxy_cls

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


class ProxyObject:

    def __init__(self, proxy_api: ProxyApi, proxy_id: str):
        self._proxy_api = proxy_api
        self._proxy_id = proxy_id

    def __getattr__(self, item):
        return self._proxy_api.get_attr(self._proxy_id, item)

target_package = os.environ.get("PACKAGE_PROXY_TARGET")
if not any(isinstance(f, ModuleFinder) for f in sys.meta_path):
    finder = ModuleFinder(proxy_target=target_package)
    sys.meta_path.insert(0, finder)
