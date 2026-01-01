import os
os.environ['provider'] = 'cluster'
from lucas import workflow, function, Workflow, actor
from lucas.serverless_function import Metadata
from lucas.train.trainer import ParameterServer
from lucas.cluster.client import (
    ClusterActor,
    ClusterExecutor,
    Context
)
import uuid
import sys

import time
import torch
import torch.nn as nn
import torch.optim as optim

context = Context.create_context("localhost:50052")

data = []
for i in range(100):
    x = torch.randn(10).tolist()
    y = [sum(x) + torch.randn(1).item() * 0.1]  # 添加一些噪声
    data.append((x, y))

with open("data.txt", "w") as f:
    for x, y in data:
        f.write(f"{x}\t{y}\n")


# 定义一个简单的线性模型
class LinearModel(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(LinearModel, self).__init__()
        self.linear = nn.Linear(input_dim, output_dim)

    def forward(self, x):
        return self.linear(x)



@actor
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
ps.load_data(os.path.abspath("data.txt"))
ps.set_worker_num(4)
ps_wfcontext = ps.export(ClusterExecutor)






ps_fn = ps_wfcontext.export()
result = ps_fn({})
print("Params from PS:", result)
