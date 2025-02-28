from lucas import workflow, Workflow, create_handler
from lucas.workflow.executor import MulThreadExecutor

@workflow(executor=MulThreadExecutor)
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
        dependency[f'reducer_{i}'] = result


    def reducer(**kwargs):
        def solve(start, end):
            if start == end:
                return kwargs[f'reducer_{start}']['output']
            mid = (start + end) // 2
            result1 = solve(start, mid)
            result2 = solve(mid+1, end)
            depend = {}
            depend['reducer_0'] = result1
            depend['reducer_1'] = result2
            result =  wf.frt.call('reducer', {**depend})
            return result['output']
        return solve(0,split_num-1)
    result = wf.func(reducer, **dependency)


    return result

handler = create_handler(wordcount)