import os
import sys
from .finder import RemoteModuleFinder

target_package = os.environ.get("PACKAGE_PROXY_TARGET")
if target_package and not any(isinstance(f, RemoteModuleFinder) for f in sys.meta_path):
    finder = RemoteModuleFinder(proxy_target=target_package)
    sys.meta_path.insert(0, finder)