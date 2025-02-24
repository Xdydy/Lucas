from lucas import function, Runtime, create_handler
import time

@function
def mapper(rt: Runtime):
    start_time = time.time()
    _input = rt.input()
    taskno = _input.get('taskno')
    store = rt.storage
    words_key = f'words_{taskno}'
    words = store.get(words_key)

    word_counts = {}
    for word in words:
        if word in word_counts:
            word_counts[word] += 1
        else:
            word_counts[word] = 1
    
    store.put(f'word_counts_{taskno}', word_counts)

    end_time = time.time()
    return rt.output({
        'task': taskno,
        'time': end_time - start_time
    })

handler = create_handler(mapper)