from lucas import workflow, function, Workflow
from lucas.serverless_function import Metadata
from lucas.utils.logging import log
from lucas.actorc.actor import ActorContext,ActorFunction,ActorExecutor,ActorRuntime
from lucas.serve.serve import Serve
import uuid

context = ActorContext.createContext()

@function(wrapper=ActorFunction, dependency=['torch', 'numpy'], provider='actor', name='funca',venv='conda')
def funca(a):
    print(a)
    def generator() :
        for i in range(10):
            yield i
    return generator()

@function(wrapper=ActorFunction, dependency=['torch', 'numpy'],provider='actor', name='funcb',venv='conda')
def funcb(stream):
    result = []
    for i in stream:
        result.append(i)
    return result



@workflow(executor=ActorExecutor, provider='actor')
def workflow1(wf: Workflow):
    _in = wf.input()
    
    a = wf.call('funca', {'a': _in['a']})
    b = wf.call('funcb', {'stream': a})
    return a


@workflow(executor=ActorExecutor, provider='actor')
def workflow2(wf: Workflow):
    _in = wf.input()
    
    a = wf.call('funca', {'a': _in['a']})
    b = wf.call('funcb', {'stream': a})
    return a

serve = Serve()
serve.add_route("/w1", workflow1)
serve.add_route("/w2", workflow2)
serve.serve(port=8081)
