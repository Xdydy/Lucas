from lucas import function
from lucas.actorc.actor import ActorFunction, ActorContext

ActorContext.createContext()

@function(
        provider="actor", 
        wrapper=ActorFunction,
        dependency=["tests/task/actor.py"],
        name="add",
        venv="conda",
        cpu=1,
        memory=128
    )
def add(a: int, b: int) -> int:
    return a + b

add_fn = add.export()
result = add_fn({"a": 1, "b": 2})
print(result)