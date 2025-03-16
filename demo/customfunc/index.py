from lucas import function, Runtime, Function

@function
def func(rt: Runtime):
    return rt.output(rt.input())

print(func.export()({"input": "Hello"}))

class MyFunction(Function):
    def _transformfunction(self, fn):
        return fn
    def onFunctionInit(self, fn):
        print("Function init")

@function(wrapper=MyFunction, provider='actor')
def funcb(data):
    return data

print(funcb.export()({"input": "Hello"}))