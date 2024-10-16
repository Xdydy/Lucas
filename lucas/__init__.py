from .durable import durable

from .runtime import (
    Runtime, 
    FaasitResult,
    AliyunRuntime,
    LocalOnceRuntime,
    LocalRuntime,
    KnativeRuntime,
    createRuntimeMetadata,
    RuntimeMetadata
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
            async def local_function(event,metadata:RuntimeMetadata = None) -> FaasitResult:
                frt = LocalRuntime(event,metadata)
                return await fn(frt)
            return local_function
        case 'aliyun':
            def aliyun_function(arg0, arg1):
                frt = AliyunRuntime(arg0, arg1)
                return fn(frt)
            return aliyun_function
        case 'knative':
            async def kn_function(event) -> FaasitResult:
                frt = KnativeRuntime(event)
                return await fn(frt)
            return kn_function
        case 'aws':
            frt = Runtime(containerConf)
        case 'local-once':
            def localonce_function(event, 
                               workflow_runner = None,
                               metadata: RuntimeMetadata = None
                               ):
                frt = LocalOnceRuntime(event, workflow_runner, metadata)
                result = fn(frt)
                return result
            return localonce_function
        case _:
            raise ValueError(f"Invalid provider {containerConf['provider']}")

routeBuilder = RouteBuilder()

def function(*args, **kwargs):
    # Read Config for different runtimes
    if kwargs.get('name') is not None:
        fn_name = kwargs.get('name')
        def function(fn: type_Function) -> type_Function:
            new_func = transformfunction(fn)
            routeBuilder.func(fn_name).set_handler(new_func)
            return new_func

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
    wf = Workflow(route)
    r  = fn(wf)
    wf.end_with(r)
    return wf
        

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
                    frt = LocalOnceRuntime(event, RouteRunner(workflow.route), createRuntimeMetadata('workflow'))
                    workflow.setRuntime(frt)
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

__all__ = ["function","workflow","durable","create_handler"]