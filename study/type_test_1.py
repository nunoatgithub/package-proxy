from __future__ import annotations

def my_meta(base: type):

    def __new(cls, *args, **kwargs):
        print(f"MyMeta.__new__((cls={cls}, args={args}, kwargs={kwargs})")
        return base.__new__(cls, *args, **kwargs)

    def __init_subclass(cls):
        print(f"MyMeta.__init_subclass__((cls={cls})")
        return base.__init_subclass__()

    def __init(self, *args, **kwargs):
        print(f"MyMeta.__init__((self={self}, args={args}, kwargs={kwargs})")
        return base.__init__(self, *args, **kwargs)

    def __call(cls, *args, **kwargs):
        print(f"MyMeta.__call__((cls={cls}, args={args}, kwargs={kwargs})")
        # return base.__call__(cls)
        return type(A).__call__(A, *args, **kwargs)

    def __getattr(self, attr):
        print (f"MyMeta.__getattr__((self={self}, attr={attr})")
        return base.__getattr__(base, attr)

    def __getattribute(cls, attr):
        print(f"MyMeta.__getattribute__((cls={cls}, attr={attr})")
        return base.__getattribute__(cls, attr)

    return type("MyMeta", (base,), {
        "__new__" : __new,
        "__init__" : __init,
        "__init_subclass__" : __init_subclass,
        "__call__" : __call,
        "__getattr__" : __getattr,
        "__getattribute__" : __getattribute,
    })

class A:

    def __new__(cls, *args, **kwargs):
        print(f"A.__new__((cls={cls}, args={args}, kwargs={kwargs})")
        return object.__new__(cls)

    def __init__(self, *args, **kwargs):
        print(f"A.__init__((self={self}, args={args}, kwargs={kwargs})")

    def __call__(self, *args, **kwargs):
        print(f"A.__call__((self={self}, args={args}, kwargs={kwargs})")

    def __getattr__(self, attr):
        print(f"A.__getattr__((self={self}, attr={attr})")

    def __getattribute__(self, item):
        print(f"A.__getattribute__((self={self}, item={item})")
        return object.__getattribute__(self, item)

    def method(self):
        print(f"{self} -> method called")

print("*" * 100)
print("-> creating object of class A")
a = A()

print("*" * 100)
print("-> printing dictionary attr of class A and its __mro__")
print("\n".join([str(t) for t in A.__dict__.items()]))
print("\n-> printing class __mro__")
print(A.__mro__)

print("*" * 100)
print("-> printing dictionary attr of class A")
print("\n".join([str(t) for t in A.__dict__.items()]))

print("*" * 100)
print("-> creating new class using a custom metatype : MyClassA = my_meta(type)(f'My{A.__name__}', (), {})")
def __new(cls, *args, **kwargs):
    print(f"MyA.__new__((cls={cls}, args={args}, kwargs={kwargs})")
    return object.__new__(cls, *args, **kwargs),
MyClassA = my_meta(type)(f"My{A.__name__}", (), {
    "__new__" : __new,
})

print("*" * 100)
print("-> printing its dictionary attr")
print("\n".join([str(t) for t in MyClassA.__dict__.items()]))
print("\n-> printing new class __mro__")
print(A.__mro__)
print(f"-> printing new class __name__ attr")
print(MyClassA.__name__)

print("*" * 100)
print(f"-> creating object of new class ")
myClassA_obj = MyClassA()
print(type(myClassA_obj))

