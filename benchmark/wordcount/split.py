from lucas import function,Runtime, create_handler
import re
import time
from lucas.utils.logging import log

@function
def split(rt: Runtime):
    start_time = time.time()
    _input = rt.input()
    split_num = _input.get('split_num', 3)
    data_file = _input.get('data_file', 'data.txt')
    store = rt.storage
    data = store.get(data_file)

    words = re.split(r'[\s,\.]', data)
    log.info(f"{len(words)} words in total")
    log.info(f"{type(words)}")

    words_keys = []

    for i in range(split_num):
        store.put(f'words_{i}', words[i*len(words)//split_num:(i+1)*len(words)//split_num])
        words_keys.append(f'words_{i}')

    end_time = time.time()

    return rt.output({
        'words_keys': words_keys,
        'time': end_time-start_time
    })

handler = create_handler(split)