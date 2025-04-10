from lucas import workflow, function, Runtime, Workflow
@function
def funca(rt: Runtime):
    return rt.output(rt.input())

@function
def funcb(rt: Runtime):
    return rt.output(rt.input())

@workflow
def workflowfunc(wf: Workflow):
    _in = wf.input()
    
    a = wf.call('funca', {'a': _in['a']})
    b = wf.call('funcb', {'a': a['a']})
    return b

workflow_i = workflowfunc.generate()
dag = workflow_i.valicate()
import json
print(json.dumps(dag.metadata(fn_export=True),indent=2))
workflow_func = workflowfunc.export()
workflow_func({'a': 1})