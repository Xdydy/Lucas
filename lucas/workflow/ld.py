from typing import Any, TYPE_CHECKING, List
from importlib import import_module
if TYPE_CHECKING:
    from .dag import DataNode,ControlNode
    from .workflow import Workflow

def generate_subgraph(wf:"Workflow", fn, list_lambda: list["Lambda"]) -> "Lambda":
    # from .dag import DataNode, ControlNode
    # from .workflow import Workflow
    return wf.func(fn, *list_lambda)

class Lambda:
    def __init__(self, value: Any | None = None) -> None:
        self.value = value
        self._dataNode: "DataNode" = None
        self.canIter = False
        self.workflow_:"Workflow" = None

    def getDataNode(self):
        return self._dataNode
    
    def setDataNode(self, node:"DataNode"):
        self._dataNode = node

    def becatch(self, wf:"Workflow"):
        self.workflow_ = wf
        return self

    def __getattr__(self,method_name):
        def method_fn(value, method_name):
            attr = getattr(value, method_name)
            if callable(attr):
                def wrapper(*args, **kwargs):
                    return attr(*args, **kwargs)
                return wrapper
            else:
                return attr
        return generate_subgraph(method_fn, [self,method_name])

    # def _generate_dag(self, fn, list_lambda: list["Lambda"]) -> "Lambda":
    #     ControlNode:"ControlNode" = import_module('faasit_runtime.workflow.dag').ControlNode
    #     DataNode:"DataNode" = import_module('faasit_runtime.workflow.dag').DataNode
    #     Workflow:"Workflow" = import_module('faasit_runtime.workflow.workflow').Workflow
    #     invoke_fn = Workflow.funcHelper(fn)
    #     fn_ctl_node = ControlNode(invoke_fn)
    #     for index,ld in enumerate(list_lambda):
    #         param_node = DataNode(ld) if ld.getDataNode() == None else ld.getDataNode()
    #         param_node.add_succ_control_node(fn_ctl_node)
    #         fn_ctl_node.add_pre_data_node(param_node)
    #         fn_ctl_node.defParams(ld,index)

    #     r = Lambda()
    #     result_node = DataNode(r)
    #     fn_ctl_node.set_data_node(result_node)
    #     result_node.set_pre_control_node(fn_ctl_node)
    #     return r

    def checkWorkflow(fn):
        def wrapper(self, *args, **kwargs):
            if not self.workflow_:
                raise Exception(f"Please call workflow.catch before use {fn.__name__}")
            return fn(self, *args, **kwargs)
        return wrapper
    
    @checkWorkflow
    def __add__(self, other: Any) -> "Lambda":
        if not isinstance(other, Lambda):
            other = Lambda(other)
        return generate_subgraph(self.workflow_, lambda x, y: x + y, [self, other])
    
    @checkWorkflow
    def __getitem__(self, key: str) -> "Lambda":
        if not isinstance(key, Lambda):
            key = Lambda(key)
        return generate_subgraph(self.workflow_, lambda dir, key: dir[key], [self,key])
    
    def __call__(self, *args: Any, **kwds: Any) -> "Lambda":
        
        pass

    def __iter__(self) -> "Lambda":
        # return self
        return generate_subgraph(lambda x: iter(x), [self])
    
    def __str__(self) -> str:
        return f"{super().__str__()}::{self.value}"
    
    
    @checkWorkflow
    def map(self, fn) -> "Lambda":
        def map_helper(fn, values):
            results = Lambda([])
            for element in values:
                # result = generate_subgraph(self.workflow_, fn, [element])
                result = fn(element)
                # generate_subgraph(list.append, [results,result])
                results.value.append(result)
            results.canIter = True
            return results
        return generate_subgraph(self.workflow_, map_helper, [fn,self])
    
    @checkWorkflow
    def fork(self, nums) -> "Lambda":
        def fork_helper(values, nums):
            results: List["Lambda"] = []
            chunkSize = len(values) // nums
            results = [values[i:i + chunkSize] for i in range(0, len(values), chunkSize)]
            return results
        return generate_subgraph(self.workflow_, fork_helper, [self,nums])
    
    @checkWorkflow
    def join(self, fn) -> "Lambda":
        def join_helper(values, fn):
            results = Lambda([])
            for value in values:
                for v in value:
                    results.value.append(v)
            results.canIter = True
            results = fn(results)
            return results
        return generate_subgraph(self.workflow_, join_helper, [self,fn])
    
    