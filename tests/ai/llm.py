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
            time.sleep(0.5)
            yield x
            if i > 100:
                return

    return generator()


def process_data(loader: Iterable[dict[str, str]]):
    def generator():
        for x in loader:
            if x["text"] == "":
                continue
            x["text"] = x["text"].strip()
            print("processed:", x["text"], file=sys.stderr)
            yield x

    return generator()


def train(loader: Iterable[dict[str, str]]):
    import sys

    param = 0
    for x in loader:
        print(x, file=sys.stderr)
        param += 1
    print(param, file=sys.stderr)

    return param


trainer = TrainerPipeline(
    data_loader=read_data,
    data_processer=process_data,
    model_trainer=train,
    data_loader_config=data_loader_config,
    data_processer_config=data_processer_config,
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
