from lucas import function, workflow, Workflow
from lucas.actorc.actor import ActorFunction, ActorContext, ActorExecutor

ActorContext.createContext()

@function(
        provider="actor", 
        wrapper=ActorFunction,
        dependency=["tests/task/actor.py"],
        name="add",
        venv="conda"
    )
def add(a: int, b: int) -> int:
    return a + b

@function(
        provider="actor", 
        wrapper=ActorFunction,
        dependency=["tests/task/actor.py"],
        name="add2",
        venv="conda"
    )
def add2(a: int, b: int) -> int:
    return a + b


@workflow(executor=ActorExecutor, provider="actor")
def add_workflow(wf: Workflow):
    c = wf.call("add", {"a": 1, "b": 2})
    d = wf.call("add2", {"a": c, "b": 3})
    return d

wf_fn = add_workflow.export()
print(wf_fn({}))