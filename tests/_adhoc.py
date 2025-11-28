import os
import sys

os.environ["PKG_PROXY_API"]="package_proxy._local.api.LocalApi"
os.environ["PKG_PROXY_TARGET"]="C"
os.environ["PKG_PROXY_API_LOGLEVEL"]="DEBUG"

import package_proxy # normally done by the pth file...

from C.mod_C1 import *

# inner = C1_1.C1_1_inner()
c1 = C1_1()
c1.method1()

class D(C1_2):
    pass

d = D()
print(D)
print(d)
print(d.abstractmethod())

# import C.mod_C1
# from C.mod_C1 import C1_2
# import B.BB
# import C.CB.mod_CB1

# print(C1_2)
#
# a = C1_2()
# print(f"print(a) = {a.method1()}")
# print(a)
# a._msg = f" {a._msg} -> updated!"
# print(f"print(a) = {a.method1()}")
#
# print("-" * 100)
# vals = "\n".join(f"{k}: {repr(v)}" for k, v in sys.modules.items() if isinstance(k, str) and (
#                     any(k.startswith(p) for p in ("C", "mod_", "__remote__", "B"))))
# print(vals)
# print("-" * 100)
# #
# #
# from pprint import pprint
# #
# for mod in [
#     "C",
#     "C.mod_C1",
#     "C.mod_C2",
#     "C.CB.mod_CB1",
#     "C.CC",
#     "__remote__C",
#     "__remote__C.mod_C1",
#     "__remote__C.mod_C2",
#     "__remote__C.CB.mod_CB1",
#     "__remote__C.CC",
# ]:
#     print("*" * 100)
#     print(f"{mod}.__dict__ : ")
#     try:
#         pprint(sys.modules[mod].__dict__)
#     except KeyError:
#         pass
