from lucas import actor, workflow, Workflow
from lucas.actorc.actor import ActorContext, ActorRuntimeClass, ActorExecutor

ActorContext.createContext()

@actor(
    wrapper=ActorRuntimeClass,
    dependency = ['tests/actor/interface.py'],
    provider='actor',
    name="classA",
    venv='conda'
)
class A:
    def methodA(self, a, b):
        return a + b
    def methodB(self, a, b):
        return a * b


@workflow(executor=ActorExecutor, provider="actor")
def cls_workflow(wf: Workflow):
    a = A.export()
    result = wf.call_method(a, "methodA", {"a": 2, "b": 3})
    result = wf.call_method(a, "methodB", {"a": result, "b": 4})
    return result

wf_fn = cls_workflow.export()
result = wf_fn({})
print(f"Workflow result: {result}")