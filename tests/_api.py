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

_remote_prefix = "__remote__"
_server_mode = False


class RemoteModuleFinder(importlib.abc.MetaPathFinder):

    def __init__(self, package_root_location: str):
        super().__init__()
        self._package_root_location = package_root_location

    def find_spec(self, module_name, path, target=None):

        if not _server_mode:
            return None

        if not module_name.startswith(_remote_prefix):
            remote_name = _remote_prefix + module_name
            real_name = module_name
        else:
            remote_name = module_name
            real_name = remote_name[len(_remote_prefix):]

        real_spec = self._get_real_spec(real_name)
        if real_spec is None:
            return None

        remote_spec = importlib.util.spec_from_loader(
            remote_name,
            RemoteLoader(real_spec),
            origin=real_spec.origin,
            is_package=real_spec.submodule_search_locations is not None
        )

        if getattr(remote_spec, "submodule_search_locations", None) in (None, []):
            remote_spec.submodule_search_locations = real_spec.submodule_search_locations

        return remote_spec

    def _get_real_spec(self, real_name: str) -> ModuleSpec:
        module_file = self._get_module_file(real_name)
        if not module_file:
            return machinery.ModuleSpec(
                real_name,
                None,  # No loader for namespace packages
                is_package=True)
        else:
            spec = util.spec_from_file_location(real_name, module_file)
            return spec

    def _get_module_file(self, real_name: str) -> str | None:
        path = Path(self._package_root_location, *real_name.split("."))
        py_path = path.with_suffix('.py')
        if py_path.is_file():
            return str(py_path)
        elif path.is_dir() and (path / "__init__.py").exists():
            return str(path / "__init__.py")
        else:
            return None


class RemoteLoader(importlib.abc.Loader):

    def __init__(self, real_spec):
        self.real_spec = real_spec

    def create_module(self, remote_spec):

        if remote_spec.name in sys.modules:
            return sys.modules[remote_spec.name]

        module = ModuleType(remote_spec.name)
        module.__file__ = self.real_spec.origin
        module.__loader__ = self
        module.__spec__ = remote_spec
        if self.real_spec.submodule_search_locations:
            module.__path__ = self.real_spec.submodule_search_locations
            module.__package__ = self.real_spec.name
        else:
            module.__package__ = ".".join(self.real_spec.name.split(".")[:-1]) or None
        return module

    def exec_module(self, module):

        if self.real_spec.loader is None:
            # Namespace package - nothing to execute
            return

        with open(self.real_spec.loader.path, 'r') as f:
            source = f.read()
        code = compile(source, self.real_spec.origin, 'exec')
        self._exec_with_fake_sys_modules(module, lambda _: exec(code, module.__dict__))

    def _exec_with_fake_sys_modules(self, module, exec_fn):
        real_name = self.real_spec.name
        remote_name = module.__spec__.name
        backup_key = f"__module_loader_tmp_{remote_name}__"
        try:
            if real_name in sys.modules:
                sys.modules[backup_key] = sys.modules[real_name]
            sys.modules[real_name] = module

            exec_fn(self)

        finally:
            if backup_key in sys.modules:
                sys.modules[real_name] = sys.modules.pop(backup_key)
            else:
                sys.modules[remote_name] = module
                sys.modules.pop(real_name, None)


class LocalApi(api.ProxyApi):
    _ROOT: str = str(Path(__file__).resolve().parent.parent / "testbed" / "server")

    def __init__(self, package_root: str):
        sys.modules = InspectDict("sys.modules", sys.modules)
        self._package_root = package_root
        self._objects = InspectDict("server-dictionary")
        self._index = 0
        sys.meta_path.insert(0, RemoteModuleFinder(self._ROOT))

    def get_module(self, fullname) -> Any:
        assert self._under_root_package(fullname)
        remote_name = _remote_prefix + fullname
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

    def create_object(self, cls: type, *args, **kwargs) -> int:
        new_obj = cls(*args, **kwargs)
        self._index += 1
        self._objects[self._index] = new_obj
        return self._index

    def _under_root_package(self, fullname: str) -> bool:
        return fullname == self._package_root or fullname.startswith(self._package_root + ".")

    @staticmethod
    def _import_module(remote_name: str) -> ModuleType:
        global _server_mode
        _server_mode = True
        try:
            return importlib.import_module(remote_name)
        finally:
            _server_mode = False
