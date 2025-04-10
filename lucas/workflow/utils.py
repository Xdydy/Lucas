from lucas.runtime import Runtime

class InvokeFuntion:
    def __init__(self, frt: Runtime, caller_name: str):
        self.frt = frt
        self.caller_name = caller_name
    def __call__(self, event: dict):
        return self.frt.call(self.caller_name, event)

class LocalFunctionCall:
    def __init__(self, fn):
        self.fn = fn
    def __call__(self, event: dict):
        args = []
        kwargs = {}
        for i in range(len(event)):
            if i not in event:
                break
            args.append(event[i])
            event.pop(i)
        for key in event:
            kwargs[key] = event[key]
        return self.fn(*args, **kwargs)
    
def get_item_func(dir, key):
    return dir[key]
