from lucas import Runtime,Workflow,workflow,function,durable,create_handler

@function
def workeradd(rt: Runtime):
    _input = rt.input()
    lhs = _input['lhs']
    rhs = _input['rhs']
    return rt.output({
        "result": lhs + rhs
    })

@durable
def durChain(rt: Runtime):
    r1 = rt.call('workeradd', {'lhs': 1, 'rhs': 2})
    r2 = rt.call('workeradd', {'lhs': r1['result'], 'rhs': 3})
    return rt.output(r2)

@workflow
def main(wf: Workflow):
    r = wf.call('durChain', {})
    return r

handler = create_handler(main)