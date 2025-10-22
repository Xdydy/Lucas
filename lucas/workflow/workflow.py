from typing import Callable,Dict,TYPE_CHECKING,Any
from ..utils import get_function_container_config
from .._private import ActorInstance
from .dag import DAG, ControlNode,DataNode, ActorNode
from .ld import Lambda
from ..runtime import Runtime
from .executor import Executor
from .route import Route,RouteRunner,RouteGroupFunc
from ..utils.logging import log
from .utils import InvokeFuntion, LocalFunctionCall

class WorkflowInput:
    def __init__(self,workflow:"Workflow") -> None:
        self.workflow = workflow
        pass

    def get(self,key:str,default_val=None) -> Lambda:
        if self.workflow.params.get(key) != None:
            return self.workflow.params[key]
        else:
            if default_val != None:
                ld = Lambda(default_val)
            else:
                ld = Lambda()
            DataNode(ld)
            self.workflow.params[key] = ld
            return ld
    def __getitem__(self,key:str) -> Lambda:
        return self.get(key)

class Workflow:
    def __init__(self,route:Route = None, name:str= None) -> None:
        self.route = route
        self.params:Dict[str,Any] = {}
        self.dag = DAG(self)
        self.frt: Runtime = None
        self.name: str = name
        self._executor_cls:Executor = None
        pass
    def copy(self):
        new_workflow = Workflow(self.route, self.name)
        new_workflow.setRuntime(self.frt)
        new_workflow.params = self.params.copy()
        return new_workflow

    def setRuntime(self, frt: Runtime):
        self.frt = frt
    def getRuntime(self):
        return self.frt

    def setExecutor(self,executor_cls:Executor):
        self._executor_cls = executor_cls

    def invokeHelper(self, fn_name):
        route_func = self.route.find(fn_name)
        if isinstance(route_func, RouteGroupFunc):
            group_func = route_func.group_func
            fn = group_func()
            fn_name = fn._config.name
        def invoke_fn(event:Dict):
            nonlocal self,fn_name
            return self.frt.call(fn_name, event)
        return invoke_fn, fn_name
    def invokeMethodHelper(self, obj: ActorInstance, method_name: str):
        def invoke_method(event:Dict):
            nonlocal self,obj,method_name
            return self.frt.call(obj, method_name, event)
        return invoke_method
    @staticmethod
    def funcHelper(fn):
        return LocalFunctionCall(fn)

    def input(self) -> dict | Lambda:
        """
        return the input if the runtime is set
        else return a lambda
        """
        if self.frt != None:
            return self.frt.input()
        else:
            return WorkflowInput(self)
    
    def build_function_param_dag(self,fn_ctl_node:ControlNode,key,ld:Lambda):
        if not isinstance(ld, Lambda):
            ld = Lambda(ld)
        param_node = DataNode(ld) if ld.getDataNode() == None else ld.getDataNode()
        param_node.add_succ_control_node(fn_ctl_node)
        fn_ctl_node.add_pre_data_node(param_node)
        fn_ctl_node.defParams(ld, key)
        self.dag.add_node(param_node)
        return param_node
    
    def build_function_return_dag(self,fn_ctl_node:ControlNode) -> Lambda:
        r = Lambda()
        result_node = DataNode(r)
        fn_ctl_node.set_data_node(result_node)
        result_node.set_pre_control_node(fn_ctl_node)
        self.dag.add_node(result_node)
        return r

    def call(self, fn_name:str, fn_params:Dict[str,Lambda]) -> Lambda:
        """
        for the remote code support
        """
        invoke_fn, fn_name = self.invokeHelper(fn_name)
        fn_ctl_node = ControlNode(invoke_fn, fn_name, "remote")
        self.dag.add_node(fn_ctl_node)
        for key, ld in fn_params.items():
            self.build_function_param_dag(fn_ctl_node,key,ld)

        r = self.build_function_return_dag(fn_ctl_node)
        return self.catch(r)
    
    def map(self, fn_name: str, fn_params: Dict[str, Lambda]) -> Lambda:
        """
        for the remote code support
        """
        invoke_fn, fn_name = self.invokeHelper(fn_name)
        fn_ctl_node = ControlNode(invoke_fn, fn_name, "remote_map")
        self.dag.add_node(fn_ctl_node)
        for key, ld in fn_params.items():
            self.build_function_param_dag(fn_ctl_node,key,ld)

        r = self.build_function_return_dag(fn_ctl_node)
        return self.catch(r)

    def call_method(self, obj: ActorInstance, method_name: str, fn_params:Dict[str,Lambda]) -> Lambda:
        """
        for the remote code support
        """
        if not hasattr(obj._instance, method_name):
            raise AttributeError(f"Object {obj} has no method {method_name}")
        method = getattr(obj._instance, method_name)
        if not callable(method):
            raise TypeError(f"{method_name} is not callable")
        invoke_fn = self.invokeHelper(f"{obj._id}-{method_name}")
        fn_ctl_node = ActorNode(obj, invoke_fn, f"{obj._instance.__class__.__name__}.{method_name}", "remote")
        self.dag.add_node(fn_ctl_node)
        for key, ld in fn_params.items():
            self.build_function_param_dag(fn_ctl_node,key,ld)

        r = self.build_function_return_dag(fn_ctl_node)
        return self.catch(r)

    def func(self,fn,*args,**kwargs) -> Lambda:
        """
        for the local code support
        """
        fn_ctl_node = ControlNode(Workflow.funcHelper(fn), fn.__name__, "local")
        self.dag.add_node(fn_ctl_node)
        for index,ld in enumerate(args):
            self.build_function_param_dag(fn_ctl_node,index,ld)
        for key, ld in kwargs.items():
            self.build_function_param_dag(fn_ctl_node,key,ld)

        r = self.build_function_return_dag(fn_ctl_node)
        return self.catch(r)
    
    def catch(self, ld: Lambda) -> Lambda:
        """
        for the Lambda use map(etc) workflow support
        """
        return ld.becatch(self)
    
    def execute(self):
        assert self.frt != None, "Runtime is not set"
        _input = self.frt.input()
        for key, ld in self.params.items():
            if isinstance(ld, Lambda):
                if ld.getDataNode() == None:
                    param_node = DataNode(ld)
                    self.dag.add_node(param_node)
                else:
                    param_node = ld.getDataNode()
                param_node.set_value(_input[key])
                param_node.set_ready()
        if self._executor_cls==None:
            executor = Executor(self.dag)
        else:
            executor = self._executor_cls(self.dag)
        return executor.execute()
    def end_with(self,ld:Lambda):
        if not isinstance(ld, Lambda):
            ld = Lambda(ld)
            end_node = DataNode(ld)
        else:
            end_node = ld.getDataNode()
        self.dag.add_node(end_node)
        end_node._is_end_node = True
    
    def __str__(self) -> str:
        return str(self.dag)

    def valicate(self):
        return self.dag