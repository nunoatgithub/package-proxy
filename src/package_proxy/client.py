from __future__ import annotations

import abc
import builtins
import functools
import importlib.abc
import importlib.util
import os
import sys

from . import PACKAGE_PROXY_TARGET, PACKAGE_PROXY_API
from .api import ProxyApi


class ClientModuleFinder(importlib.abc.MetaPathFinder):
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
        api_class_name = os.environ.get(PACKAGE_PROXY_API)
        if api_class_name is None:
            raise ImportError(f"No proxy implementation class defined in {PACKAGE_PROXY_API}")

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

    def __init__(self, name: str, proxy_api: ProxyApi, proxy_id: int) -> None:
        object.__setattr__(self, "__name__", name)
        object.__setattr__(self, "__loader__", ModuleLoader)
        object.__setattr__(self, "__builtins__", builtins.__dict__)

        object.__setattr__(self, "_proxy_api", proxy_api)
        object.__setattr__(self, "_proxy_id", proxy_id)

        object.__setattr__(self, "_type_proxy_builder", TypeProxyBuilder(proxy_api, name))
        object.__setattr__(self, "_callable_proxy_builder", CallableProxyBuilder(proxy_api, proxy_id))

    def __getattr__(self, item):

        if item in ['__spec__']:
            return None

        # Handle __all__ for 'from module import *'
        if item == '__all__':
            try:
                api_attr = self._proxy_api.get_attr(self._proxy_id, item)
                return api_attr.attr
            except (AttributeError, KeyError):
                # Get the remote module's __dict__ and return public names
                api_attr = self._proxy_api.get_attr(self._proxy_id, '__dict__')
                module_dict = api_attr.attr
                return [name for name in module_dict.keys() if not name.startswith('_')]

        api_attr = self._proxy_api.get_attr(self._proxy_id, item)
        attr = api_attr.attr

        if isinstance(attr, type):
            type_proxy = self._type_proxy_builder.build_proxy_for_type_attr(api_attr)
            object.__setattr__(self, item, type_proxy)
            return type_proxy

        if callable(attr):
            _callable = self._callable_proxy_builder.build_for_attr(attr)
            object.__setattr__(self, item, _callable)
            return _callable

        if item in ["__package__", "__path__"]:
            object.__setattr__(self, item, attr)

        return attr

    def __setattr__(self, key, value):
        object.__setattr__(self, key, value)


class TypeProxyBuilder:

    def __init__(self, proxy_api: ProxyApi, module_name: str) -> None:
        self._proxy_api = proxy_api
        self._module_name = module_name

    def ProxyMeta(self, type_attr: ProxyApi.AttrWrapper, base: type) -> type:

        _type, _type_id = type_attr.attr, type_attr.proxy_id

        def _getattr(cls, attr_name):
            return self._get_attr_for_type(cls, _type_id, attr_name)

        def _call(cls, *args, **kwargs):
            return base.__call__(cls, *args, **kwargs)

        return type(
            f"ProxyMeta<{_type.__name__}>",
            (base,),
            {
                '__getattr__': _getattr,
                '__call__': _call
            }
        )

    def _build_object_proxy_template(self, type_attr: ProxyApi.AttrWrapper) -> tuple[str, tuple, dict]:

        _type, _type_id = type_attr.attr, type_attr.proxy_id

        object_proxy_name = f"ObjectProxy<{_type.__name__}>"

        object_proxy_bases = _type.__bases__

        object_proxy_dict = dict(ObjectProxy.__dict__)
        object_proxy_dict["_cls"] = _type
        object_proxy_dict["_cls_id"] = _type_id
        object_proxy_dict["__module__"] = self._module_name
        object_proxy_dict["_proxy_api"] = self._proxy_api

        return object_proxy_name, object_proxy_bases, object_proxy_dict

    def build_proxy_for_type_attr(self, type_attr: ProxyApi.AttrWrapper):

        object_proxy_template = self._build_object_proxy_template(type_attr)
        proxy_cls = self.ProxyMeta(type_attr, type(type_attr.attr))(*object_proxy_template)

        if issubclass(type_attr.attr, abc.ABC):
            # proxy_cls = self.ProxyMeta(type_attr, abc.ABCMeta)(*object_proxy_template)
            # Trying to set __abstractractmethods__ in the template itself does not work
            # ABCMeta cleans that up. So we need to set it here after ABC machinery returns
            try:
                abstract_methods = type.__getattribute__(type_attr.attr, "__abstractmethods__")
                type.__setattr__(proxy_cls, "__abstractmethods__", abstract_methods)
            except AttributeError:
                pass
        # else:
        #     proxy_cls = self.ProxyMeta(type_attr, type(type_attr.attr))(*object_proxy_template)

        return proxy_cls

    @staticmethod
    def _is_pybind_type(tp: type):
        meta = type(tp)
        return meta.__module__ == "pybind11_builtins" and meta.__name__ == "pybind11_type"

    def _get_attr_for_type(self, _type: type, _type_id: int, attr_name: str):

        api_attr: ProxyApi.AttrWrapper= self._proxy_api.get_attr(_type_id, attr_name)
        attr = api_attr.attr

        if isinstance(attr, type):
            type_proxy = self.build_proxy_for_type_attr(api_attr)
            type.__setattr__(_type, attr_name, type_proxy)
            return type_proxy

        if callable(attr):
            _callable = CallableProxyBuilder(self._proxy_api, _type_id).build_for_attr(attr)
            type.__setattr__(_type, attr_name, _callable)
            return _callable

        return attr


class CallableProxyBuilder:

    def __init__(self, proxy_api: ProxyApi, parent_id: int) -> None:
        self._proxy_api = proxy_api
        self._parent_id = parent_id

    def build_for_attr(self, callable_attr):

        proxy_api, parent_id = self._proxy_api, self._parent_id

        @functools.wraps(callable_attr)
        def _callable(*args, _func=callable_attr.__name__, **kwargs):
            return proxy_api.call(parent_id, _func, *args, **kwargs)

        # ABCMeta machinery needs this flag in callables to add them to __abstractmethods__
        # in subclasses. This needs to be made in addition to setting the __abstractmethods__
        # itself on the class returned by ABCMeta.
        try:
            flag = getattr(callable_attr, '__isabstractmethod__')
            object.__setattr__(_callable, "__isabstractmethod__", flag)
        except AttributeError:
            pass

        return _callable


class ObjectProxy:

    def __new__(cls, *args, **kwargs):
        proxy_id = None
        try:
            proxy_id = cls._proxy_api.create_object(cls._cls_id, *args, **kwargs)
        except TypeError:
            # TODO log this as signal of attempt to create types from outside the target package
            pass
        instance = cls._cls(*args, **kwargs)
        # object.__setattr__(instance, "__mro__", cls._cls.__mro__)
        object.__setattr__(instance, "_proxy_id", proxy_id)
        return instance

    def __getattr__(self, item):
        api_attr = self._proxy_api.get_attr(self._proxy_id, item)
        attr = api_attr.attr
        if callable(attr):
            _callable = CallableProxyBuilder(self._proxy_api, self._proxy_id).build_for_attr(attr)
            object.__setattr__(self, item, _callable)
            return _callable

        return attr

    @property
    def __dict__(self):
        api_attr = self._proxy_api.get_attr(self._proxy_id, "__dict__")
        return api_attr.attr

    def __setattr__(self, key, value):
        self._proxy_api.set_attr(self._proxy_id, key, value)


target_package = os.environ.get(PACKAGE_PROXY_TARGET)
if not any(isinstance(f, ClientModuleFinder) for f in sys.meta_path):
    finder = ClientModuleFinder(proxy_target=target_package)
    sys.meta_path.insert(0, finder)
