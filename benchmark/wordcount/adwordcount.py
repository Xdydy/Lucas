from lucas import workflow, Workflow, create_handler
from lucas.workflow.executor import MulThreadExecutor
from lucas.utils.logging import log

@workflow(executor=MulThreadExecutor)
def wordcount(wf:Workflow):
    _in = wf.input()
    split_num = _in.get('split_num', 20)
    data_file = _in.get('data_file', 'data.txt')

    def split():
        split_resp = wf.call('split', {'split_num': split_num, 'data_file': data_file})
        return split_resp
    def mapper(pre):
        results = []
        for i in range(split_num):
            result = wf.call('mapper', {'taskno': i})
            results.append(result)
        return results
    def reducer(results):
        def solve(start, end):
            if start == end:
                return results[start]['output']
            mid = (start + end) // 2
            result1 = solve(start, mid)
            result2 = solve(mid+1, end)
            depend = {}
            depend['reducer_0'] = result1
            depend['reducer_1'] = result2
            result =  wf.call('reducer', {**depend})

            return result['output']
        return solve(0, split_num-1)

    split_resp = wf.func(split)
    map_resp = wf.func(mapper, split_resp)
    reduce_resp = wf.func(reducer, map_resp)


    return reduce_resp

handler = create_handler(wordcount)