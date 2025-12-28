import sys
import time
from typing import Iterable
from lucas import workflow, function, Workflow
from lucas.serverless_function import Metadata
from lucas.train.trainer import TrainerPipeline, TrainerConfig
from lucas.actorc.actor import (
    ActorContext,
    ActorFunction,
    ActorExecutor,
    ActorRuntime,
)
import uuid
import cloudpickle
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

context = ActorContext.createContext("localhost:50051")

data_loader_config = TrainerConfig(
    wrapper=ActorFunction,
    dependency=[],
    provider="actor",
    name="read_data",
    venv="test2"
)
data_processer_config = TrainerConfig(
    wrapper=ActorFunction,
    dependency=[],
    provider="actor",
    name="process_data",
    venv="test2"
)
model_trainer_config = TrainerConfig(
    wrapper=ActorFunction,
    dependency=[],
    provider="actor",
    name="train",
    venv="test2"
)

def read_data(dataset: str, name: str):
    import os

    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    from datasets import load_dataset

    dataset = load_dataset(dataset, name)["train"]

    def generator():
        for i, x in enumerate(dataset):
            print(x)
            yield x
            if i > 100:
                return

    return generator()


def train(loader: Iterable[dict[str, str]]):
    """
    统一把每条记录转换为字符串文本输出的 generator。
    返回每条记录的 dict（含 text 字段），并清洗空行。
    """
    
    for x in loader:
        txt = x.get("text") or x.get("content") or x.get("article") or ""
        if not isinstance(txt, str):
            """使用 Hugging Face Transformers 对一个小型 causal language model（默认 distilgpt2）进行微调。

            该实现会把传入的 loader 中的文本收集为训练语料，构建 HF Dataset，tokenize，使用 Trainer 训练并保存模型到 `hf_llm_out/`。
            如果环境中没有安装 `transformers` / `datasets` / `torch`，函数会打印安装提示并返回错误信息字典。
            """

            # collect texts from loader
            texts = []
            for rec in loader:
                t = rec.get("text") or rec.get("content") or rec.get("article") or ""
                if not isinstance(t, str):
                    t = str(t)
                t = t.strip()
                if t:
                    texts.append(t)

            if len(texts) == 0:
                print("No training data found in loader", file=sys.stderr)
                return {"error": "no_data"}

            model_name = "distilgpt2"

            # create HF dataset
            ds = Dataset.from_dict({"text": texts})

            tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
            # distilgpt2 may not have pad token; set it if missing
            if tokenizer.pad_token is None:
                tokenizer.add_special_tokens({"pad_token": tokenizer.eos_token})

            def tokenize_function(examples):
                return tokenizer(examples["text"], truncation=True, max_length=128)

            tokenized = ds.map(tokenize_function, batched=True, remove_columns=["text"]) 

            # prepare model
            model = AutoModelForCausalLM.from_pretrained(model_name)
            model.resize_token_embeddings(len(tokenizer))

            data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

            training_args = TrainingArguments(
                output_dir="hf_llm_out",
                overwrite_output_dir=True,
                num_train_epochs=1,
                per_device_train_batch_size=4,
                save_steps=500,
                logging_steps=50,
                learning_rate=5e-5,
            )

            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=tokenized,
                data_collator=data_collator,
            )

            train_result = trainer.train()
            trainer.save_model("hf_llm_out")

            metrics = train_result.metrics if hasattr(train_result, "metrics") else {"trained_examples": len(texts)}
            print(f"HF training finished, trained_examples={len(texts)}", file=sys.stderr)
            return {"trained_examples": len(texts), "metrics": metrics}


trainer = TrainerPipeline(
    data_loader=read_data,
    model_trainer=train,
    data_loader_config=data_loader_config,
    model_trainer_config=model_trainer_config,
)




# workflow_i = workflowfunc.generate()
# dag = workflow_i.valicate()
# import json

# print(json.dumps(dag.metadata(fn_export=True), indent=2))
trainer = trainer.export(ActorExecutor)

def actorWorkflowExportFunc(dict: dict):

    # just use for local invoke
    from lucas import routeBuilder

    route = routeBuilder.build()
    route_dict = {}
    for function in route.functions:
        route_dict[function.name] = function.handler
    for workflow in route.workflows:
        route_dict[workflow.name] = function.handler
    metadata = Metadata(
        id=str(uuid.uuid4()),
        params=dict,
        namespace=None,
        router=route_dict,
        request_type="invoke",
        redis_db=None,
        producer=None,
    )
    rt = ActorRuntime(metadata)
    trainer.set_runtime(rt)
    workflow = trainer.generate()
    return workflow.execute()

trainer_fn = trainer.export(actorWorkflowExportFunc)
print("----first execute----")
trainer_fn({"dataset": "wikitext", "name": "wikitext-2-raw-v1"})

'''
model = ...
predict(model, text)
for i in range(batch_num):
    batch = read_data(i)
    model = train(model, batch)
predict(model, text)

'''
