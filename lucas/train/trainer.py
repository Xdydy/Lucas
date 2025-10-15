from typing import Callable, Dict, Any, List
from lucas import function, workflow, Workflow
from lucas._private.functions import Function, FunctionConfig
from datasets import Dataset
import time

class DataProcessFunction:
    def __init__(self, fns: list[Function]):
        self._fns: list[Function] = fns
    def export(self):
        index = 0
        
        # @workflow(executor=executor)
        # def robin(wf: Workflow):
        #     if len(self._fns) == 0:
        #         raise ValueError("No worker functions available")
        #     _in =  wf.input()
        #     input_data: Dict[str, List[Any]] = {}
        #     for key, value in _in.items():
        #         if not isinstance(value, List):
        #             value = [value]
        #         input_data[key] = value


        #     def shuffle(*datas):
        #         results = []
        #         for data in datas:
        #             results.extend(data)
        #         return results
        #     results = []
        #     for key, list_value in input_data.items():
        #         for value in list_value:
        #             nonlocal index
        #             fn = self._fns[index % len(self._fns)]
        #             index += 1
        #             result = wf.call(fn._config.name, {key: value})
        #             results.extend(result)
            
        #     return wf.func(shuffle, *results)
        def robin():
            if len(self._fns) == 0:
                raise ValueError("No worker functions available")
            return self._fns[index % len(self._fns)]
        return robin


def data_process(
        num_workers : int = 1,
        wrapper = Function,
        dependency: List = [],
        provider: str = None,
        name: str = None,
        venv: str = None,
    ):
    def __data_process(fn) -> DataProcessFunction:
        fns = []
        for i in range(num_workers):
            fn_name = f"{name or fn.__name__}_worker_{i}"
            func = function(
                provider=provider,
                name=fn_name,
                wrapper=wrapper,
                dependency=dependency,
                venv=venv,
            )(fn)
            fns.append(func)
        dataProcessFunction = DataProcessFunction(fns)
        from lucas import routeBuilder
        routeBuilder.group(name).set_group_func(dataProcessFunction.export())
        return dataProcessFunction
        
    return __data_process


class Trainer:
    def __init__(self, 
                 train_func: Callable[..., Dict[str, Any]], 
                 **config):
        """
        初始化训练器
        :param train_func: 训练函数，应返回包含训练结果的字典
        :param config: 训练配置参数
        """
        self.train_func = train_func
        self.config = config
        self.metrics = {}
        self.history = []
        
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        """
        执行训练
        :return: 训练结果字典
        """
        start_time = time.time()
        
        # 合并初始化配置和运行时参数
        merged_kwargs = {**self.config, **kwargs}
        
        try:
            result = self.train_func(*args, **merged_kwargs)
            self.metrics = result
            self.history.append({
                'timestamp': time.time(),
                'args': args,
                'kwargs': merged_kwargs,
                'result': result
            })
            return result
        except Exception as e:
            self.metrics = {'error': str(e)}
            raise
            
    def get_metrics(self) -> Dict[str, Any]:
        """获取最新训练指标"""
        return self.metrics
    
    def get_history(self) -> list:
        """获取训练历史记录"""
        return self.history

class TrainerConfig:
    def __init__(self,
                 wrapper,
                 dependency,
                 provider,
                 name,
                 venv):
        self.wrapper = wrapper
        self.dependency = dependency
        self.provider = provider
        self.name = name
        self.venv = venv
    def export(self):
        return {
            'wrapper': self.wrapper,
            'dependency': self.dependency,
            'provider': self.provider,
            'name': self.name,
            'venv': self.venv
        }

class TrainerPipeline:
    def __init__(self, 
                 data_loader: Callable[[str], Any],
                 model_trainer: Callable[[Dataset], Any],
                 data_loader_config: TrainerConfig,
                 model_trainer_config: TrainerConfig
        ):
        self.data_loader = data_loader
        self.model_trainer = model_trainer
        self.data_loader_config = data_loader_config
        self.model_trainer_config = model_trainer_config
    
    def export(self, executor, fn=None) -> Callable[[str], Any]:
        @function(**self.data_loader_config.export())
        def data_loader(path: str):
            return self.data_loader(path)
        
        @function(**self.model_trainer_config.export())
        def model_trainer(dataset: Dataset):
            return self.model_trainer(dataset)

        data_loader = data_loader.export()
        model_trainer = model_trainer.export()

        @workflow(executor=executor)
        def training_pipeline_workflow(wf: Workflow):
            _in = wf.input()
            ds = wf.call(self.data_loader_config.name, {"path": _in['path']})
            model = wf.call(self.model_trainer_config.name, {"dataset": ds})
            return model
        workflow_fn = training_pipeline_workflow.export(fn)
        def output_workflow(path:str):
            return workflow_fn({"path": path})
        return output_workflow

class ParameterServer:
    pass
