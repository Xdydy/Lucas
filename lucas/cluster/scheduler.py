from lucas.utils.logging import log
from lucas.workflow.dag import DAG, ControlNode, DAGNode, DataNode

from .protos import cluster_pb2, cluster_pb2_grpc, controller_pb2, platform_pb2
import grpc

class Scheduler:
    def __init__(self, master_addr: str = "localhost:50051"):
        self._master_addr = master_addr
        
        self._workers = self.get_workers().workers
        for worker in self._workers:
            log.info(f"Worker {worker.worker_id} is available at {worker.host}:{worker.port} with worker rank {worker.worker_rank}")
        host = master_addr.split(":")[0]
        port = int(master_addr.split(":")[1])
        self._workers.append(cluster_pb2.AddWorker(
            worker_id="0",
            host=host,
            port=port,
            worker_rank=0
        ))
    def get_workers(self) -> cluster_pb2.GetWorkersResponse:
        request = cluster_pb2.GetWorkersRequest()
        channel = grpc.insecure_channel(self._master_addr)
        stub = cluster_pb2_grpc.ClusterServiceStub(channel)
        response = stub.GetWorkers(request)
        return response

    def schedule(self, msg: controller_pb2.Message) -> platform_pb2.Message:
        # Implement scheduling logic here
        if msg.type == controller_pb2.MessageType.APPEND_FUNCTION:
            return platform_pb2.Message(
                type=platform_pb2.MessageType.BROADCAST,
                broadcast=platform_pb2.Broadcast(
                    controller_message=msg
                )
            )
        else:
            return platform_pb2.Message(
                type=platform_pb2.MessageType.APPLY_TO_WORKER,
                apply_to_worker=platform_pb2.ApplyToWorker(
                    controller_message=msg
                )
            )
    
    def feedback(self, result: controller_pb2.ReturnResult):
        pass
        
class RobinScheduler(Scheduler):
    def __init__(self, master_addr: str = "localhost:50051"):
        super().__init__(master_addr)
        self._current_worker_index = 0
        self._len = len(self._workers)
        self._node_to_worker = {}
    def analyze(self, dag: DAG):
        nodes = dag.get_nodes()
        in_dags = {}
        for node in nodes:
            in_dags[node] = 0
        for node in nodes:
            if isinstance(node, DataNode):
                for ctl_node in node.get_succ_control_nodes():
                    in_dags[ctl_node] += 1
            elif isinstance(node, ControlNode):
                in_dags[node.get_data_node()] += 1
        
        zero_nodes = [node for node, in_degree in in_dags.items() if in_degree == 0]
        while len(zero_nodes) > 0:
            node = zero_nodes.pop()
            if isinstance(node, DataNode):
                for ctl_node in node.get_succ_control_nodes():
                    ctl_node: ControlNode
                    metadata = ctl_node.metadata()
                    if metadata["id"] not in self._node_to_worker:
                        self._node_to_worker[metadata['id']] = self._workers[self._current_worker_index].worker_id
                        self._current_worker_index = (self._current_worker_index + 1) % self._len
                    in_dags[ctl_node] -= 1
                    if in_dags[ctl_node] == 0:
                        zero_nodes.append(ctl_node)
            elif isinstance(node, ControlNode):
                data_node = node.get_data_node()
                in_dags[data_node] -= 1
                if in_dags[data_node] == 0:
                    zero_nodes.append(data_node)

    def schedule(self, msg):
        if msg.type == controller_pb2.MessageType.APPEND_FUNCTION:
            return platform_pb2.Message(
                type=platform_pb2.MessageType.BROADCAST,
                broadcast=platform_pb2.Broadcast(
                    controller_message=msg
                )
            )
        elif msg.type == controller_pb2.MessageType.APPEND_FUNCTION_ARG:
            arg = msg.append_function_arg
            func_id = arg.instance_id
            apply_worker_id = self._node_to_worker[func_id]
            return platform_pb2.Message(
                type=platform_pb2.MessageType.APPLY_TO_WORKER,
                apply_to_worker=platform_pb2.ApplyToWorker(
                    controller_message=msg,
                    worker_id=apply_worker_id
                )
            )
        elif msg.type == controller_pb2.MessageType.INVOKE_FUNCTION:
            invoke_func = msg.invoke_function
            func_id = invoke_func.instance_id
            apply_worker_id = self._node_to_worker[func_id]
            return platform_pb2.Message(
                type=platform_pb2.MessageType.APPLY_TO_WORKER,
                apply_to_worker=platform_pb2.ApplyToWorker(
                    controller_message=msg,
                    worker_id=apply_worker_id
                )
            )

class PathScheduler(Scheduler):
    class Path:
        def __init__(self):
            self._nodes: list[DAGNode] = []
            self._apply_to_worker = None
        def get(self):
            return self._nodes
        def add(self, node):
            self._nodes.append(node)
        def get_last_node(self):
            return self._nodes[-1]
        def set_apply_to_worker(self, worker_id):
            self._apply_to_worker = worker_id
        def get_apply_to_worker(self):
            return self._apply_to_worker
        
    def __init__(self, master_addr: str = "localhost:50051"):
        super().__init__(master_addr)
        self._node_to_worker = {}
        self._in_dags = {}
        self._paths: list[PathScheduler.Path] = []
        self._zero_nodes = []
        self._visited: dict[DAGNode, PathScheduler.Path] = {}
    
    def analyze(self, dag: DAG):
        nodes = dag.get_nodes()
        self._in_dags = {}
        for node in nodes:
            self._in_dags[node] = 0
        for node in nodes:
            if isinstance(node, DataNode):
                for ctl_node in node.get_succ_control_nodes():
                    self._in_dags[ctl_node] += 1
            elif isinstance(node, ControlNode):
                self._in_dags[node.get_data_node()] += 1

        self._zero_nodes = [node for node, in_degree in self._in_dags.items() if in_degree == 0]
        self._paths = []
        while len(self._zero_nodes) > 0:
            node = self._zero_nodes.pop()
            if isinstance(node, DataNode):
                if node.get_pre_control_node() is not None:
                    pre_ctl_node = node.get_pre_control_node()
                    path = self._visited[pre_ctl_node]
                    path.add(node)
                else:
                    path = self.Path()
                    self._paths.append(path)
                    path.add(node)
                self._visited[node] = path
                for ctl_node in node.get_succ_control_nodes():
                    self._in_dags[ctl_node] -= 1
                    if self._in_dags[ctl_node] == 0:
                        self._zero_nodes.append(ctl_node)
            elif isinstance(node, ControlNode):
                if len(node.get_pre_data_nodes()) > 0:
                    pre_data_node = node.get_pre_data_nodes()[0]
                    path = self._visited[pre_data_node]
                    path.add(node)
                else:
                    path = self.Path()
                    self._paths.append(path)
                    path.add(node)
                self._visited[node] = path
                data_node = node.get_data_node()
                self._in_dags[data_node] -= 1
                if self._in_dags[data_node] == 0:
                    self._zero_nodes.append(data_node)
        
        worker_index = 0
        for path in self._paths:
            path.set_apply_to_worker(self._workers[worker_index].worker_id)
            worker_index = (worker_index + 1) % len(self._workers)
        
        for path in self._paths:
            for node in path.get():
                metadata = node.metadata()
                self._node_to_worker[metadata['id']] = path.get_apply_to_worker()
    def schedule(self, msg):
        if msg.type == controller_pb2.MessageType.APPEND_FUNCTION:
            return platform_pb2.Message(
                type=platform_pb2.MessageType.BROADCAST,
                broadcast=platform_pb2.Broadcast(
                    controller_message=msg
                )
            )
        elif msg.type == controller_pb2.MessageType.APPEND_FUNCTION_ARG:
            arg = msg.append_function_arg
            func_id = arg.instance_id
            apply_worker_id = self._node_to_worker[func_id]
            return platform_pb2.Message(
                type=platform_pb2.MessageType.APPLY_TO_WORKER,
                apply_to_worker=platform_pb2.ApplyToWorker(
                    controller_message=msg,
                    worker_id=apply_worker_id
                )
            )
        elif msg.type == controller_pb2.MessageType.INVOKE_FUNCTION:
            invoke_func = msg.invoke_function
            func_id = invoke_func.instance_id
            apply_worker_id = self._node_to_worker[func_id]
            return platform_pb2.Message(
                type=platform_pb2.MessageType.APPLY_TO_WORKER,
                apply_to_worker=platform_pb2.ApplyToWorker(
                    controller_message=msg,
                    worker_id=apply_worker_id
                )
            )
        
class KeyPathScheduler(Scheduler):
    class Path:
        def __init__(self):
            self._nodes: list[DAGNode] = []
            self._apply_to_worker = None
            self._crush_node: ControlNode | None = None
            self._transmit_data_size = 0
        def set_crush_node(self, node):
            self._crush_node = node
        def get(self):
            return self._nodes
        def add(self, node):
            self._nodes.append(node)
        def get_last_node(self):
            return self._nodes[-1]
        def set_apply_to_worker(self, worker_id):
            self._apply_to_worker = worker_id
        def get_apply_to_worker(self) -> str | None:
            return self._apply_to_worker
        def set_transmit_data_size(self, size: int):
            self._transmit_data_size = size
        def get_transmit_data_size(self) -> int:
            return self._transmit_data_size
    def __init__(self, master_addr: str = "localhost:50051"):
        super().__init__(master_addr)
        self._node_to_worker = {}
        self._in_dags = {}
        self._paths: list[KeyPathScheduler.Path] = []
        self._origin_in_dags = {}
        self._paths: list[KeyPathScheduler.Path] = []
        self._visited: dict[str, KeyPathScheduler.Path] = {}
        self._crush_paths: dict[str, list[KeyPathScheduler.Path]] = {}

    def _topo(self):
        _zero_nodes = [node for node, in_degree in self._in_dags.items() if in_degree == 0 and node not in self._visited]
        while len(_zero_nodes) > 0:
            node = _zero_nodes.pop()
            if isinstance(node, DataNode):
                # 相当于图上的边，后面跟随的是下一个计算任务，通常需要放在同一个节点上，如果下一个任务有多个入度则代表冲突
                path = None
                if node.get_pre_control_node() is not None:
                    pre_ctl_node = node.get_pre_control_node()
                    path = self._visited[pre_ctl_node._id]
                    path.add(node)
                else:
                    path = self.Path()
                    self._paths.append(path)
                    path.add(node)
                self._visited[node._id] = path
                for ctl_node in node.get_succ_control_nodes():
                    self._in_dags[ctl_node] -= 1
                    if self._origin_in_dags[ctl_node] == 1:
                        _zero_nodes.append(ctl_node)
                    else:
                        # 冲突节点，设置断点
                        path.set_crush_node(node)
                        if node._id not in self._crush_paths:
                            self._crush_paths[node._id] = []
                        self._crush_paths[node._id].append(path)
            elif isinstance(node, ControlNode):
                if len(node.get_pre_data_nodes()) > 0:
                    pre_data_node = node.get_pre_data_nodes()[0]
                    path = self._visited[pre_data_node._id]
                    path.add(node)
                else:
                    path = self.Path()
                    self._paths.append(path)
                    path.add(node)
                self._visited[node._id] = path
                data_node = node.get_data_node()
                self._in_dags[data_node] -= 1
                if self._in_dags[data_node] == 0:
                    _zero_nodes.append(data_node)
        
    def analyze(self, dag: DAG):
        nodes = dag.get_nodes()
        self._in_dags = {}
        for node in nodes:
            self._in_dags[node] = 0
        for node in nodes:
            if isinstance(node, DataNode):
                for ctl_node in node.get_succ_control_nodes():
                    self._in_dags[ctl_node] += 1
            elif isinstance(node, ControlNode):
                self._in_dags[node.get_data_node()] += 1

        self._origin_in_dags = self._in_dags.copy()
        self._topo()
        worker_index = 0
        for path in self._paths:
            path.set_apply_to_worker(self._workers[worker_index].worker_id)
            worker_index = (worker_index + 1) % len(self._workers)
            
    def feedback(self, result: controller_pb2.ReturnResult):
        node_id = result.instance_id
        path = self._visited[node_id]
        path.set_transmit_data_size(result.value.size)

    def _find_crush_pathes(self, func_id: str) -> list[Path]:
        return self._crush_paths.get(func_id, [])

    def _find_best_worker(self, func_id: str) -> str:
        paths = self._find_crush_pathes(func_id)
        min_path = None
        for path in paths:
            if min_path is None:
                min_path = path
            else:
                if path.get_transmit_data_size() < min_path.get_transmit_data_size():
                    min_path = path

        for path in paths:
            if path != min_path:
                path.set_apply_to_worker(min_path.get_apply_to_worker())
        
        return min_path.get_apply_to_worker()

    def schedule(self, msg: controller_pb2.Message) -> platform_pb2.Message:
        if msg.type == controller_pb2.MessageType.APPEND_FUNCTION:
            return platform_pb2.Message(
                type=platform_pb2.MessageType.BROADCAST,
                broadcast=platform_pb2.Broadcast(
                    controller_message=msg
                )
            )
        elif msg.type == controller_pb2.MessageType.APPEND_FUNCTION_ARG:
            arg = msg.append_function_arg
            func_id = arg.instance_id
            if self._visited.get(func_id) is not None:
                apply_worker_id = self._visited[func_id].get_apply_to_worker()
                return platform_pb2.Message(
                    type=platform_pb2.MessageType.APPLY_TO_WORKER,
                    apply_to_worker=platform_pb2.ApplyToWorker(
                        controller_message=msg,
                        worker_id=apply_worker_id
                    )
                )
            else:
                apply_worker_id = self._find_best_worker(func_id)
                self._topo()
                return platform_pb2.Message(
                    type=platform_pb2.MessageType.APPLY_TO_WORKER,
                    apply_to_worker=platform_pb2.ApplyToWorker(
                        controller_message=msg,
                        worker_id=apply_worker_id
                    )
                )
        elif msg.type == controller_pb2.MessageType.INVOKE_FUNCTION:
            invoke_func = msg.invoke_function
            func_id = invoke_func.instance_id
            apply_worker_id = self._visited[func_id].get_apply_to_worker()
            return platform_pb2.Message(
                type=platform_pb2.MessageType.APPLY_TO_WORKER,
                apply_to_worker=platform_pb2.ApplyToWorker(
                    controller_message=msg,
                    worker_id=apply_worker_id
                )
            )