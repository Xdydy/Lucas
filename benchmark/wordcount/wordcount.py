from lucas import workflow, Workflow, create_handler
from lucas.workflow import Lambda

@workflow
def wordcount(wf:Workflow):
    _in = wf.input()
    split_num = _in.get('split_num', 20)
    data_file = _in.get('data_file', 'data.txt')

    split_resp = wf.call('split', {'split_num': split_num, 'data_file': data_file})
    
    results = []
    for i in range(split_num):
        result = wf.call('mapper', {'taskno': i, 'split': split_resp})

        results.append(result)

    dependency = {}
    for i,result in enumerate(results):
        # timeresults[f"mapper-{i}"] = result['time']
        dependency[f'word_counts_words_{i}'] = result

    def get_time(*args):
        times = []
        for a in args:
            times.append(a['time'])
        return times
    mapper_times = wf.func(get_time, *results)

    result1 = wf.call('reducer', {**dependency, 'start': 0, 'end': split_num//2})
    result2 = wf.call('reducer', {**dependency, 'start': split_num//2, 'end': split_num})

    reduce_times = wf.func(get_time, result1, result2)

    def get_total_time(split_time, mapper_times, reduce_times):
        return {
            'split': split_time,
            'map': mapper_times,
            'reduce': reduce_times
        }
    
    final_result = wf.func(get_total_time, split_resp['time'], mapper_times, reduce_times)


    return final_result

handler = create_handler(wordcount)