import B.BB.mod_BB1


class C1_1:

    _msg = "method 2 here!"
    _ext = B.BB.mod_BB1.BB1_C1()

    def method1(self) -> str:
        print(f"C1_1._ext = {self._ext}")
        print(f"C1_1._msg = {self._msg}")
        self._ext.method1()
        return self._msg
