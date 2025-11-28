from __future__ import annotations

import importlib
import logging
import os
import sys
import threading
from types import ModuleType
from typing import Any

from package_proxy import api, PACKAGE_PROXY_API_LOGLEVEL
from package_proxy.client import ClientModuleFinder
from .logger import InspectDict

_IMPORT_LOCK = threading.Lock()

loglevel = os.environ.get(PACKAGE_PROXY_API_LOGLEVEL, "ERROR")
level = getattr(logging, loglevel.upper(), logging.ERROR)
logging.basicConfig(level=level)

class ModuleImportTracker(importlib.abc.MetaPathFinder):

    _REMOTE_PREFIX = "__remote__"

    def __init__(self, target_package_name: str):
        super().__init__()
        self._target_package_name = target_package_name
        self._tracked_imports = set()

    def find_spec(self, module_name, path, target=None):
        if not _IMPORT_LOCK.locked():
            return None
        if self.under_root_package(module_name):
            self._tracked_imports.add(module_name)
        return None

    def move_tracked_imports_in_sys_modules(self) -> None:
        if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
            log_msg = "Moving tracked imports : \n" +'\n'.join(self._tracked_imports)
            logging.debug(log_msg)

        for name in self._tracked_imports:
            module = sys.modules.pop(name)
            sys.modules[self.get_remote_name_for(name)] = module
        self._tracked_imports.clear()

    def get_remote_name_for(self, module_name: str) -> str:
        return self._REMOTE_PREFIX + module_name

    def under_root_package(self, module_name: str) -> bool:
        return (module_name == self._target_package_name or
                module_name.startswith(self._target_package_name + "."))

class LocalApi(api.ProxyApi):

    def __init__(self, target_package: str):
        sys.modules = InspectDict("sys.modules", sys.modules)
        self._objects = InspectDict("server-dictionary")
        self._mod_tracker = ModuleImportTracker(target_package)
        self._index = -1

        assert isinstance(sys.meta_path[0], ClientModuleFinder)
        sys.meta_path.insert(1, self._mod_tracker)

    def get_module(self, module_name) -> int:
        assert self._mod_tracker.under_root_package(module_name)
        remote_name = self._mod_tracker.get_remote_name_for(module_name)
        module = sys.modules.get(remote_name)
        if not module:
            module = self._import_module(module_name)
        return self._add_object(module)

    def get_attr(self, proxy_id, item):
        obj = self._objects[proxy_id]
        if item == "__dict__":
            return obj.__dict__
        try:
            attr = getattr(obj, item)
            if isinstance(attr, type):
                proxy_id = self._add_object(attr)
                type.__setattr__(attr, "__proxy_id__", proxy_id)
            return attr
        except AttributeError:
            raise

    def set_attr(self, proxy_id, key, value):
        obj = self._objects[proxy_id]
        return setattr(obj, key, value)

    def create_object(self, cls_id: int, *args: Any, **kwargs: Any) -> int:
        cls = self._objects[cls_id]
        new_obj = cls(*args, **kwargs)
        return self._add_object(new_obj)

    def call(self, proxy_id: int, func_name: str, *args: Any, **kwargs: Any) -> Any:
        obj = self._objects[proxy_id]
        return getattr(obj, func_name)(*args, **kwargs)

    def _add_object(self, obj: Any) -> Any:
        self._index += 1
        self._objects[self._index] = obj
        return self._index

    def _import_module(self, name: str) -> ModuleType:
        """
        Removes the client module finder and allows the rest of the metapath chain do its job,
        while keeping record of all the imported modules that are relevant, by inserting itself
        as the first element in that chain in order to collect that info and forward the resolution
        to others.
        At the end, when the import machinery returns, uses that record to rename the key under
        which those modules are found in sys.module and puts the client module finder at the
        start of the chain.
        """
        with _IMPORT_LOCK :
            package_proxy_mod_finder = sys.meta_path.pop(0)
            assert isinstance(package_proxy_mod_finder, ClientModuleFinder)
            try:
                return importlib.import_module(name)
            finally:
                self._mod_tracker.move_tracked_imports_in_sys_modules()
                sys.meta_path.insert(0, package_proxy_mod_finder)
