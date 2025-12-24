from lucas import actor
from lucas.actorc.actor import ActorContext, ActorRuntimeClass

ActorContext.createContext()

@actor(
    wrapper=ActorRuntimeClass,
    dependency = ['tests/actor/interface.py'],
    provider='actor',
    name="classA",
    venv='conda'
)
class A:
    def __init__(self):
        self.c = 3
    def methodA(self, a, b):
        self.c = a + b
        return a + b
    def methodB(self, a, b):
        return self.c

a = A.export()
result1 = a.remote("methodA", {"a": 2, "b": 3})
result2 = a.remote("methodB", {"a": 2, "b": 3})
print(f"result1: {result1}, result2: {result2}")