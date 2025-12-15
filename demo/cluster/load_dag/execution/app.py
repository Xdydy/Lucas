import os
import json
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from lucas.cluster.scheduler import RobinScheduler
import random

context = Context.create_context()
scheduler = RobinScheduler()
context.set_scheduler(scheduler)

@function
def funca(a: int, b: int, c: int) -> int:
    return a + b + c

@function
def funcb(a: int, b: int, c: int) -> int:
    with open("k", "r") as f:
        flag = int(f.read().strip())
    if flag == 0:
        raise RuntimeError("Simulated function failure")
    return a * b * c

@function
def add(a: int, b: int) -> int:
    return a + b

@workflow(executor = ClusterExecutor)
def robin_workflow(wf: Workflow):
    a = wf.call("funca", {"a": 1, "b": 2, "c": 3})
    b = wf.call("funcb", {"a": 1, "b": 2, "c": 3})
    c = wf.call("add", {"a": a, "b": b})
    return c

dag = robin_workflow.generate().valicate()
scheduler.analyze(dag)
func = robin_workflow.export()
func()
