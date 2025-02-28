from lucas import function, create_handler, Runtime

@function
def fibonacci(rt: Runtime):
    _in = rt.input()
    n = _in['n']
    if n <= 1:
        return n
    else:
        return rt.call('fibonacci', {'n': n-1}) + rt.call('fibonacci', {'n': n-2})

handler = create_handler(fibonacci)