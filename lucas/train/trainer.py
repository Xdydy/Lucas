from typing import Callable, Dict, Any, List
from lucas import function, workflow, Workflow, actor
from lucas._private.functions import Function, FunctionConfig
from datasets import Dataset
import time
import inspect

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
                 data_loader: Callable[..., Any] = None,
                 data_processer: Callable[..., Any] = None,
                 model_trainer: Callable[..., Any] = None,
                 data_loader_config: TrainerConfig = None,
                 data_processer_config: TrainerConfig = None,
                 model_trainer_config: TrainerConfig = None
        ):
        self.data_loader = data_loader
        self.data_processer = data_processer
        self.model_trainer = model_trainer
        self.data_loader_config = data_loader_config
        self.data_processer_config = data_processer_config
        self.model_trainer_config = model_trainer_config
    
    def _fetch_function_signature(self, fn: Callable) -> list[str]:
        sig = inspect.signature(fn)
        return [param.name for param in sig.parameters.values()]

    def export(self, executor) -> Callable[[str], Any]:

        data_loader_fn = None
        data_processer_fn = None
        model_trainer_fn = None
        if self.data_loader != None:
            data_loader_fn = function(**self.data_loader_config.export())(self.data_loader).export()
        if self.model_trainer != None:
            model_trainer_fn = function(**self.model_trainer_config.export())(self.model_trainer).export()
        if self.data_processer != None:
            data_processer_fn = function(**self.data_processer_config.export())(self.data_processer).export()
        
            

        @workflow(executor=executor)
        def training_pipeline_workflow(wf: Workflow):
            _in = wf.input()

            pipe = None
            if data_loader_fn != None:
                params = self._fetch_function_signature(self.data_loader)
                dict_params = {param: _in[param] for param in params}
                pipe = wf.call(self.data_loader_config.name, dict_params)
            if data_processer_fn != None:
                params = self._fetch_function_signature(self.data_processer)
                dict_params = {param: pipe for param in params}
                pipe = wf.call(self.data_processer_config.name, dict_params)
            if model_trainer_fn != None:
                params = self._fetch_function_signature(self.model_trainer)
                dict_params = {param: pipe for param in params}
                model = wf.call(self.model_trainer_config.name, dict_params)
            return model
        return training_pipeline_workflow

class ParameterServer:
    def __init__(self, evaluate_func: Function):
        self._evaluate_func = evaluate_func
        self._datas = None
        self._metrics = None
        self._function_wrapper = None
        self._provider = None
    def load_data(self, data):
        self._datas = data
    def store(self, metrics):
        self._metrics = metrics
    def evaluate(self):
        if self._datas is None:
            raise ValueError("No data loaded for evaluation")
        if self._evaluate_func is None:
            raise ValueError("No evaluation function provided")
        self._metrics = self._evaluate_func(self._datas)
        return self._metrics
    def set_function_wrapper(self, wrapper):
        self._function_wrapper = wrapper
    def set_provider(self, provider):
        self._provider = provider
    def export(self, executor):
        if self._evaluate_func is None:
            raise ValueError("No evaluation function provided")
        if self._datas is None:
            raise ValueError("No data loaded for evaluation")
        if self._function_wrapper is None:
            raise ValueError("No function wrapper set for evaluation function")
        if self._provider is None:
            raise ValueError("No provider set for evaluation function")
        evaluate_func = self._evaluate_func._origin_fn
        @function(
            wrapper=self._function_wrapper,
            dependency=[],
            provider=self._provider,
            name="load_data",
            venv="default"
        )
        def load_data(ds):
            def generate_data():
                for x, y in self._datas:
                    yield {
                        "x": x,
                        "y": y
                    }
            return generate_data()
        load_data_fn = load_data.export()
        
        @workflow(executor=executor)
        def parameter_server_workflow(wf: Workflow):
            dataset = wf.call(load_data._config.name, {"ds":"ds"})
            params = self._fetch_function_signature(evaluate_func)
            dict_params = {param: dataset for param in params}
            metric = wf.call(self._evaluate_func._config.name, dict_params)
            return metric

        return parameter_server_workflow

    def _fetch_function_signature(self, fn: Callable) -> list[str]:
        sig = inspect.signature(fn)
        return [param.name for param in sig.parameters.values()]
