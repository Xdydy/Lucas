from lucas import function,AbstractFunction,workflow,Workflow,create_handler

class CustomFunc(AbstractFunction):
    def func(self):
        print(self.fn)
        return self.fn()

@function(wrapper=CustomFunc)
def f():
    print("f")
    return 1

@workflow
def testF(wf:Workflow):
    return wf.call('f',{})

print(testF)