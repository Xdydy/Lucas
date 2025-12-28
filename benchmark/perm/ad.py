import os
import time
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from lucas.cluster.scheduler import RobinScheduler
from typing import Dict, Tuple

context = Context.create_context()
scheduler = RobinScheduler()
context.set_scheduler(scheduler)

@function
def func(siz: int):
    result = []
    expected = siz * 0.001
    for i in range(siz):
        result.append(i)
    time.sleep(expected)
    return result

@function
def add(a: list, b: list) -> list:
    result = []
    for x, y in zip(a, b):
        result.append(x + y)
    return result



@workflow(executor=ClusterExecutor)
def add_workflow(wf:Workflow):
    _in = wf.input()
    siz = _in['siz']
    a = wf.call("func", {"siz": siz})
    b = wf.call("func", {"siz": siz})
    c = wf.call("add", {"a": a, "b": b})
    return c

dag = add_workflow.generate().valicate()
scheduler.analyze(dag)
w_func = add_workflow.export()

payloads = [
    {"siz": 1000},
    {"siz": 2000},
    {"siz": 3000},
    {"siz": 4000},
]
out = []
for payload in payloads:
    start_t = time.time()
    result = w_func(payload)
    end_t = time.time()
    print(f"Payload: {payload}, Execution time: {end_t - start_t} seconds") 
    out.append((payload, end_t - start_t))

with open("ad.txt", "w") as f:
    for record in out:
        f.write(f"{record[0]} {record[1]}\n")