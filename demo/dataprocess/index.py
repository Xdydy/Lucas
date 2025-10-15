import sys
sys.path.append("./protos")
sys.path.append("./utils")
from lucas import workflow, function, Workflow
from lucas.train.trainer import data_process
from lucas.serverless_function import Metadata
from lucas.utils.logging import log
from actor import ActorContext,ActorFunction,ActorExecutor,ActorRuntime
import uuid

context = ActorContext.createContext()


@data_process(
        num_workers=2,
        wrapper=ActorFunction, 
        dependency=['torch', 'numpy'], provider='actor', 
        name='process',
        venv='conda'
    )
def process(x):
    return x*2


@workflow(executor=ActorExecutor)
def workflowfunc(wf: Workflow):
    _in = wf.input()
    res = wf.call("process", {'x': _in['a']})
    return res



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
        route_dict[workflow.name] = function.handler
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