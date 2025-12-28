import dill

def func():
    yield 1
    yield 2
    yield 3

serialized = dill.dumps(func)
deserialized = dill.loads(serialized)
for value in deserialized():
    print(value)