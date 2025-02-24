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


    result = wf.call('reducer', {**dependency, 'split_num': split_num})

    return result['time']

handler = create_handler(wordcount)