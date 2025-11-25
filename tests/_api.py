from __future__ import annotations

import importlib
import sys
from importlib import util, machinery
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import Any

from package_proxy import api
from util import InspectDict


_server_mode = False


class ModuleNameMng:

    _REMOTE_PREFIX = "__remote__"

    def __init__(self, import_root: str, target_package_name: str) -> None:
        self._import_root = import_root
        self.real_package_root = target_package_name
        self.remote_package_root = self._REMOTE_PREFIX + self.real_package_root

    def get_real_and_remote_names(self, module_name: str) -> tuple[str, str]:

        if module_name.startswith(self._REMOTE_PREFIX):
            real_name = module_name[len(self._REMOTE_PREFIX):]
            remote_name = module_name
        else:
            real_name = module_name
            remote_name = self._REMOTE_PREFIX + real_name

        return real_name, remote_name

    def module_is_under_root_package(self, module_name: str) -> bool:
        real_name, _ = self.get_real_and_remote_names(module_name)
        return (real_name == self.real_package_root or
                real_name.startswith(self.real_package_root + "."))

    def get_module_path_incl_import_root(self, module_name) -> Path:
        return Path(self._import_root, *module_name.split("."))


class RemoteModuleFinder(importlib.abc.MetaPathFinder):

    def __init__(self, modname_mng: ModuleNameMng):
        super().__init__()
        self._modname_mng = modname_mng

    def find_spec(self, module_name, path, target=None):

        if not _server_mode:
            return None

        if not self._modname_mng.module_is_under_root_package(module_name):
            return None

        real_name, remote_name = self._modname_mng.get_real_and_remote_names(module_name)

        real_spec = self._get_real_spec(real_name)
        if real_spec is None:
            return None

        remote_spec = importlib.util.spec_from_loader(
            remote_name,
            RemoteLoader(real_spec, self._modname_mng),
            origin=real_spec.origin,
            is_package=real_spec.submodule_search_locations is not None
        )

        if getattr(remote_spec, "submodule_search_locations", None) in (None, []):
            remote_spec.submodule_search_locations = real_spec.submodule_search_locations

        return remote_spec

    def _get_real_spec(self, real_name: str) -> ModuleSpec:
        module_file = self._get_module_file(real_name)
        if not module_file: # namespace package
            return machinery.ModuleSpec(
                real_name,
                None,  # No loader for namespace packages
                is_package=True)
        else:
            spec = util.spec_from_file_location(real_name, module_file)
            return spec

    def _get_module_file(self, real_name: str) -> str | None:
        path = self._modname_mng.get_module_path_incl_import_root(real_name)
        py_path = path.with_suffix('.py')
        if py_path.is_file():
            return str(py_path)
        elif path.is_dir() and (path / "__init__.py").exists():
            return str(path / "__init__.py")
        else:
            return None # namespace package


class RemoteLoader(importlib.abc.Loader):

    def __init__(self, real_spec: ModuleSpec, modname_mng: ModuleNameMng):
        self._real_spec = real_spec
        self._modname_mng = modname_mng

    def create_module(self, remote_spec):

        assert self._modname_mng.module_is_under_root_package(remote_spec.name)

        if remote_spec.name in sys.modules:
            return sys.modules[remote_spec.name]

        module = ModuleType(remote_spec.name)
        module.__file__ = self._real_spec.origin
        module.__loader__ = self
        module.__spec__ = remote_spec
        if self._real_spec.submodule_search_locations:
            module.__path__ = self._real_spec.submodule_search_locations
            module.__package__ = self._real_spec.name
        else:
            module.__package__ = ".".join(self._real_spec.name.split(".")[:-1]) or None

        return module

    def exec_module(self, module):

        if self._real_spec.loader is None:
            # Namespace package - nothing to execute
            return

        with open(self._real_spec.loader.path, 'r') as f:
            source = f.read()
        code = compile(source, self._real_spec.origin, 'exec')
        self._exec_with_instrumented_sys_modules(module, lambda _: exec(code, module.__dict__))

    def _exec_with_instrumented_sys_modules(self, module, fn):
        real_name = self._real_spec.name
        remote_name = module.__spec__.name
        backup_key = f"__module_loader_tmp_{remote_name}__"
        try:
            if real_name in sys.modules:
                sys.modules[backup_key] = sys.modules[real_name]
            sys.modules[real_name] = module

            fn(self)

        finally:
            if backup_key in sys.modules:
                sys.modules[real_name] = sys.modules.pop(backup_key)
            else:
                sys.modules[remote_name] = module
                sys.modules.pop(real_name, None)


class LocalApi(api.ProxyApi):

    def __init__(self, root_package: str):
        sys.modules = InspectDict("sys.modules", sys.modules)
        self._objects = InspectDict("server-dictionary")
        self._index = 0

        import_root_path = Path(__file__).resolve().parent.parent / "testbed" / "server"
        self._modname_mng = ModuleNameMng(str(import_root_path), root_package)
        sys.meta_path.insert(0, RemoteModuleFinder(self._modname_mng))

    def get_module(self, module_name) -> Any:
        assert self._modname_mng.module_is_under_root_package(module_name)

        _, remote_name = self._modname_mng.get_real_and_remote_names(module_name)
        module = self._import_module(remote_name)

        assert type(module.__loader__) is RemoteLoader

        self._index += 1
        self._objects[self._index] = module
        return self._index

    def get_attr(self, proxy_id, item):
        obj = self._objects[proxy_id]
        return getattr(obj, item)

    def set_attr(self, proxy_id, key, value):
        obj = self._objects[proxy_id]
        return setattr(obj, key, value)

    def create_object(self, parent_id: int, cls_name: str, *args: Any, **kwargs: Any) -> int:
        parent_obj = self._objects[parent_id]
        cls = getattr(parent_obj, cls_name)
        new_obj = cls(*args, **kwargs)
        self._index += 1
        self._objects[self._index] = new_obj
        return self._index

    def call(self, proxy_id: int, func_name: str, *args: Any, **kwargs: Any) -> Any:
        obj = self._objects[proxy_id]
        return getattr(obj, func_name)(*args, **kwargs)

    @staticmethod
    def _import_module(remote_name: str) -> ModuleType:
        global _server_mode
        _server_mode = True
        try:
            return importlib.import_module(remote_name)
        finally:
            _server_mode = False
