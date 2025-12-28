from lucas import workflow, function, Workflow, actor
from lucas.serverless_function import Metadata
from lucas.train.trainer import ParameterServer
from lucas.actorc.actor import (
    ActorContext,
    ActorFunction,
    ActorExecutor,
    ActorRuntime,
    ActorRuntimeClass
)
import uuid
import sys

import time
import torch
import torch.nn as nn
import torch.optim as optim

context = ActorContext.createContext("localhost:50051")

data = []
for i in range(100):
    x = torch.randn(10).tolist()
    y = [sum(x) + torch.randn(1).item() * 0.1]  # 添加一些噪声
    data.append((x, y))


# 定义一个简单的线性模型
class LinearModel(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(LinearModel, self).__init__()
        self.linear = nn.Linear(input_dim, output_dim)

    def forward(self, x):
        return self.linear(x)



@actor(
    wrapper=ActorRuntimeClass,
    dependency=[],
    provider="actor",
    name="Train",
    venv="test2",
)
class Train:
    def __init__(self):
        self.model = LinearModel(10, 1)
        self.criterion = nn.MSELoss()
        self.optimizer = optim.SGD(self.model.parameters(), lr=0.01)


        
    def train_func(self, dataset):
        """
        接收数据集并进行训练，返回训练损失。这是分布式训练中的其中一个worker，计算一小部分参数，然后由PS聚合。
        """
        # 训练函数，返回模型参数和本地准确率
        self.model.train()
        total_loss = 0.0
        for x, y in dataset:
            inputs = torch.tensor(x, dtype=torch.float32)
            targets = torch.tensor(y, dtype=torch.float32)

            self.optimizer.zero_grad()
            outputs = self.model(inputs)
            loss = self.criterion(outputs, targets)
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()
        avg_loss = total_loss
        return {"loss": avg_loss, "gradients": {name: param.grad.tolist() for name, param in self.model.named_parameters()}}
            
        
    
    # 根据梯度更新模型
    def update_model(self, gradients):
        """     
        接收梯度并更新模型参数。
        :param gradients: 字典，键为参数名称，值为对应的梯度张量。
        """
        with torch.no_grad():
            for name, param in self.model.named_parameters():
                if name in gradients:
                    param.grad = torch.tensor(gradients[name], dtype=torch.float32)
            self.optimizer.step()

# @function(
#     wrapper=ActorFunction,
#     dependency=[],
#     provider="actor",
#     name="train_func",
#     venv="test2",
# )
# def train_func(dataset):
#     # 训练函数，返回模型参数和本地准确率
#     model = compose.Pipeline(
#         preprocessing.StandardScaler(),
#         linear_model.LogisticRegression()
#     )
#     metric = metrics.Accuracy()
#     for x, y in dataset:
#         y_pred = model.predict_one(x)
#         model.learn_one(x, y)
#         metric.update(y, y_pred)
#     # 返回权重和本地 metric
#     # 注意：River pipeline 需取最后一步的 weights
#     weights = model[-1].weights if hasattr(model[-1], 'weights') else {}
#     return {"weights": dict(weights), "metric": metric.get()}

ps = ParameterServer(train_func=Train)
ps.set_function_wrapper(ActorFunction)
ps.set_provider("actor")
ps.load_data(data)
ps.set_worker_num(4)
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
result = ps_fn({})
print("Params from PS:", result)
