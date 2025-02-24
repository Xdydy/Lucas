from lucas import function, Runtime, create_handler
import time
@function
def reducer(rt: Runtime):
    start_time = time.time()
    _input = rt.input()
    split_num = _input.get('split_num')
    store = rt.storage
    word_counts = {}
    for i in range(split_num):
        key = f'word_counts_{i}'
        word_count = store.get(key)
        for word in word_count:
            if word in word_counts:
                word_counts[word] += word_count[word]
            else:
                word_counts[word] = word_count[word]

    end_time = time.time()
    return rt.output({"time": end_time-start_time})

handler = create_handler(reducer)