from lucas import function, Runtime, create_handler
import time
@function
def reducer(rt: Runtime):
    start_time = time.time()
    _input = rt.input()
    store = rt.storage
    word_counts = {}
    _file = None # final output file
    for k,v in _input.items():
        if not k.startswith('reducer'):
            continue
        _file = v
        word_count = store.get(v)
        for word in word_count:
            if word in word_counts:
                word_counts[word] += word_count[word]
            else:
                word_counts[word] = word_count[word]

    end_time = time.time()
    return rt.output({
        "time": end_time-start_time,
        'output': _file
    })

handler = create_handler(reducer)