from lucas import function, Runtime,create_handler

@function
def count(rt: Runtime):
    _input = rt.input()
    words = _input["words"]

    counter = {}
    for word in words:
        if word in counter:
            counter[word] += 1
        else:
            counter[word] = 1
    return rt.output({
        "counter": list(counter.items())
    })

handler = create_handler(count)