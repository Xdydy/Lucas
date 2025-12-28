import os
import json
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from lucas.cluster.scheduler import RobinScheduler
import time

context = Context.create_context()

@workflow(executor = ClusterExecutor)
def robin_workflow(wf: Workflow):
    a = wf.call("funca", {"a": 1})
    a2 = wf.call("funca", {"a": 2})
    b = wf.call("funcb", {"a": a})
    c = wf.call("add", {"a": a2, "b": b})
    return c

dag = robin_workflow.generate().valicate()
with open("dag.json", "r") as f:
    metadata = f.read()
    dag.loads(json.loads(metadata))

start_t = time.time()
func = robin_workflow.export()
func()
end_t = time.time()
print("Total execution time:", end_t - start_t)