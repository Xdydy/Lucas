from .dag import duplicateDAG,DAG,DataNode,ControlNode
from lucas.utils.logging import log

class Executor:
    def __init__(self, dag:DAG):
        self.dag = duplicateDAG(dag)
    def execute(self):
        while not self.dag.hasDone():
            task = []
            for node in self.dag.get_nodes():
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
                        log.info(f"{control_node.describe()} appargs {node.ld.value}")
                        if control_node.appargs(node.ld):
                            task.append(control_node)
                elif isinstance(node, ControlNode):
                    r_node: DataNode = node.calculate()
                    log.info(f"{node.describe()} calculate {r_node.describe()}")
                    if r_node.is_ready():
                        task.append(r_node)
        result = None
        for node in self.dag.get_nodes():
            if isinstance(node, DataNode) and node.is_end_node:
                result = node.ld.value
                break
        return result