from lucas import workflow, function, Workflow
from lucas.serverless_function import Metadata
from lucas.train.trainer import ParameterServer
from lucas.actorc.actor import (
    ActorContext,
    ActorFunction,
    ActorExecutor,
    ActorRuntime,
)
import uuid
import sys

from river import datasets
from river import linear_model

from river import metrics

from river import compose
from river import preprocessing
from river import evaluate
import time

context = ActorContext.createContext("localhost:50051")


# todo: 模型对比



data = datasets.Phishing()

@function(
    wrapper=ActorFunction,
    dependency=[],
    provider="actor",
    name="evaluate_data",
    venv="test2",
)
def evaluate_data(dataset):
    time.sleep(2)
    model = compose.Pipeline(
        preprocessing.StandardScaler(), linear_model.LogisticRegression()
    )
    metric = metrics.ROCAUC()

    for data in dataset:
        x = data["x"]
        y = data["y"]
        print(x, y, file=sys.stderr)
        y_pred = model.predict_proba_one(x)
        model.learn_one(x, y)
        metric.update(y, y_pred)

    # evaluate.progressive_val_score(dataset, model, metric)
    return metric

ps = ParameterServer(evaluate_func=evaluate_data)
ps.set_function_wrapper(ActorFunction)
ps.set_provider("actor")
ps.load_data(data)
ps_wfcontext = ps.export(ActorExecutor)



# print(metric)




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
    ps_wfcontext.set_runtime(rt)
    workflow = ps_wfcontext.generate()
    return workflow.execute()


ps_fn = ps_wfcontext.export(actorWorkflowExportFunc)
ps_fn({})
