from .protos import controller_pb2, controller_pb2_grpc

class ExecutorSandBox:
    def __init__(self, execute_obj, params: list[str]):
        self._execute_obj = execute_obj
        self._args = {}
        self._params = params
        self._torun = False
    def apply_args(self, data: dict):
        self._args.update(data)
    def can_run(self) -> bool:
        for param in self._params:
            if param not in self._args:
                return False
        return self._torun
    def set_run(self) -> bool:
        self._torun = True
    def run(self):
        try:
            result = self._execute_obj(**self._args)
        except TypeError as e:
            raise RuntimeError(f"Failed to execute function: {e}")
        except Exception as e:
            raise RuntimeError(f"Error during function execution: {e}")
        return result

class FunctionExecutor:
    def __init__(self, fn, params):
        self._fn = fn
        self._params = params
        self._sandboxes : dict[str, ExecutorSandBox] = {}

    def create_instance(self, instance_id: str):
        if instance_id in self._sandboxes:
            return self._sandboxes[instance_id]
        sandbox = ExecutorSandBox(self._fn, self._params)
        self._sandboxes[instance_id] = sandbox
        return sandbox

    # def apply_args(self, instance_id:str, data: dict):
    #     if instance_id not in self._sandboxes:
    #         raise RuntimeError(f"Instance {instance_id} not found")
    #     sandbox = self._sandboxes[instance_id]
    #     sandbox.apply_args(data)

    # def can_run(self, instance_id: str) -> bool:
    #     if instance_id not in self._sandboxes:
    #         raise RuntimeError(f"Instance {instance_id} not found")
    #     sandbox = self._sandboxes[instance_id]
    #     return sandbox.can_run()
    # def run(self, instance_id: str):
    #     if instance_id not in self._sandboxes:
    #         raise RuntimeError(f"Instance {instance_id} not found")
    #     try:
    #         sandbox = self._sandboxes[instance_id]
    #         result = sandbox.run()
    #     except Exception as e:
    #         raise RuntimeError(f"Failed to run function in instance {instance_id}: {e}")
    #     finally:
    #         del self._sandboxes[instance_id]
    #     return result
    
class ClassExecutor:
    def __init__(self, obj, methods: list[controller_pb2.AppendClass.Method]):
        self._obj = obj
        self._methods = methods
        self._sandboxes : dict[str, dict[str, ExecutorSandBox]] = {}

    def create_instance(self, instance_id: str, method_name: str):
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
