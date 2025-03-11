from lucas import function, Runtime

@function
def funca(rt: Runtime):
    result = rt.tell("funcb", {"hello": "world"})
    return rt.output({"message": result})
@function
def funcb(rt: Runtime):
    return rt.output({"message": "ok"})