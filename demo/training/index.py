from lucas.train import training, TrainContext, MSELoss
import numpy as np
@training
def trainfunc(X):
    with TrainContext(lr=0.01, loss=MSELoss) as ctx: # ctx: TrainContext
        fc1 = ctx.Linear(2, 4)  # 输入层到隐藏层
        sigmoid = ctx.Sigmoid() # 激活函数
        fc2 = ctx.Linear(4, 1) # 隐藏层到输出层

        X = fc1(X)
        X = sigmoid(X)
        X = fc2(X)

        ctx.forward(X)
    return ctx

X = np.array([[0,0], [0,1], [1,0], [1,1]])
y = np.array([[0], [1], [1], [0]])
trainfunc.train(X,y) # 训练