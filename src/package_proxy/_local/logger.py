import inspect
import logging
import os

from package_proxy import PACKAGE_PROXY_API_LOGLEVEL

loglevel = os.environ.get(PACKAGE_PROXY_API_LOGLEVEL, "ERROR")
level = getattr(logging, loglevel.upper(), logging.ERROR)
logging.basicConfig(level=level)

class InspectDict(dict):

    ignore_contains = [
        "django.utils",
        "django",
        "django.forms",
        "django.utils.datastructures",
        "matplotlib",
        "matplotlib.pyplot",
        "multiprocessing",
        "numpy",
        "pprint",
        "pylab",
        "pydevd_asyncio_utils",
        "tensorflow",
        "torch",
        "warnings"
    ]

    def __init__(self, name, source=None, on_write=None):
        self._target = source if source is not None else {}
        self.logger = logging.getLogger(name)
        self._on_write = on_write if on_write is not None else \
            lambda action, key, value, mod=None, lineno=None: \
                self.logger.debug(f"[{mod}:{lineno}] {action} {key} {value} {type(value)}")

    def _notify(self, action, key=None, value=None, mod=None, lineno=None):
        if callable(self._on_write):
            try:
                # forward the captured module and line number to the callback
                self._on_write(action, key, value, mod=mod, lineno=lineno)
            except Exception:
                pass

    # Mapping Interface Methods

    def __getitem__(self, key):
        if key in self.ignore_contains:
            return self._target.__getitem__(key)
        def fn(mod=None, lineno=None):
            self._notify('__getitem__', key, None, mod, lineno)
            return self._target.__getitem__(key)
        return self._trace(fn)

    def __setitem__(self, key, value):
        def fn(mod=None, lineno=None):
            self._notify('__setitem__', key, value, mod, lineno)
            self._target.__setitem__(key, value)
        return self._trace(fn)

    def __delitem__(self, key):
        def fn(mod=None, lineno=None):
            self._notify('__delitem__', key, None, mod, lineno)
            self._target.__delitem__(key)
        return self._trace(fn)

    def __iter__(self):
        def fn(mod=None, lineno=None):
            self._notify('__iter__', None, None, mod, lineno)
            return self._target.__iter()
        return self._trace(fn)

    def __len__(self):
        def fn(mod=None, lineno=None):
            self._notify('__len__', None, None, mod, lineno)
            return self._target.__len__()
        return self._trace(fn)

    def __contains__(self, key):
        if key in self.ignore_contains:
            return self._target.__contains__(key)
        def fn(mod=None, lineno=None):
            self._notify('__contains__', key, None, mod, lineno)
            return self._target.__contains__(key)
        return self._trace(fn)

    def get(self, key, default=None):
        if key in self.ignore_contains:
            return self._target.get(key, default)
        def fn(mod=None, lineno=None):
            self._notify('get', key, default, mod, lineno)
            return self._target.get(key, default)
        return self._trace(fn)

    def items(self):
        return self._target.items()

    def keys(self):
        return self._target.keys()

    def values(self):
        return self._target.values()

    def setdefault(self, key, default=None):
        def fn(mod=None, lineno=None):
            self._notify('setdefault', key, default, mod, lineno)
            return self._target.setdefault(key, default)
        return self._trace(fn)

    def update(self, *args, **kwargs):
        def fn(mod=None, lineno=None):
            items = dict(*args, **kwargs)
            self._notify('update', None, items.items(), mod, lineno)
            self._target.update(items)
        return self._trace(fn)

    def pop(self, key, *args):
        def fn(mod=None, lineno=None):
            self._notify('pop', key, None, mod, lineno)
            return self._target.pop(key, *args)
        return self._trace(fn)

    def popitem(self):
        def fn(mod=None, lineno=None):
            self._notify('popitem', None, None, mod, lineno)
            return self._target.popitem()
        return self._trace(fn)

    def clear(self):
        def fn(mod=None, lineno=None):
            self._notify('clear', None, None, mod, lineno)
            self._target.clear()
        return self._trace(fn)

    def _trace(self, fn):
        frame = inspect.currentframe()
        try:
            # get the frame one level above the current caller (parent of caller)
            caller = frame.f_back.f_back if frame is not None and frame.f_back is not None else None
            mod = None
            lineno = None
            if caller is not None:
                # avoid inspect.getframeinfo() to prevent re-entering module dicts
                try:
                    mod = caller.f_globals.get('__name__', caller.f_code.co_filename)
                except Exception:
                    mod = getattr(caller.f_code, 'co_filename', None)
                lineno = getattr(caller, 'f_lineno', None)
            return fn(mod, lineno)
        finally:
            # break reference cycles
            del frame
            if 'caller' in locals():
                del caller