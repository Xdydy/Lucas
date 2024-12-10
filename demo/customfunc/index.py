from lucas import function,AbstractFunction

class CustomFunc(AbstractFunction):
    def func(self):
        print(self.fn)
        return self.fn()

@function(wrapper=CustomFunc)
def f():
    print("f")
    return 1