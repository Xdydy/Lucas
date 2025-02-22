import numpy as np
from lucas import Workflow
from lucas.utils.logging import log

class LossFunc:
    def __call__(self, y_true, y_pred):
        ...
    def derivative(self, y_true, y_pred):
        ...
class MSELoss(LossFunc):
    def __call__(self,y_true, y_pred):
        return 0.5 * np.mean((y_true - y_pred)**2)
    def derivative(self,y_true, y_pred):
        return (y_pred - y_true) / y_true.size

class Tensor:
    def __init__(self, data):
        self._data = data
        self._grad = 0
        self._backward_fn = None

    def update(self, grad=0):
        self._grad += grad
        return self._grad

    def get(self):
        return self._data

    def __add__(self, other:"Tensor"):
        tensor = Tensor(self.get() + other.get())
        def add_backward():
            self.update(1)
            other.update(1)
        tensor._backward_fn = add_backward
        return tensor

    def __mul__(self, other:"Tensor"):
        tensor = Tensor(self.get() * other.get())
        def mul_backward():
            self.update(other.get())
            other.update(self.get())
        tensor._backward_fn = mul_backward
        return tensor

    def no_grad(self):
        self._grad = 0

class TrainContext:
    def __enter__(self):
        return self  

    def __exit__(self, exc_type, exc_value, traceback):
        pass
    def __init__(self, **kwargs):
        self._layers = []
        self._wf = Workflow(name=kwargs.get('name'))
        self._lr = kwargs.get('lr', 0.01)
        self._lossFn: LossFunc = kwargs.get('loss', MSELoss)()
        self._forward_value = None
    def Linear(self, input_size, output_size):
        w = np.random.randn(input_size, output_size) * 0.01
        b = np.zeros((1, output_size))
        log.info(f'Linear layer: {input_size} -> {output_size}, w = {w}, b = {b}')

        
        def forward(X):
            layer_input = None
            def backward(dout):
                nonlocal w,b
                dw = np.dot(layer_input.T, dout)
                db = np.sum(dout, axis=0, keepdims=True)
                dx = np.dot(dout, w.T)
                w -= self._lr * dw
                b -= self._lr * db
                log.info(f'Linear backward: dout = {dout}, dw = {dw}, db = {db}, dx = {dx}')
                return dx
            self._layers.append(backward)
            
            def forward_execute(x):
                nonlocal layer_input
                layer_input = x
                y = np.dot(x, w) + b
                log.info(f'Linear forward: X = {x}, y = {y}')
                self._forward_value = y
                return y
            output = self._wf.func(forward_execute, X)
            return output
        
        return forward
    

    def Sigmoid(self):

        def forward(X):
            layer_output = None
            def backward(dout):
                dx = dout * layer_output * (1 - layer_output)
                log.info(f"Sigmoid backward: dout = {dout}, dx = {dx}")
                return dx
            self._layers.append(backward)

            def forward_execute(X):
                y = 1 / (1 + np.exp(-X))
                nonlocal layer_output
                layer_output = y
                log.info(f"Sigmoid forward: X = {X}, y = {y}")
                self._forward_value = y
                return y
        
            output = self._wf.func(forward_execute, X)
            return output
        
        return forward

    def forward(self,X):
        self._forward_value = X

    def backword(self, y_true):
        dloss = self._wf.func(self._lossFn.derivative, y_true, self._forward_value)
        for layer in reversed(self._layers):
            dloss = self._wf.func(layer, dloss)

    def trainOnce(self):
        self._wf.execute({})

    def loss(self, y_true):
        return self._lossFn(y_true, self._forward_value)

class LucasTrainer:
    def __init__(self, fn, **kwargs):
        self._fn_proxy = fn
        self._epoch = kwargs['epoch'] if 'epoch' in kwargs else 100
    def train(self, X, y):
        context: TrainContext = self._fn_proxy(X)
        context.backword(y)
        for i in range(self._epoch):
            context.trainOnce()
            print(f'epoch {i} loss: {context.loss(y)}')
        

def training(*args, **kwargs):
    if len(args) == 1 and len(kwargs) == 0:
        fn = args[0] # fn: train(X)
        return LucasTrainer(fn)
    else:
        def __training(fn):
            return LucasTrainer(fn, kwargs)
        return __training
    


__all__ = ['training', 'TrainContext', 'LucasTrainer', 'MSELoss']
