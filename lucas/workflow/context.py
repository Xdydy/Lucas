from .workflow import Workflow
from .route import Route
from typing import Type, TypeVar, TYPE_CHECKING
import uuid
if TYPE_CHECKING:
    from ..runtime import Runtime
class WorkflowContext:
    def __init__(self, wf: Workflow, provider:str, route:Route):
        self._wf = wf
        self._rt_cls  = None
        self._provider = provider
        self._route = route

    def set_runtime_cls(self, rt_cls):
        if rt_cls is not None:
            self._rt_cls = rt_cls
            return
        if self._provider == 'knative':
            from ..runtime.kn_runtime import KnativeRuntime
            self._rt_cls = KnativeRuntime
        elif self._provider == 'aliyun':
            from ..runtime.aliyun_runtime import AliyunRuntime
            self._rt_cls = AliyunRuntime
        elif self._provider == 'local-once':
            from ..runtime.local_once_runtime import LocalOnceRuntime
            self._rt_cls = LocalOnceRuntime
        else:
            raise NotImplementedError(f"provider {self._provider} is not supported yet")

    def set_runtime(self, rt):
        self._wf.setRuntime(rt)
    
    def generate(self) -> Workflow:
        """
        Generate the workflow. 
        If the runtime is not set, it will throw an error when executed, but the workflow can still be generated for static analysis.
        If you want to execute the workflow, you need to call `export()` to get the function.
        Returns:
            Workflow: The generated workflow.
        """
        return self._wf
    
    def export(self, fn=None):
        """
        Export the workflow function.
        Returns:
            Callable: The exported workflow function.
        """
        if fn is not None:
            return fn
        if self._provider == 'knative':
            from ..serverless_function import Metadata
            from ..runtime.kn_runtime import KnativeRuntime
            def kn_workflow(metadata: Metadata):
                rt = KnativeRuntime(metadata)
                self.set_runtime(rt)
                
                return self._wf.execute()
            return kn_workflow
        elif self._provider == 'aliyun':
            from ..runtime.aliyun_runtime import AliyunRuntime
            def ali_workflow(args0, args1):
                rt = AliyunRuntime(args0, args1)
                self.set_runtime(rt)
                return self._wf.execute()
            return ali_workflow
        elif self._provider == 'local-once':
            from ..runtime.local_once_runtime import LocalOnceRuntime
            from ..serverless_function import Metadata
            def local_once_workflow(data: dict):
                route_dict = {}
                for function in self._route.functions:
                    route_dict[function.name] = function.handler
                metadata = Metadata(str(uuid.uuid4()), data, None, route_dict, 'invoke', None, None)
                rt = LocalOnceRuntime(metadata)
                self.set_runtime(rt)
                return self._wf.execute()
            return local_once_workflow
        elif self._provider == 'actor':
            from lucas import routeBuilder
            from lucas.serverless_function import Metadata
            from lucas.actorc.actor import ActorRuntime
            def actor_workflow_export_func(data: dict):
                route = routeBuilder.build()
                route_dict = {}
                for function in route.functions:
                    route_dict[function.name] = function.handler
                for workflow in route.workflows:
                    route_dict[workflow.name] = workflow
                for actor in route.actors:
                    route_dict[actor.name] = actor._cls
                metadata = Metadata(
                    id=str(uuid.uuid4()),
                    params=data,
                    namespace=None,
                    router=route_dict,
                    request_type="invoke",
                    redis_db=None,
                    producer=None
                )
                rt = ActorRuntime(metadata)
                self.set_runtime(rt)
                return self._wf.execute()
            return actor_workflow_export_func
        else:
            raise NotImplementedError(f"provider {self._provider} is not supported yet")