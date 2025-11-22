import cloudpickle
import sys
import pympler.asizeof as asizeof
class ComplexObject:
    def __init__(self, name):
        self.name = name
        self.data = list(range(1000))  # 大量数据
        self.children = []

a = ComplexObject("root")

print(asizeof.asizeof(cloudpickle.dumps(a)))
print(sys.getsizeof(cloudpickle.dumps(a)))
print(len(cloudpickle.dumps(a)))