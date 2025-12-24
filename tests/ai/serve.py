from lucas import workflow, function, Workflow
from lucas.serverless_function import Metadata
from lucas.utils.logging import log
from lucas.actorc.actor import ActorContext,ActorFunction,ActorExecutor,ActorRuntime
from lucas.serve.serve import Serve
import uuid

context = ActorContext.createContext()

@function(wrapper=ActorFunction, dependency=['torch', 'numpy'], provider='actor', name='inference',venv='conda')
def inference(a):
    try:
        # 兼容 a 为 str 或 dict 的情况
        if isinstance(a, dict):
            text = a.get("text") or a.get("prompt") or a.get("a") or ""
        else:
            text = str(a)

        text = (text or "").strip()

        # 使用transformer下的模型进行推理
        from transformers import AutoTokenizer, AutoModelForCausalLM
        model_name = "gpt2"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        input_ids = tokenizer(text, return_tensors="pt").input_ids
        gen = model.generate(input_ids, max_length=min(128, input_ids.shape[-1] + 50), do_sample=True, top_k=50, top_p=0.95, num_return_sequences=1)
        out = tokenizer.decode(gen[0], skip_special_tokens=True)

        # 最后回显输入
        return {"text": text, "generated": out}
    except Exception as e:
        return {"error": str(e)}


@workflow(executor=ActorExecutor, provider='actor')
def workflow1(wf: Workflow):
    _in = wf.input()
    
    a = wf.call('inference', {'a': _in['a']})
    return a


serve = Serve()
serve.add_route("/w1", workflow1)
serve.serve(port=8081)
