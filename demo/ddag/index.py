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

@function(
        provider="actor", 
        wrapper=ActorFunction,
        dependency=["tests/task/actor.py"],
        name="add3",
        venv="conda"
    )
def add3(a: int, b: int) -> int:
    return a * b

@workflow(executor=ActorExecutor, provider="actor")
def add_workflow(wf: Workflow):
    def sub_workflow(result):
        if result < 10:
            return wf.call("add2", {"a": result, "b": 10})
        else:
            return wf.call("add3", {"a": result, "b": 2})
    c = wf.call("add", {"a": 1, "b": 2})
    result = wf.func(sub_workflow, c)
    return result

wf_fn = add_workflow.export()
print(wf_fn({}))