from lucas import function, Runtime, create_handler

@function
def baseline(rt: Runtime):
    _input = rt.input()
    split_num = _input['split_num']
    data_file = _input.get('data_file', 'data.txt')

    finalresults = {}
    split_resp = rt.call('split', {'split_num': split_num, 'data_file': data_file})

    finalresults['split'] = split_resp['time']

    timeresults = {}
    for i in range(split_num):
        result = rt.call('mapper', {'taskno': i, 'split': split_resp})
        timeresults[f"mapper-{i}"] = result['time']

    finalresults['map'] = timeresults
    result = rt.call('reducer', {'split_num': split_num})
    finalresults['reduce'] = result['time']

    return rt.output(finalresults)

handler = create_handler(baseline)