import os
import time
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from lucas.cluster.scheduler import RobinScheduler

context = Context.create_context()
scheduler = RobinScheduler()
context.set_scheduler(scheduler)

@function
def func(x: int) -> int:
    return x + 1

dag_start_t = time.time()
@workflow(executor=ClusterExecutor)
def dag_workflow(wf: Workflow):
    result = 0
    for i in range(600):
        wf.call("func", {"x": i})
    return result

dag_end_t = time.time()
dag = dag_workflow.generate().valicate()
length = len(dag.get_nodes())
scheduler.analyze(dag)

workflow_start_t = time.time()
w_func = dag_workflow.export()
w_func()
workflow_end_t = time.time()

with open("dag.txt", "a") as f:
    f.write(f"{length-1} {dag_end_t - dag_start_t:.3f} {workflow_end_t - workflow_start_t:.3f}\n")

