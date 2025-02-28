from lucas import function, Runtime, create_handler

@function
def baseline(rt: Runtime):
    _input = rt.input()
    split_num = _input['split_num']
    data_file = _input.get('data_file', 'data.txt')

    finalresults = {}
    split_resp = rt.call('split', {'split_num': split_num, 'data_file': data_file})

    finalresults['split'] = split_resp['time']

    map_times = []
    mapper_outputs = []
    for i in range(split_num):
        result = rt.call('mapper', {'taskno': i, 'split': split_resp})
        mapper_outputs.append(result['output'])
        map_times.append(result['time'])

    finalresults['map'] = map_times

    reduce_times = []
    def solve(start, end):
        if start == end:
            return mapper_outputs[start]
        mid = (start + end) // 2
        result1 = solve(start, mid)
        result2 = solve(mid+1, end)
        result = rt.call('reducer', {'reducer_1': result1, 'reducer_2': result2})
        reduce_times.append(result['time'])
        return result['output']
        
    solve(0, split_num-1)
    finalresults['reduce'] = reduce_times

    return rt.output(finalresults)

handler = create_handler(baseline)