from __future__ import annotations

import json
import logging
import os
import shutil
import site
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

logging.basicConfig(level=logging.INFO)


class PythonInterpreterInitializedWithPath:
    def __init__(self, *folder):
        self._python_path: list[str] = [os.path.join(_PROJECT_ROOT, f) for f in folder]
        self._package_proxy_target: str | None = None
        self._package_proxy_api_impl: str | None = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None

    def _launch(self, code: str) -> subprocess.Popen:

        env_dict = os.environ.copy()
        env_dict["PYTHONPATH"] = os.pathsep.join(self._python_path)
        # env_dict = {"PYTHONPATH": os.pathsep.join(self._python_path)}
        if self._package_proxy_target is not None:
            env_dict["PACKAGE_PROXY_TARGET"] = self._package_proxy_target
        if self._package_proxy_api_impl is not None:
            env_dict["PACKAGE_PROXY_API_IMPL"] = self._package_proxy_api_impl

        return subprocess.Popen(
            ["python3", "-c", code],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            env=env_dict,
            close_fds=True,
        )

    def _build_import_code_using(self, import_statement: str) -> str:
        return textwrap.dedent(f"""
        import sys
        for p in {self._python_path}:
            assert p in sys.path, f"Unexpected sys.path: {{sys.path}}"
        import json

        try:
            {import_statement}
            result = dict(imported=True)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            result = dict(imported=False, error=str(e), traceback=tb)
        print(json.dumps(result), flush=True)
        """)

    def _test_imports(self, import_statement: str, test_success: bool) -> None:

        code = self._build_import_code_using(import_statement)

        logging.debug(f"\n[proxy_target = {self._package_proxy_target}]\n{code}")
        stdout, stderr = self._launch(code).communicate()

        # Only fail if stderr contains a real Python error
        try:
            assert (not stderr
                    or stderr.startswith("Connected to: <socket")  # ignore debugger noise
                    or stderr.startswith(
                        "package_proxy successfully imported"))  # ignore boostrap messages
        except AssertionError as e:
            logging.error(stderr)
            raise

        assert stdout
        result = json.loads(stdout)

        if test_success:
            fail_msg = (f"Expected import to succeed for : {import_statement}, but got:\n "
                        f"{yaml.safe_dump(result, sort_keys=False, default_flow_style=False, )}")
            assert result["imported"], fail_msg
        else:
            assert not result["imported"], f"Expected import to fail for : {import_statement}"

    def nok(self, import_statement: str) -> None:
        self._test_imports(import_statement, test_success=False)

    def ok(self, import_statement: str) -> None:
        self._test_imports(import_statement, test_success=True)

    def setenv_PACKAGE_PROXY_TARGET(self, target: str) -> None:
        self._package_proxy_target = target

    def setenv_PACKAGE_PROXY_API_IMPL(self, api_impl_cls: str) -> None:
        self._package_proxy_api_impl = api_impl_cls

    def _debug_imports(self, code: str) -> None:
        logging.info(f"\n[proxy_target = {self._package_proxy_target}]\n{code}")
        stdout, stderr = self._launch(code).communicate()
        logging.info(f"STDOUT:\n{stdout}")
        logging.info(f"STDERR:\n{stderr}")


@pytest.fixture
def with_proxy_bootstrap():
    # Find the site-packages directory for the current environment
    site_dirs = site.getsitepackages() if hasattr(site, "getsitepackages") else [sys.prefix]
    site_dir = Path(site_dirs[0])

    # copy the bootstrap file there
    src = (_PROJECT_ROOT / "package_proxy_bootstrap.pth").resolve()
    pth_file = site_dir / src.name
    shutil.copy2(src, pth_file)
    try:
        yield pth_file
    finally:
        pass
        # delete the file
        if pth_file.exists():
            pth_file.unlink()
