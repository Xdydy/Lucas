import os
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from lucas.cluster.scheduler import RobinScheduler
context = Context.create_context()
scheduler = RobinScheduler()
context.set_scheduler(scheduler)

@function
def funca(a):
    return a

@function
def funcb(a):
    result = []
    for i in range(a):
        result.append(i)
    return result

@function
def add(a,b):
    result = 0
    for i in b:
        result += i
    return a*result

@workflow(executor = ClusterExecutor)
def robin_workflow(wf: Workflow):
    b = wf.call("funcb", {"a": 100000})
    a = wf.call("funca", {"a": 3})
    c = wf.call("add", {"a": a, "b": b})
    return c

dag = robin_workflow.generate().valicate()
scheduler.analyze(dag)
w_func = robin_workflow.export()
import time
start_t = time.time()
result = w_func()
end_t = time.time()
print(result)
print(f"Execution time: {end_t - start_t} seconds")