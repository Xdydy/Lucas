import os
import json
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from lucas.cluster.scheduler import RobinScheduler
import random
import time

context = Context.create_context()

@function
def funca(a) -> int:
    return a

@function
def funcb(a) -> int:
    with open("k", "r") as f:
        flag = int(f.read().strip())
    if flag == 0:
        raise RuntimeError("Simulated function failure")
    return a

@function
def add(a: int, b: int) -> int:
    return a + b

@workflow(executor = ClusterExecutor)
def robin_workflow(wf: Workflow):
    a = wf.call("funca", {"a": 1})
    a2 = wf.call("funca", {"a": 2})
    b = wf.call("funcb", {"a": a})
    c = wf.call("add", {"a": a2, "b": b})
    return c

func = robin_workflow.export()
start_t = time.time()
func()
end_t = time.time()
print("Total execution time:", end_t - start_t)
