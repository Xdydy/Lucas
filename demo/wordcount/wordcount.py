from lucas import workflow, Workflow, create_handler

@workflow
def wordcount(wf:Workflow):
    _in = wf.getEvent()
    text: str = _in.get('text')
    
    # words = (await frt.call('split', {'text': text}))['words']
    words = wf.call('split', {'text': text})['words']


    def work(words):
        result = wf.call('count', {'words': words})
        return result['counter']
    def join(counter):
        result = wf.call('sort', {'counter': counter})
        return result['counter']
    
    result = words.fork(3).map(work).join(join)

    return result

handler = create_handler(wordcount)