from tests.conftest import PythonInterpreterInitializedWithPath


class TestPackageProxy:

    def test_preconditions(self):

        with PythonInterpreterInitializedWithPath("testbed/client") as python:

            python.ok("import A, A.mod_A1")
            python.ok("from A.mod_A1 import aClass, aFunction")
            python.nok("from A.mod_A1 import aNonExistingSymbol")

            python.nok("import C")
            python.nok("import B.BB")
            python.nok("import B.mod_B1")

        with PythonInterpreterInitializedWithPath("testbed/server") as python:

            python.nok("import A")
            python.nok("import A.mod_A1")

            python.ok("import C, C.mod_C1, B.mod_B1, B.BB, B.BB.mod_BB1")

    def test_import_proxy(self, with_proxy_bootstrap):

        with PythonInterpreterInitializedWithPath("testbed/client", "src") as python:

            python.setenv_PACKAGE_PROXY_TARGET("C")

            # python.ok("import A")
            # python.nok("import B")
            # python.ok("import C")

            python.ok("import C.mod_C1")




