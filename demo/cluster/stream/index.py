import os
os.environ['provider'] = 'cluster'
from lucas import workflow, function, Workflow, actor
from lucas.serverless_function import Metadata
from lucas.cluster.client import (
    ClusterExecutor,
    Context
)
context = Context.create_context("localhost:50051")



@function
def data_generate(num: int):
    for i in range(num):
        yield i

@function
def stream_process(nums):
    result = 0
    for num in nums:
        result += num
    return result

@workflow(executor = ClusterExecutor)
def stream_workflow(wf: Workflow):
    data_t = wf.call("data_generate", {"num": 100})
    result = wf.call("stream_process", {"nums": data_t})
    return result

ps_fn = stream_workflow.export()
result = ps_fn({})
print("result: ", result)
