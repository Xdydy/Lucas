from ..serverless_function import Metadata

class FunctionConfig:
    def __init__(self, *args, **options):
        for key, value in options.items():
            setattr(self, key, value)
        pass

class Function:
    def __init__(self, fn, config: FunctionConfig = None):
        self._config = config
        fn = self._transformfunction(fn)
        self._fn = fn
        self.onFunctionInit(fn)

    def _transformfunction(self, fn):
        raise NotImplementedError("This method should be implemented by the subclass.\n If you dont want to implement it, just return the self._fn is ok")
    
    def export(self):
        return self._fn
    def onFunctionInit(self, fn):
        pass
    def onFunctionStart(self):
        pass
    def onFunctionFinish(self):
        pass
    def onFunctionError(self):
        pass
    
class LocalFunction(Function):
    def __init__(self, fn, config: FunctionConfig=None):
        super().__init__(fn, config)

    def _transformfunction(self, fn):
        def local_function(md: Metadata):
            from ..runtime.local_runtime import LocalRuntime
            rt = LocalRuntime(md)
            return fn(rt)
        return local_function

class AliyunFunction(Function):
    def __init__(self, fn, config: FunctionConfig=None):
        super().__init__(fn, config)
    def _transformfunction(self, fn):
        def aliyun_function(arg0, arg1):
            from ..runtime.aliyun_runtime import AliyunRuntime
            rt = AliyunRuntime(arg0, arg1)
            return fn(rt)
        return aliyun_function

class KnativeFunction(Function):
    def __init__(self, fn, config: FunctionConfig = None):
        super().__init__(fn, config)
    def _transformfunction(self, fn):
        def kn_function(md: Metadata):
            from ..runtime.kn_runtime import KnativeRuntime
            rt = KnativeRuntime(md)
            return fn(rt)
        return kn_function
    
class LocalOnceFunction(Function):
    def __init__(self, fn, config: FunctionConfig = None):
        super().__init__(fn, config)
    def _transformfunction(self, fn):
        def localonce_function(data: dict):
            import uuid
            from ..runtime.local_once_runtime import LocalOnceRuntime
            from lucas import routeBuilder
            route = routeBuilder.build()
            route_dict = {}
            for function in route.functions:
                route_dict[function.name] = function.handler
            for workflow in route.workflows:
                route_dict[workflow.name] = function.handler
            metadata = Metadata(str(uuid.uuid4()), data, None, route_dict, 'invoke', None, None)
            rt = LocalOnceRuntime(metadata)
            result = fn(rt)
            return result
        return localonce_function

class DurableFunction(Function):
    def __init__(self, fn, config = None):
        super().__init__(fn, config)
    def _transformfunction(self, fn):
        from ..durable import durable_helper
        return durable_helper(fn)


__all__=[
    'FunctionConfig',
    'Function',
    'LocalFunction',
    'AliyunFunction',
    'KnativeFunction',
    'LocalOnceFunction'
    'DurableFunction'
]