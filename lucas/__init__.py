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
from .workflow import Workflow,Route,RouteBuilder,RouteRunner,WorkflowContext,RouteClass
from typing import Callable, Any
import inspect
from ._private import (
    FunctionConfig,
    LocalFunction,
    AliyunFunction,
    KnativeFunction,
    LocalOnceFunction,
    DurableFunction,
    Function,
    ActorClass,
    ActorConfig,
    ActorInstance
)

type_Function = Callable[[Any], FaasitResult]

def transformfunction(fn: type_Function) -> type_Function:
    containerConf = get_function_container_config()
    provider = containerConf['provider']
    if provider == 'local':
        def local_function(event,metadata:RuntimeMetadata = None) -> FaasitResult:
            LocalRuntime = load_runtime('local')
            frt = LocalRuntime(event,metadata)
            return fn(frt)
        return local_function
    elif provider == 'aliyun':
        def aliyun_function(arg0, arg1):
            AliyunRuntime = load_runtime('aliyun')
            frt = AliyunRuntime(arg0, arg1)
            return fn(frt)
        return aliyun_function
    elif provider == 'knative':
        from .serverless_function import Metadata
        def kn_function(metadata: Metadata) -> FaasitResult:
            KnativeRuntime = load_runtime('knative')
            frt = KnativeRuntime(metadata)
            return fn(frt)
        return kn_function
    elif provider == 'aws':
        frt = Runtime(containerConf)
    elif provider == 'local-once':
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
    else :
        raise ValueError(f"Invalid provider {containerConf['provider']}")

routeBuilder = RouteBuilder()

def durable(*args, **kwargs) -> Function:
    def __durable(fn) -> Function:
        config = get_function_container_config()
        provider = kwargs.get('provider', config['provider'])
        fn_name = kwargs.get('name', fn.__name__)
        cpu = kwargs.get('cpu', 0.5)
        memory = kwargs.get('memory', 128)
        fn_config = FunctionConfig(provider=provider, cpu=cpu, memory=memory, name=fn_name)
        func = DurableFunction(fn, fn_config)
        routeBuilder.func(fn_name).set_handler(func.export())
        return func
    if len(args) == 1 and len(kwargs) == 0:
        fn = args[0]
        return __durable(fn)
    else:
        return __durable

from typing import Union  # Add this import at the top if not already present

def function(*args, **kwargs) -> Union[Function, Callable[[Callable[..., Any]], Function]]:

    def __function(fn) -> Function:
        config = get_function_container_config()
        provider = kwargs.get('provider', config['provider'])
        fn_name = kwargs.get('name', fn.__name__)
        cpu = kwargs.get('cpu', 0.5)
        memory = kwargs.get('memory', 128)
        
        func_cls = kwargs.get('wrapper', None)
        Function
        fn_config = FunctionConfig(**kwargs)
        if provider == 'local':
            func = LocalFunction(fn, fn_config)
        elif provider == 'aliyun':
            func = AliyunFunction(fn, fn_config)
        elif provider == 'knative':
            func = KnativeFunction(fn, fn_config)
        elif provider == 'local-once':
            func = LocalOnceFunction(fn, fn_config)
        else:
            assert func_cls != None, "wrapper is required for custom runtime"
            assert issubclass(func_cls, Function), "wrapper must be subclass of Function"
            func = func_cls(fn, fn_config)
        routeBuilder.func(fn_name).set_handler(func.export()).set_function(func)
        return func
    if len(args) == 1 and len(kwargs) == 0:
        fn = args[0]
        return __function(fn)
    else:
        return __function
        
def actor(*args, **kwargs)-> ActorClass:
    def __actor(cls) -> ActorClass:
        class_name = kwargs.get('name', cls.__name__)
        kwargs.setdefault('name', class_name)
        actorConfig = ActorConfig(**kwargs)
        class_cls = kwargs.get('wrapper', None)
        if class_cls is None:
            class_cls = ActorClass
        actor_class = class_cls(cls, actorConfig)
        return actor_class
    if len(args) == 1 and len(kwargs) == 0:
        cls = args[0]
        return __actor(cls)
    else:
        return __actor

def workflow(*args, **kwargs) -> WorkflowContext:
    def __workflow(fn) -> WorkflowContext:
        config = get_function_container_config()
        provider = kwargs.get('provider', config['provider'])
        executor_cls = kwargs.get('executor')
        route = routeBuilder.build()
        wf = Workflow(route,fn.__name__)
        if executor_cls != None:
            wf.setExecutor(executor_cls)
        r = fn(wf)
        wf.end_with(r)
        routeBuilder.workflow(fn.__name__).set_workflow(wf)
        return WorkflowContext(wf, provider, route)

    if len(args) == 1 and len(kwargs) == 0:
        fn = args[0]
        return __workflow(fn)
    else:
        return __workflow


def recursive(fn):
    def Y(f):
        return (lambda x: f(lambda v: x(x)(v)))(lambda x: f(lambda v: x(x)(v)))
    def helper():
        return fn
    return Y(helper)

def create_handler(fn_or_workflow : Function | WorkflowContext):
    container_conf = get_function_container_config()
    if isinstance(fn_or_workflow, WorkflowContext):
        workflow_ctx = fn_or_workflow
        provider = container_conf['provider']
        if provider == 'local':
            async def handler(event:dict, metadata=None):...
                # metadata = createFaasitRuntimeMetadata(container_conf['funcName']) if metadata == None else metadata
                # return await runner.run(event, metadata)
            return handler
        elif provider == 'aliyun':
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
        elif provider == 'local-once':
            def handler(event: dict, executor=None):
                result = workflow_ctx.execute(executor)
                return result
            return handler
        elif provider == 'knative':
            from .serverless_function import Metadata
            from .runtime.kn_runtime import KnativeRuntime
            def handler(metadata: Metadata):
                rt = KnativeRuntime(metadata)
                workflow_ctx.set_runtime(rt)
                workflow = workflow_ctx.generate()
                
                return workflow.execute()
        return handler
    else: #type(fn) == Function:
        return fn_or_workflow.export()

    

__all__ = ["_private","workflow","durable","create_handler",'recursive','AbstractFunction']