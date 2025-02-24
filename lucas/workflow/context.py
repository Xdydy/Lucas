from .workflow import Workflow

class WorkflowContext:
    def __init__(self, wf_generate_fn):
        self._wf_generate_fn = wf_generate_fn
        self._rt = None

    def set_runtime(self, rt):
        self._rt = rt
    
    def generate(self) -> Workflow:
        return self._wf_generate_fn(self._rt)