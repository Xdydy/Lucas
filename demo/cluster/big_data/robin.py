import os
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from lucas.cluster.scheduler import RobinScheduler
context = Context.create_context()
scheduler = RobinScheduler()
context.set_scheduler(scheduler)

@function
def funca(a,b,c):
    _len = len(a)
    res = []
    for i in range(_len):
        res.append(a[i]+b[i]+c[i])
    return res

@function
def funcb(a,b,c):
    _len = len(a)
    res = []
    for i in range(_len):
        res.append(a[i]*b[i]*c[i])
    return res

@function
def add(a,b):
    _len = len(a)
    res = []
    for i in range(_len):
        res.append(a[i]+b[i])
    return res

@workflow(executor = ClusterExecutor)
def robin_workflow(wf: Workflow):
    ma = [1 for i in range(10000)]
    mb = [2 for i in range(10000)]
    mc = [3 for i in range(10000)]
    a = wf.call("funca", {"a": ma, "b": mb, "c": mc})
    b = wf.call("funcb", {"a": ma, "b": mb, "c": mc})
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
print(f"Execution time: {(end_t - start_t)} seconds")