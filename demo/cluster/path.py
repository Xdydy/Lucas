import os
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from lucas.cluster.scheduler import PathScheduler
context = Context.create_context()
scheduler = PathScheduler()
context.set_scheduler(scheduler)

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
scheduler.analyze(dag)
w_func = robin_workflow.export()
import time
start_t = time.time()
for i in range(1000):
    result = w_func()
end_t = time.time()
print(result)
print(f"Execution time: {end_t - start_t} seconds")