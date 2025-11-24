import sys

# import C
# import C.mod_C1
from C.mod_C1 import C1_1
import C.CC

print("-" * 100)
vals = "\n".join(f"{k}: {repr(v)}" for k, v in sys.modules.items() if isinstance(k, str) and (
            k.startswith("C") or k.startswith("mod_") or k.startswith("__remote__")))
print(vals)
print("-" * 100)
from pprint import pprint

for mod in [
    "C",
    "C.mod_C1",
    "C.mod_C2",
    "C.CC",
    "__remote__C",
    "__remote__C.mod_C1",
    "__remote__C.mod_C2",
    "__remote__C.CC",
]:
    print("*" * 100)
    print(f"{mod}.__dict__ : ")
    pprint(sys.modules[mod].__dict__)
