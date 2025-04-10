from typing import Any, List, Callable, TYPE_CHECKING, Optional
from .ld import Lambda
from lucas.utils.logging import log
import threading
import uuid
if TYPE_CHECKING:
    from .workflow import Workflow

class DAGNode:
    def __init__(self) -> None:
        self._id = str(uuid.uuid4())
        self._done = False
        self.belong_dag:"DAG" = None
    def reset(self):
        self._done = False
    def getid(self) -> str:
        return self._id
    def metadata(self, fn_export=False) -> dict:
        return {
            'id': self._id,
            "done": self._done,
        }

class ControlNode(DAGNode):
    def __init__(self, fn, name:str) -> None:
        super().__init__()
        self._fn_name = name
        self._fn = fn
        self._ld_to_key: dict[Lambda, str] = {}
        self._datas = {}
        self._data_node = None
        self._pre_data_nodes:list["DataNode"] = []
        self._init_state = {
            "done": False,
            "fn": fn,
            "pre_data_nodes": [],
            "ld_to_key": {},
            "datas": {},
            "data_node": None,
            'fn_name': name
        }
    def metadata(self, fn_export=False) -> dict:
        result = super().metadata()
        result['type'] = "ControlNode"
        result["functionname"] = self._fn_name
        result['params'] = {ld.getid(): r for ld, r in self._ld_to_key.items()}
        result['current'] = self._datas
        result['data_node'] = self._data_node.getid()
        result['pre_data_nodes'] = [node.getid() for node in self._pre_data_nodes]
        if fn_export:
            import pickle
            import base64
            result['fn'] = base64.b64encode(pickle.dumps(self._fn)).decode()
        return result

    def add_pre_data_node(self, data_node: DAGNode):
        self._pre_data_nodes.append(data_node)

    def set_data_node(self, data_node:"DataNode"):
        self._data_node = data_node

    def get_pre_data_nodes(self):
        return self._pre_data_nodes

    def get_data_node(self):
        return self._data_node

    def defParams(self, ld: Lambda, key: str):
        self._ld_to_key[ld] = key

    def appargs(self, ld: Lambda) -> bool:
        key = self._ld_to_key[ld]
        # self.datas[key] = ld.value if not callable(ld.value) else ld
        self._datas[key] = ld.value
        if len(self._datas) == len(self._ld_to_key):
            return True
        else:
            return False

    def calculate(self):
        res = self._fn(self._datas)
        from collections.abc import Generator
        if isinstance(res, Generator):
            try:
                next(res)
            except StopIteration as e:
                res = e.value
        self._data_node.set_value(res)
        self._data_node.try_parent_ready()
        if self._data_node.is_ready():
            self._data_node.set_ready()
        return self.get_data_node()
    
    def describe(self) -> str:
        res = f"{self._fn_name} ("
        for key,value in self._ld_to_key.items():
            res += f"{value},"
        res = res + ")"
        return res

    def __str__(self) -> str:
        res = f"(ControlNode {super().__str__()}) {self.fn.__name__}"
        return res

    def reset(self):
        """
        reset the control node to the undone state
        """
        super().reset()
        self._ld_to_key = self._init_state["ld_to_key"]
        self._datas = self._init_state["datas"]


class DataNode(DAGNode):
    def __init__(self, ld: Lambda) -> None:
        super().__init__()
        self._ld = ld
        self._ready = ld.value is not None
        self._suf_control_nodes:list["ControlNode"] = []
        self._is_end_node = False
        self._pre_control_node:Optional[ControlNode] = None
        self._parent_node: Optional["DataNode"] = None
        self._child_node:list["DataNode"] = []
        self._lock = threading.Lock()
        ld.setDataNode(self)

    def metadata(self,fn_export=False) -> dict:
        result = super().metadata()
        result['type'] = "DataNode"
        result['lambda'] = self._ld.getid()
        result['ready'] = self._ready
        result['suf_control_nodes'] = [node.getid() for node in self._suf_control_nodes]
        result['pre_control_node'] = self._pre_control_node.getid() if self._pre_control_node else None
        result['parent_node'] = self._parent_node.getid() if self._parent_node else None
        result['child_node'] = [node.getid() for node in self._child_node]
        return result
    
    def reset(self): 
        """
        reset the data node to the undone state
        """
        super().reset()
        self._ready = False
        self._ld.value = None

    def set_parent_node(self, node:"DataNode"):
        self._parent_node = node
    def get_parent_node(self):
        return self._parent_node
    def registry_child_node(self, node:"DataNode"):
        self._child_node.append(node)

    def set_pre_control_node(self, control_node: "ControlNode"):
        self._pre_control_node = control_node
    
    def get_pre_control_node(self) -> "ControlNode":
        return self._pre_control_node

    def add_succ_control_node(self, control_node: "ControlNode"):
        self._suf_control_nodes.append(control_node)

    def get_succ_control_nodes(self):
        return self._suf_control_nodes

    def set_value(self, value: Any):
        if isinstance(value, Lambda):
            ld = value
            if ld.canIter:
                self._ld.value = ld.value
                self._ld.canIter = True
                for v in ld.value:
                    if not isinstance(v,Lambda):
                        v = Lambda(v)
                        DataNode(v)
                    v.getDataNode().set_parent_node(self)
                    self.registry_child_node(v.getDataNode())
            else:
                self._ld.value = ld
                self.registry_child_node(ld.getDataNode())
                ld.getDataNode().set_parent_node(self)
        else:
            self._ld.value = value
        
    def try_parent_ready(self):
        if self._parent_node == None:
            return
        if not self.is_ready():
            return
        if self._parent_node.is_ready():
            self._parent_node.apply()
            self._parent_node.set_ready()
            self._parent_node.try_parent_ready()
    def is_ready(self):
        if self._ready:
            return True
        for child_node in self._child_node:
            if not child_node.is_ready():
                return False
        if self._ld.value is None:
            return False
        return True
    def set_ready(self):
        self._ready = True
    def apply(self):
        if self._ld.canIter:
            for i in range(len(self._ld.value)):
                if isinstance(self._ld.value[i], Lambda):
                    self._ld.value[i] = self._ld.value[i].value
        else:
            self._ld.value = self._ld.value.value
    
    def describe(self) -> str:
        res = f"Lambda value is: {self._ld}"
        return res

    def __str__(self) -> str:
        res = f"[DataNode {super()}] {self._ld}"
        return res


class DAG:
    def __init__(self, workflow:"Workflow") -> None:
        self.nodes: List[DAGNode] = []
        self.workflow_ = workflow

    def metadata(self, fn_export=False) -> dict:
        result = []
        for node in self.nodes:
            result.append(node.metadata(fn_export))
        return result
    
    def reset(self):
        for node in self.nodes:
            node.reset()

    def add_node(self, node: DAGNode):
        """
        recursive add node
        if node is already in nodes, return
        we have considerd the subgraph case in this function
        """
        if node in self.nodes or node == None:
            return
        node.belong_dag = self
        self.nodes.append(node)
        if isinstance(node, DataNode):
            self.add_node(node.get_pre_control_node())
            for control_node in node.get_succ_control_nodes():
                control_node: ControlNode
                self.add_node(control_node)
        elif isinstance(node, ControlNode):
            self.add_node(node.get_data_node())
            for data_node in node.get_pre_data_nodes():
                self.add_node(data_node)

    def get_nodes(self) -> list[DAGNode]:
        return self.nodes

    def __str__(self):
        res = ""
        for node in self.nodes:
            if isinstance(node, DataNode):
                res += str(node)
                for control_node in node.get_succ_control_nodes():
                    control_node: ControlNode
                    res += f"  -> {str(control_node)}\n"
            if isinstance(node, ControlNode):
                res += str(node)
                data_node: DataNode = node.get_data_node()
                res += f"  -> {str(data_node)}\n"
        return res

    def hasDone(self) -> bool:
        for node in self.nodes:
            if node._done == False:
                return False
        return True
    def run(self):
        while not self.hasDone():
            task = []
            for node in self.nodes:
                if node.done:
                    continue
                if isinstance(node, DataNode):
                    if node.is_ready():
                        task.append(node)
                if isinstance(node, ControlNode):
                    if node.get_pre_data_nodes() == []:
                        task.append(node)

            while len(task) != 0:
                node = task.pop(0)
                node._done = True
                if isinstance(node, DataNode):
                    for control_node in node.get_succ_control_nodes():
                        control_node: ControlNode
                        print(f"{control_node.describe()} appargs {node.ld.value}")
                        if control_node.appargs(node.ld):
                            task.append(control_node)
                elif isinstance(node, ControlNode):
                    r_node: DataNode = node.calculate()
                    print(f"{node.describe()} calculate {r_node.describe()}")
                    if r_node.is_ready():
                        task.append(r_node)
        result = None
        for node in self.nodes:
            if isinstance(node, DataNode) and node._is_end_node:
                result = node.ld.value
                break
        return result

def duplicateDAG(dag:DAG):
    # new_workflow = dag.workflow_.copy()
    new_workflow = dag.workflow_
    new_dag = DAG(new_workflow)
    new_workflow.dag = new_dag
    nodes = dag.get_nodes()

    node_map:dict[DAGNode,DAGNode] = {}
    lambda_map:dict[Lambda,Lambda] = {}
    for node in nodes:
        if isinstance(node, DataNode):
            new_lambda = Lambda(node.ld.value)
            lambda_map[node.ld] = new_lambda
            new_node = DataNode(new_lambda) 
            new_node.belong_dag = new_dag
            new_node.done = False
            new_node._is_end_node = node._is_end_node
            node_map[node] = new_node
            new_dag.add_node(new_node)
        elif isinstance(node, ControlNode):
            new_node = ControlNode(node.fn, node._fn_name)
            new_node.belong_dag = new_dag
            new_node.datas = node.datas
            new_node.done = False
            node_map[node] = new_node
            new_dag.add_node(new_node)
    
    for node in nodes:
        if isinstance(node, DataNode):
            new_node:DataNode = node_map[node]
            if node.get_pre_control_node() != None:
                new_node.set_pre_control_node(node_map[node.get_pre_control_node()])
            for ctl_node in node.get_succ_control_nodes():
                new_node.add_succ_control_node(node_map[ctl_node])
        elif isinstance(node,ControlNode):
            new_node:ControlNode = node_map[node]
            new_node.set_data_node(node_map[node.get_data_node()])
            for data_node in node.get_pre_data_nodes():
                new_node.add_pre_data_node(node_map[data_node])
            for ld, key in node.ld_to_key.items():
                new_node.defParams(lambda_map[ld], key)
    return new_dag