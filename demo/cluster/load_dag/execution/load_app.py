import os
import json
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from lucas.cluster.scheduler import RobinScheduler

context = Context.create_context()
scheduler = RobinScheduler()
context.set_scheduler(scheduler)

@workflow(executor = ClusterExecutor)
def robin_workflow(wf: Workflow):
    a = wf.call("funca", {"a": 1, "b": 2, "c": 3})
    b = wf.call("funcb", {"a": 1, "b": 2, "c": 3})
    c = wf.call("add", {"a": a, "b": b})
    return c

dag = robin_workflow.generate().valicate()
with open("dag.json", "r") as f:
    metadata = f.read()
    dag.loads(json.loads(metadata))

scheduler.analyze(dag)
func = robin_workflow.export()
func()