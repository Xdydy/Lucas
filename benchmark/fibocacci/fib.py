from lucas import workflow, Workflow, create_handler

@workflow
def fibonacci(wf: Workflow):
    _in = wf.input()
    n = _in['n']
    if n <= 1:
        return n
    else:
        return wf.call('fibonacci', {'n': n-1}) + wf.call('fibonacci', {'n': n-2})

handler = create_handler(fibonacci)