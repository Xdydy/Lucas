from lucas import workflow, function, Runtime, Workflow
@function
def funca(rt: Runtime):
    return rt.output(rt.input())

@function
def funcb(rt: Runtime):
    return rt.output(rt.input())

@workflow
def workflow(wf: Workflow):
    _in = wf.input()
    
    a = wf.call('funca', {'a': _in['a']})
    b = wf.call('funcb', {'a': a['a']})
    return b

workflow = workflow.export()
workflow({'a': 1})