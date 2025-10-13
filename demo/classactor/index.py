import sys
sys.path.append("./protos")
sys.path.append("./utils")
from lucas import workflow, Workflow,actor
from lucas.serverless_function import Metadata
from lucas.utils.logging import log
from actor import ActorContext,ActorFunction,ActorExecutor,ActorRuntime,ActorRuntimeClass
import uuid

context = ActorContext.createContext()

@actor(wrapper=ActorRuntimeClass, dependency=['torch', 'numpy'], provider='actor', name='classA',venv='conda')
class A:
    def method(self, a):
        print(a)
        def generator() :
            for i in range(10):
                yield i
        return generator()

@actor(wrapper=ActorRuntimeClass, dependency=['torch', 'numpy'], provider='actor', name='classB',venv='conda')
class B:
    def method(self, stream):
        result = []
        for i in stream:
            result.append(i)
        return result

    



@workflow(executor=ActorExecutor)
def workflowfunc(wf: Workflow):
    _in = wf.input()
    in_a = A.export()
    in_b = B.export()
    a = wf.call_method(in_a, 'method', {'a': _in['a']})
    b = wf.call_method(in_b, 'method', {'stream': a})
    return b



workflow_i = workflowfunc.generate()
dag = workflow_i.valicate()
import json
print(json.dumps(dag.metadata(fn_export=True),indent=2))


def actorWorkflowExportFunc(dict: dict):

    # just use for local invoke
    from lucas import routeBuilder
    route = routeBuilder.build()
    route_dict = {}
    for function in route.functions:
        route_dict[function.name] = function.handler
    for workflow in route.workflows:
        route_dict[workflow.name] = workflow._generate_workflow
    for actor in route.actors:
        route_dict[actor.name] = actor._cls
    metadata = Metadata(
        id=str(uuid.uuid4()),
        params=dict,
        namespace=None,
        router=route_dict,
        request_type="invoke",
        redis_db=None,
        producer=None
    )
    rt = ActorRuntime(metadata)
    workflowfunc.set_runtime(rt)
    workflow = workflowfunc.generate()
    return workflow.execute()


workflow_func = workflowfunc.export(actorWorkflowExportFunc)
print("----first execute----")
workflow_func({'a': 1})
print("----second execute----")
workflow_func({'a': 2})