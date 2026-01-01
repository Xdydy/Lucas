import os
import time
import json
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from lucas.cluster.scheduler import KeyPathScheduler

context = Context.create_context()
scheduler = KeyPathScheduler()
context.set_scheduler(scheduler)

matrix_size = 100
matrix_num = 4

@function
def generate(size: int = 32) -> bytes:
    return [i for i in range(size)]

@function
def merge(a: list, b: list) -> list:
    return a + b


@workflow(executor=ClusterExecutor)
def matrix_concat(wf:Workflow):
    results = []
    for i in range(matrix_num):
        matrix = wf.call("generate", {"size": matrix_size})
        results.append(matrix)
    for i in range(1, matrix_num):
        results[0] = wf.call("merge", {"a": results[0], "b": results[i]})
    return results[0]

dag = matrix_concat.generate().valicate()
scheduler.analyze(dag)
w_func = matrix_concat.export()

# payloads = [
#     (1000, 1000),
#     (2000, 1000),
#     (3000, 1000),
#     (4000, 1000),
#     (1000, 2000),
#     (2000, 2000),
#     (3000, 2000),
#     (4000, 2000),
# ]
with open("result.json", "r") as f:
    data = json.load(f)
    if 'path' not in data:
        data['path'] = {}
    start_t = time.time()
    result = w_func({})
    end_t = time.time()
    data['path'].update({
        f"{matrix_size}x{matrix_num}": end_t - start_t
    })

with open("result.json", "w") as f:
    json.dump(data, f, indent=2)
