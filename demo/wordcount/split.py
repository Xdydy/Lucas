from lucas import function,Runtime, create_handler
import re

@function
def split(rt: Runtime):
    _input = rt.input()
    text: str = _input["text"]
    words = re.split(r'[\s,\.]', text)

    return rt.output({
        'message': 'ok',
        'words': words
    })

handler = create_handler(split)