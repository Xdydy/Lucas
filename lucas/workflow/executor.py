from .dag import duplicateDAG,DAG,DataNode,ControlNode
from lucas.utils.logging import log
from threading import Thread
import time

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
    
class LucasThread(Thread):
    def __init__(self, node: ControlNode, *args):
        Thread.__init__(self)
        self.node = node
        self.args = args
        self.result = None
        self.error = None
    def run(self):
        try:
            self.result = self.node.calculate()
            log.info(f"{self.node.describe()} calculate {self.result.describe()}")
        except Exception as e:
            self.error = e
            log.error(f"Error in thread: {e}")
class MulThreadExecutor:
    def __init__(self, dag:DAG):
        self.dag = duplicateDAG(dag)
    def launch(self, node:ControlNode):
        task = LucasThread(node)
        task.start()
        return task
    def execute(self):
        while not self.dag.hasDone():
            tasks = []
            pending = []
            for node in self.dag.get_nodes():
                if node.done:
                    continue
                if isinstance(node, DataNode):
                    if node.is_ready():
                        tasks.append(node)
                if isinstance(node, ControlNode):
                    if node.get_pre_data_nodes() == []:
                        tasks.append(node)

            while len(tasks) != 0 or len(pending) != 0:
                while len(tasks) == 0 and len(pending) != 0:
                    try:
                        task = pending.pop(0)
                        if task.is_alive():
                            log.info(f"Task {task} is alive")
                            pending.append(task)
                            time.sleep(0.1)
                            continue
                        elif task.result is not None:
                            node:DataNode = task.result
                            if node.is_ready():
                                tasks.append(node)
                        else :
                            log.error(f"Task failed: {task.error}")
                            raise task.error
                    except IndexError:
                        log.error(f"No task to run: {tasks}")
                        log.error(f"Pending tasks: {pending}")
                        raise IndexError("No task to run")
                if len(tasks) == 0:
                    break
                node = tasks.pop(0)
                node.done = True
                if isinstance(node, DataNode):
                    for control_node in node.get_succ_control_nodes():
                        control_node: ControlNode
                        log.info(f"{control_node.describe()} appargs {node.ld.value}")
                        if control_node.appargs(node.ld):
                            tasks.append(control_node)
                elif isinstance(node, ControlNode):
                    pending.append(self.launch(node))
                    # r_node: DataNode = node.calculate()
                    # log.info(f"{node.describe()} calculate {r_node.describe()}")
                    # if r_node.is_ready():
                    #     task.append(r_node)
        result = None
        for node in self.dag.get_nodes():
            if isinstance(node, DataNode) and node.is_end_node:
                result = node.ld.value
                break
        return result