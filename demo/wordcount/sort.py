from lucas import function, Runtime, create_handler

@function
def sort(rt: Runtime):
    _input = rt.input()
    counterArray = _input["counter"]

    counter = {}
    for arr in counterArray:
        if arr[0] not in counter:
            counter[arr[0]] = 0
        counter[arr[0]] += arr[1]

    reducedCounter = list(counter.items())
    reducedCounter.sort(key=lambda x: x[1], reverse=True)

    return rt.output({
        "counter": reducedCounter
    })

handler = create_handler(sort)