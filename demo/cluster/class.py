import os
os.environ["provider"] = "cluster"
from lucas import actor, workflow, Workflow
from lucas.cluster.client import ClusterExecutor
from lucas.cluster.client import Context

Context.create_context()

@actor
class A:
    def __init__(self):
        self.value = 0

    def add(self, x, y, z):
        self.value = x + y + z
        return self.value
    
    def get_value(self, val):
        return self.value
    
@workflow(executor = ClusterExecutor)
def workflow_define(wf: Workflow):
    a = A.export()
    res = wf.call_method(a, "add", {"x": 1, "y": 2, "z": 3})
    val = wf.call_method(a, "get_value", {"val": res})
    return val

w_func = workflow_define.export()
result = w_func()
print(result)