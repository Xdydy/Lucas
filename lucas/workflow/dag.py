from typing import Any, List, Callable, TYPE_CHECKING
from .ld import Lambda
if TYPE_CHECKING:
    from .workflow import Workflow

class DAGNode:
    def __init__(self) -> None:
        self.done = False
        self.belong_dag:"DAG" = None
        pass


class ControlNode(DAGNode):
    def __init__(self, fn) -> None:
        super().__init__()
        self.fn = fn
        self.pre_data_nodes = []
        self.ld_to_key: dict[Lambda, str] = {}
        self.datas = {}
        self.data_node = None

    def add_pre_data_node(self, data_node: DAGNode):
        self.pre_data_nodes.append(data_node)

    def set_data_node(self, data_node:"DataNode"):
        self.data_node = data_node

    def get_pre_data_nodes(self):
        return self.pre_data_nodes

    def get_data_node(self):
        return self.data_node

    def defParams(self, ld: Lambda, key: str):
        self.ld_to_key[ld] = key

    def appargs(self, ld: Lambda) -> bool:
        key = self.ld_to_key[ld]
        # self.datas[key] = ld.value if not callable(ld.value) else ld
        self.datas[key] = ld.value
        if len(self.datas) == len(self.ld_to_key):
            return True
        else:
            return False

    def calculate(self):
        res = self.fn(self.datas)
        from collections.abc import Generator
        if isinstance(res, Generator):
            try:
                next(res)
            except StopIteration as e:
                res = e.value
        self.data_node.set_value(res)
        self.data_node.try_parent_ready()
        if self.data_node.is_ready():
            self.data_node.set_ready()
        return self.get_data_node()
    
    def describe(self) -> str:
        res = f"fn ("
        for key,value in self.ld_to_key.items():
            res += f"{value},"
        res = res + ")"
        return res

    def __str__(self) -> str:
        res = f"(ControlNode {super().__str__()}) {self.fn.__name__}"
        return res


class DataNode(DAGNode):
    def __init__(self, ld: Lambda) -> None:
        super().__init__()
        self.ld = ld
        self.ready = False
        self.succ_control_nodes = []
        self.is_end_node = False
        self.pre_control_node = None
        self.parent_node:"DataNode" = None
        self.child_node:list["DataNode"] = []
        ld.setDataNode(self)

    def set_parent_node(self, node:"DataNode"):
        self.parent_node = node
    def get_parent_node(self):
        return self.parent_node
    def registry_child_node(self, node:"DataNode"):
        self.child_node.append(node)

    def set_pre_control_node(self, control_node: "ControlNode"):
        self.pre_control_node = control_node
    
    def get_pre_control_node(self) -> "ControlNode":
        return self.pre_control_node

    def add_succ_control_node(self, control_node: "ControlNode"):
        self.succ_control_nodes.append(control_node)

    def get_succ_control_nodes(self):
        return self.succ_control_nodes

    def set_value(self, value: Any):
        if isinstance(value, Lambda):
            ld = value
            if ld.canIter:
                self.ld.value = ld.value
                self.ld.canIter = True
                for v in ld.value:
                    if not isinstance(v,Lambda):
                        v = Lambda(v)
                        DataNode(v)
                    v.getDataNode().set_parent_node(self)
                    self.registry_child_node(v.getDataNode())
            else:
                self.ld.value = ld
                self.registry_child_node(ld.getDataNode())
                ld.getDataNode().set_parent_node(self)
        else:
            self.ld.value = value
        
    def try_parent_ready(self):
        if self.parent_node == None:
            return
        if not self.is_ready():
            return
        if self.parent_node.is_ready():
            self.parent_node.apply()
            self.parent_node.set_ready()
            self.parent_node.try_parent_ready()
    def is_ready(self):
        if self.ready:
            return True
        for child_node in self.child_node:
            if not child_node.is_ready():
                return False
        if self.ld.value == None:
            return False
        return True
    def set_ready(self):
        self.ready = True
    def apply(self):
        if self.ld.canIter:
            for i in range(len(self.ld.value)):
                self.ld.value[i] = self.ld.value[i].value
        else:
            self.ld.value = self.ld.value.value
    
    def describe(self) -> str:
        res = f"Lambda value is: {self.ld}"
        return res

    def __str__(self) -> str:
        res = f"[DataNode {super()}] {self.ld}"
        return res


class DAG:
    def __init__(self, workflow:"Workflow") -> None:
        self.nodes: List[DAGNode] = []
        self.workflow_ = workflow

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

    def get_nodes(self):
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
            if node.done == False:
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
                node.done = True
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
            if isinstance(node, DataNode) and node.is_end_node:
                result = node.ld.value
                break
        return result
