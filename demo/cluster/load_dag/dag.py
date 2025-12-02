import os
import json
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from lucas.cluster.scheduler import RobinScheduler

@function
def funca(a,b,c):
    return a+b+c

@function
def funcb(a,b,c):
    return a*b*c

@function
def add(a,b):
    return a+b

@workflow(executor = ClusterExecutor)
def robin_workflow(wf: Workflow):
    a = wf.call("funca", {"a": 1, "b": 2, "c": 3})
    b = wf.call("funcb", {"a": 1, "b": 2, "c": 3})
    c = wf.call("add", {"a": a, "b": b})
    return c

dag = robin_workflow.generate().valicate()
with open("dag.json", 'w') as f:
    f.write(json.dumps(dag.metadata(),indent=2))

