from __future__ import annotations

import abc


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
        return base.__call__(cls)
        # return type(A).__call__(A, *args, **kwargs)

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

class AbstractClass(abc.ABC):

    def __new__(cls, *args, **kwargs):
        print(f"AbstractClass.__new__((cls={cls}, args={args}, kwargs={kwargs})")
        return object.__new__(cls)

    def __init__(self, *args, **kwargs):
        print(f"AbstractClass.__init__((self={self}, args={args}, kwargs={kwargs})")

    def __call__(self, *args, **kwargs):
        print(f"AbstractClass.__call__((self={self}, args={args}, kwargs={kwargs})")

    def __getattr__(self, attr):
        print(f"AbstractClass.__getattr__((self={self}, attr={attr})")

    def __getattribute__(self, item):
        print(f"AbstractClass.__getattribute__((self={self}, item={item})")
        return object.__getattribute__(self, item)

    @abc.abstractmethod
    def method_x(self):
        pass
    def method_y(self):
        print(f"{self} -> method Y called")

class A(AbstractClass):

    def method_x(self):
        print(f"{self} -> method X called")

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

print("*" * 200)
print("-> printing dictionary attr of AbstractClass")
print("\n".join([str(t) for t in AbstractClass.__dict__.items()]))

print("*" * 200)
print("-> printing all methods labeled as abstract in this class")
print("\n".join([m.__name__ for k,m in AbstractClass.__dict__.items() if callable(m) and getattr(m, "__isabstractmethod__", False)]))
print("\n-> printing AbstractClass __mro__")
print(AbstractClass.__mro__)
print(f"\n-> printing AbstractClass __name__ attr")
print(AbstractClass.__name__)

print("*" * 200)
print("-> creating object of class A")
a = A()
print("*" * 200)
print(f"-> caling method from abstract class ")
a.method_y()

print("*" * 200)
print("-> printing dictionary attr of class A")
print("\n".join([str(t) for t in A.__dict__.items()]))

print("*" * 200)
print("-> printing all methods labeled as abstract in this class")
print("\n".join([m.__name__ for k,m in A.__dict__.items() if callable(m) and getattr(m, "__isabstractmethod__", False)]))
print("\n-> printing A __mro__")
print(A.__mro__)
print(f"\n-> printing A __name__ attr")
print(A.__name__)

print("*" * 200)
print(f"-> creating new class using a custom metatype : MyClassA = my_meta({type(A)})(f'MyA', (), ()')")
def __new(cls, *args, **kwargs):
    print(f"MyA.__new__((cls={cls}, args={args}, kwargs={kwargs})")
    return object.__new__(cls, *args, **kwargs),
MyA = my_meta(type(A))(f"My{A.__name__}", (A.__bases__), {
    "__new__" : __new,
    "method_x" : lambda _: print(f"My{A.__name__}.method_x")
})

print("*" * 200)
print("-> printing its dictionary attr")
print("\n".join([str(t) for t in MyA.__dict__.items()]))

print("*" * 200)
print("-> printing all methods labeled as abstract in this class")
print("\n".join([m.__name__ for k,m in MyA.__dict__.items() if callable(m) and getattr(m, "__isabstractmethod__", False)]))
print("\n-> printing new class __mro__")
print(MyA.__mro__)
print(f"\n-> printing new class __name__ attr")
print(MyA.__name__)

print("*" * 200)
print(f"-> creating object of new class ")
myClassA_obj = MyA()
print(type(myClassA_obj))

print("*" * 200)
print("-> printing its dictionary attr")
try:
    print("\n".join([str(t) for t in myClassA_obj.__dict__.items()]))
except AttributeError as e:
    print(str(e))

print("*" * 200)
print(f"-> calling locally overridden abstract method ")
try:
    myClassA_obj.method_x()
except AttributeError as e:
    print(str(e))

print("*" * 200)
print(f"-> calling method from abstract class ")
try:
    myClassA_obj.method_y()
except AttributeError as e:
    print(str(e))





