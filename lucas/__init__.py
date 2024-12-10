from .durable import durable_helper

from .runtime import (
    Runtime, 
    FaasitResult,
    createRuntimeMetadata,
    RuntimeMetadata,
    load_runtime
)
from .utils import (
    get_function_container_config,
    callback,
)
from .workflow import Workflow,Route,RouteBuilder,RouteRunner
from typing import Callable, Set, Any
import asyncio
import inspect

type_Function = Callable[[Any], FaasitResult]

def transformfunction(fn: type_Function) -> type_Function:
    containerConf = get_function_container_config()
    match containerConf['provider']:
        case 'local':
            def local_function(event,metadata:RuntimeMetadata = None) -> FaasitResult:
                LocalRuntime = load_runtime('local')
                frt = LocalRuntime(event,metadata)
                return fn(frt)
            return local_function
        case 'aliyun':
            def aliyun_function(arg0, arg1):
                AliyunRuntime = load_runtime('aliyun')
                frt = AliyunRuntime(arg0, arg1)
                return fn(frt)
            return aliyun_function
        case 'knative':
            def kn_function(event) -> FaasitResult:
                KnativeRuntime = load_runtime('knative')
                frt = KnativeRuntime(event)
                return fn(frt)
            return kn_function
        case 'aws':
            frt = Runtime(containerConf)
        case 'local-once':
            def localonce_function(event, 
                               workflow_runner = None,
                               metadata: RuntimeMetadata = None
                               ):
                LocalOnceRuntime = load_runtime('local-once')
                frt = LocalOnceRuntime(event, workflow_runner, metadata)
                result = fn(frt)
                callback(result,frt)
                return result
            return localonce_function
        case _:
            raise ValueError(f"Invalid provider {containerConf['provider']}")

routeBuilder = RouteBuilder()

def durable(fn):
    new_func = durable_helper(fn)
    routeBuilder.func(fn.__name__).set_handler(new_func)
    return new_func

class AbstractFunction:
    def __init__(self, fn):
        self.fn = fn
    def __call__(self, *args, **kwds):
        return self.fn(*args, **kwds)
    def func(self):
        pass

def function(*args, **kwargs):
    # Read Config for different runtimes
    if len(kwargs) > 0:
        wrapper: AbstractFunction = kwargs.get('wrapper')
        def function(fn: type_Function) -> type_Function:
            fn_name = kwargs.get('name', fn.__name__)
            if wrapper is None:
                new_func = transformfunction(fn)
                routeBuilder.func(fn_name).set_handler(new_func)
                return new_func
            else:
                custom_func = wrapper(fn)
                custom_func.func()
                routeBuilder.func(fn_name).set_handler(custom_func)
                return custom_func

        return function
    else:
        fn = args[0]
        signature = inspect.signature(fn)
        def is_frt_runtime():
            if len(signature.parameters) != 1:
                return False
            first_param = next(iter(signature.parameters.values()))
            param_name = first_param.name
            param_annotation = first_param.annotation
            if param_name == 'frt':
                return True
            if param_annotation == Runtime:
                return True
            return False
        if is_frt_runtime():
            new_func = transformfunction(fn)
            routeBuilder.func(fn.__name__).set_handler(new_func)
            return new_func
        else: # custom runtime
            return fn
        

def workflow(fn) -> Workflow:
    route = routeBuilder.build()
    def generate_workflow(
            workflow_runner: RouteRunner = None, 
            metadata = None) -> Workflow:
        wf = Workflow(route,fn.__name__)
        r  = fn(wf)
        wf.end_with(r)
        container_conf = get_function_container_config()
        match container_conf['provider']:
            case 'local-once':
                LocalOnceRuntime = load_runtime('local-once')
                frt = LocalOnceRuntime(
                    None, 
                    workflow_runner if workflow_runner else RouteRunner(route), 
                    metadata if metadata else createRuntimeMetadata(fn.__name__)
                )
                wf.setRuntime(frt)
        return wf
    routeBuilder.workflow(fn.__name__).set_workflow(generate_workflow)
    return generate_workflow()

def recursive(fn):
    def Y(f):
        return (lambda x: f(lambda v: x(x)(v)))(lambda x: f(lambda v: x(x)(v)))
    def helper():
        return fn
    return Y(helper)

def create_handler(fn_or_workflow : type_Function | Workflow):
    container_conf = get_function_container_config()
    if isinstance(fn_or_workflow, Workflow):
        workflow = fn_or_workflow
        match container_conf['provider']:
            case 'local':
                async def handler(event:dict, metadata=None):...
                    # metadata = createFaasitRuntimeMetadata(container_conf['funcName']) if metadata == None else metadata
                    # return await runner.run(event, metadata)
                return handler
            case 'aliyun':
                def handler(args0, args1):
                    if container_conf['funcName'] == '__executor':
                        AliyunRuntime = load_runtime('aliyun')
                        frt = AliyunRuntime(args0, args1)
                        workflow.setRuntime(frt)
                        return workflow.execute(frt.input())
                    else:
                        fn = RouteRunner(workflow.route).route(container_conf['funcName'])
                        result = fn(args0,args1)
                        return result
                return handler
            case 'local-once':
                def handler(event: dict):
                    result = workflow.execute(event)
                    return result
                return handler
        return handler
    else: #type(fn) == type_Function:
        match container_conf['provider']:
            case 'aliyun':
                def handler(event: dict, *args):
                    return asyncio.run(fn_or_workflow(event, *args))
                return handler
            case _:
                async def handler(event: dict, *args):
                    return await fn_or_workflow(event, *args)
                return handler

__all__ = ["function","workflow","durable","create_handler",'recursive','AbstractFunction']