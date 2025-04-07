from .workflow import Workflow
from .route import Route
class WorkflowContext:
    def __init__(self, wf_generate_fn, provider, route:Route):
        self._wf_generate_fn = wf_generate_fn
        self._rt = None
        self._provider = provider
        self._route = route

    def set_runtime(self, rt):
        self._rt = rt
    
    def generate(self) -> Workflow:
        return self._wf_generate_fn(self._rt)
    
    def export(self):
        if self._provider == 'knative':
            from ..serverless_function import Metadata
            from ..runtime.kn_runtime import KnativeRuntime
            def kn_workflow(metadata: Metadata):
                rt = KnativeRuntime(metadata)
                self.set_runtime(rt)
                workflow = self.generate()
                
                return workflow.execute()
            return kn_workflow
        elif self._provider == 'aliyun':
            from ..runtime.aliyun_runtime import AliyunRuntime
            def ali_workflow(args0, args1):
                rt = AliyunRuntime(args0, args1)
                self.set_runtime(rt)
                workflow = self.generate()
                return workflow.execute()
            return ali_workflow
        elif self._provider == 'local-once':
            from ..runtime.local_once_runtime import LocalOnceRuntime
            from ..serverless_function import Metadata
            import uuid
            def local_once_workflow(data: dict):
                route_dict = {}
                for function in self._route.functions:
                    route_dict[function.name] = function.handler
                metadata = Metadata(str(uuid.uuid4()), data, None, route_dict, 'invoke', None, None)
                rt = LocalOnceRuntime(metadata)
                self.set_runtime(rt)
                workflow = self.generate()
                return workflow.execute()
            return local_once_workflow
        else:
            raise NotImplementedError(f"provider {self._provider} is not supported yet")