import inspect
def funca(a:int,b:int=5):
    return a + b

sig = inspect.signature(funca)
for name , param in sig.parameters.items():
    print(name, param)
    