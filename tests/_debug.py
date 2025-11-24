import textwrap

from tests.conftest import PythonInterpreterInitializedWithPath


class TestDebug:

    def test(self, with_proxy_bootstrap):

        with PythonInterpreterInitializedWithPath("testbed/client", "src", "tests") as python:

            python.setenv_PACKAGE_PROXY_TARGET("C")
            python.setenv_PACKAGE_PROXY_API_IMPL("_api.LocalApi")

            python._debug_imports(textwrap.dedent(f"""
            import C
            from pprint import PrettyPrinter
            pp = PrettyPrinter()
            pp.pprint(dir(C))
            pp.pprint(C.__dict__)
            import sys
            sys.stdout.flush()
            """))