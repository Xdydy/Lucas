from .protos import controller_pb2, controller_pb2_grpc
import threading
class ExecutorSandBox:
    def __init__(self, execute_obj, params: list[str]):
        self._execute_obj = execute_obj
        self._args = {}
        self._params = params
        self._torun = False
        self._has_run = False
        self._lock = threading.Lock()
    def apply_args(self, data: dict):
        self._args.update(data)
    def can_run(self) -> bool:
        for param in self._params:
            if param not in self._args:
                return False
        return self._torun and not self._has_run
    def set_run(self) -> bool:
        self._torun = True
    def run(self):
        try:
            result = self._execute_obj(**self._args)
        except TypeError as e:
            raise RuntimeError(f"Failed to execute function: {e}")
        except Exception as e:
            raise RuntimeError(f"Error during function execution: {e}")
        self._has_run = True
        return result
    def lock(self):
        return self._lock

class FunctionExecutor:
    def __init__(self, fn, params):
        self._fn = fn
        self._params = params
        self._sandboxes_lock = threading.Lock()
        self._sandboxes : dict[str, ExecutorSandBox] = {}

    def create_instance(self, instance_id: str):
        with self._sandboxes_lock:
            if instance_id in self._sandboxes:
                return self._sandboxes[instance_id]
            sandbox = ExecutorSandBox(self._fn, self._params)
            self._sandboxes[instance_id] = sandbox
            return sandbox
class ClassExecutor:
    def __init__(self, obj, methods: list[controller_pb2.AppendClass.Method]):
        self._obj = obj
        self._methods = methods
        self._sandboxes : dict[str, dict[str, ExecutorSandBox]] = {}

    def create_instance(self, instance_id: str, method_name: str):
        method_name = method_name.split(".")[-1]
        if method_name not in [m.method_name for m in self._methods]:
            raise RuntimeError(f"Method {method_name} not found in class executor")
        if method_name not in self._sandboxes:
            self._sandboxes[method_name] = {}
        if instance_id not in self._sandboxes[method_name]:
            for m in self._methods:
                if m.method_name == method_name:
                    self._sandboxes[method_name][instance_id] = ExecutorSandBox(getattr(self._obj, method_name), m.params)
                    break
        return self._sandboxes[method_name][instance_id]
