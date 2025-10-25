from lucas import workflow, function, Workflow
from lucas.serverless_function import Metadata
from lucas.utils.logging import log
from lucas.actorc.actor import ActorContext,ActorFunction,ActorExecutor,ActorRuntime
import uuid

context = ActorContext.createContext()

@function(wrapper=ActorFunction, dependency=['torch', 'numpy'], provider='actor', name='funca',venv='conda')
def funca(a):
    print(a)
    def generator() :
        for i in range(10):
            yield i
    return generator()

@function(wrapper=ActorFunction, dependency=['torch', 'numpy'],provider='actor', name='funcb',venv='conda')
def funcb(stream):
    result = []
    for i in stream:
        result.append(i)
    return result



@workflow(executor=ActorExecutor, provider='actor')
def workflowfunc(wf: Workflow):
    _in = wf.input()
    
    a = wf.call('funca', {'a': _in['a']})
    b = wf.call('funcb', {'stream': a})
    return b



workflow_i = workflowfunc.generate()
dag = workflow_i.valicate()
import json
print(json.dumps(dag.metadata(fn_export=True),indent=2))




workflow_func = workflowfunc.export()
print("----first execute----")
workflow_func({'a': 1})
print("----second execute----")
workflow_func({'a': 2})