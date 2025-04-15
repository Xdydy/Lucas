class C:
    def func(self):
        raise NotImplementedError

class B(C):
    def func(self):
        return 1

class A:
    def __init__(self, b):
        self.b = b
    def func(self):
        return self.b.func()
    
b = C()
a = A(b)
b = B()
a.func()