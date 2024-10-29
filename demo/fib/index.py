from lucas import function,workflow,create_handler,recursive
from lucas.workflow import Workflow


@workflow
def fib(wf:Workflow):
    _in = wf.getEvent()
    n = _in.get("n")
    def fn(n):
        if n <= 1:
            return n
        else:
            a = wf.call('fib', {'n': n-1})
            b = wf.call('fib', {'n': n-2})
            return a + b
    return n.becatch(wf).map(fn)

handler = create_handler(fib)