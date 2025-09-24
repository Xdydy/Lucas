import cloudpickle

class A:
    def __call__(self, a):
        print(a)
        return a

a = A()
obj = cloudpickle.dumps(a)

b = cloudpickle.loads(obj)
b(1)