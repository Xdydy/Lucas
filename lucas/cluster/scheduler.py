from lucas.utils.logging import log
from lucas.workflow.dag import DAG, ControlNode, DAGNode, DataNode

from .protos import cluster_pb2, cluster_pb2_grpc, controller_pb2, platform_pb2
import grpc
import time

class Scheduler:
    def __init__(self, master_addr: str = "localhost:50051"):
        self._master_addr = master_addr
        
        workers = self.get_workers().workers
        self._workers = []
        for worker in workers:
            log.info(f"Worker {worker.worker_id} is available at {worker.host}:{worker.port} with worker rank {worker.worker_rank}")
            self._workers.append(worker)
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

    def schedule(self, msg: controller_pb2.Message) -> list[platform_pb2.Message]:
        # Implement scheduling logic here
        if msg.type == controller_pb2.MessageType.APPEND_FUNCTION:
            return [platform_pb2.Message(
                type=platform_pb2.MessageType.BROADCAST,
                broadcast=platform_pb2.Broadcast(
                    controller_message=msg
                )
            )]
        else:
            return [platform_pb2.Message(
                type=platform_pb2.MessageType.APPLY_TO_WORKER,
                apply_to_worker=platform_pb2.ApplyToWorker(
                    controller_message=msg
                )
            )]
    
    def feedback(self, result: controller_pb2.ReturnResult):
        pass

    def shutdown(self):
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

    def schedule(self, msg: controller_pb2.Message) -> list[platform_pb2.Message]:
        if msg.type == controller_pb2.MessageType.APPEND_FUNCTION:
            return [platform_pb2.Message(
                type=platform_pb2.MessageType.BROADCAST,
                broadcast=platform_pb2.Broadcast(
                    controller_message=msg
                )
            )]
        elif msg.type == controller_pb2.MessageType.APPEND_FUNCTION_ARG:
            arg = msg.append_function_arg
            func_id = arg.instance_id
            apply_worker_id = self._node_to_worker[func_id]
            log.info(f"Function {func_id} is assigned to worker {apply_worker_id}")
            return [platform_pb2.Message(
                type=platform_pb2.MessageType.APPLY_TO_WORKER,
                apply_to_worker=platform_pb2.ApplyToWorker(
                    controller_message=msg,
                    worker_id=apply_worker_id
                )
            )]
        elif msg.type == controller_pb2.MessageType.INVOKE_FUNCTION:
            invoke_func = msg.invoke_function
            func_id = invoke_func.instance_id
            apply_worker_id = self._node_to_worker[func_id]
            log.info(f"Function {func_id} is assigned to worker {apply_worker_id}")
            return [platform_pb2.Message(
                type=platform_pb2.MessageType.APPLY_TO_WORKER,
                apply_to_worker=platform_pb2.ApplyToWorker(
                    controller_message=msg,
                    worker_id=apply_worker_id
                )
            )]

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
    def schedule(self, msg: controller_pb2.Message) -> list[platform_pb2.Message]:
        if msg.type == controller_pb2.MessageType.APPEND_FUNCTION:
            return [platform_pb2.Message(
                type=platform_pb2.MessageType.BROADCAST,
                broadcast=platform_pb2.Broadcast(
                    controller_message=msg
                )
            )]
        elif msg.type == controller_pb2.MessageType.APPEND_FUNCTION_ARG:
            arg = msg.append_function_arg
            func_id = arg.instance_id
            apply_worker_id = self._node_to_worker[func_id]
            return [platform_pb2.Message(
                type=platform_pb2.MessageType.APPLY_TO_WORKER,
                apply_to_worker=platform_pb2.ApplyToWorker(
                    controller_message=msg,
                    worker_id=apply_worker_id
                )
            )]
        elif msg.type == controller_pb2.MessageType.INVOKE_FUNCTION:
            invoke_func = msg.invoke_function
            func_id = invoke_func.instance_id
            apply_worker_id = self._node_to_worker[func_id]
            return [platform_pb2.Message(
                type=platform_pb2.MessageType.APPLY_TO_WORKER,
                apply_to_worker=platform_pb2.ApplyToWorker(
                    controller_message=msg,
                    worker_id=apply_worker_id
                )
            )]
        
class KeyPathScheduler(Scheduler):
    class Path:
        """
        Path 表示 DAG 上的可串行的关键路径，包含路径上的若干节点. 冲突节点表示多条路径的汇合点，需要根据传输的数据量来决定后续路径的调度策略。
        """
        def __init__(self):
            self._nodes: list[DAGNode] = []
            self._apply_to_worker = None
            self._crush_node: ControlNode | None = None
            self._transmit_data_size = -1
        def set_crush_node(self, node):
            self._crush_node = node
        def get_crush_node(self):
            return self._crush_node
        def put_crush_node_in_nodes(self):
            if self._crush_node is not None:
                self._nodes.append(self._crush_node)
            self._crush_node = None
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
        # map controll node to paths that crush at this node
        self._crush_paths: dict[str, set[KeyPathScheduler.Path]] = {}
        self._ready_crush_controll_node: set[str] = set()
        self._unknown_requests: list[controller_pb2.Message] = []
        self._pending_nodes: list[tuple[DAGNode, KeyPathScheduler.Path | None]] = []
        self._scheduler_time = 0
    
    def get_total_scheduler_time(self):
        return self._scheduler_time

    def dfs(self, u: ControlNode, path: Path = None):
        assert isinstance(u, ControlNode)
        if u._id in self._visited:
            return
        if path is None:
            path = self.Path()
            self._paths.append(path)
        path.add(u)
        self._visited[u._id] = path
        for pre_edge in u.get_pre_data_nodes():
            path.add(pre_edge)
            self._visited[u._id] = path
        edge: DataNode = u.get_data_node()
        for v in edge.get_succ_control_nodes():
            self._in_dags[v] -= 1
            if self._origin_in_dags[v] > 1:
                path.set_crush_node(v)
                if v._id not in self._crush_paths:
                    self._crush_paths[v._id] = set()
                self._crush_paths[v._id].add(path)
                if len(self._crush_paths[v._id]) == self._origin_in_dags[v]:
                    self._ready_crush_controll_node.add(v._id)
            else:
                self.dfs(v, path)



    def step(self):
        while len(self._pending_nodes) > 0:
            node, path = self._pending_nodes.pop(0)
            self.dfs(node, path)
        
    def analyze(self, dag: DAG):
        """
        分析 DAG，构建关键路径，并为每条路径分配计算节点，在任务执行前调用预先分配部分计算节点
        
        """
        nodes = dag.get_nodes()
        self._in_dags = {}
        for node in nodes:
            if isinstance(node, ControlNode):
                self._in_dags[node] = 0
        for node in nodes:
            if isinstance(node, ControlNode):
                data_node = node.get_data_node()
                for ctl_node in data_node.get_succ_control_nodes():
                    self._in_dags[ctl_node] += 1

        self._origin_in_dags = self._in_dags.copy()
        self._pending_nodes = [(node, None) for node, in_degree in self._in_dags.items() if in_degree == 0 and node not in self._visited]
        self.step()
        worker_index = 0
        for path in self._paths:
            path.set_apply_to_worker(self._workers[worker_index].worker_id)
            worker_index = (worker_index + 1) % len(self._workers)
            
    def feedback(self, result: controller_pb2.ReturnResult):
        """
        反馈任务执行结果，更新关键路径的传输数据量信息
        """
        node_id = result.instance_id
        path = self._visited[node_id]
        path.set_transmit_data_size(result.value.size)

    def handle_ready_controll_nodes(self):
        successful_ctl_id = []
        for ctl_node_id in self._ready_crush_controll_node:
            paths = self._crush_paths[ctl_node_id]
            min_path = None
            for path in paths:
                if path.get_transmit_data_size() != -1:
                    min_path = None
                    break
                if min_path is None:
                    min_path = path
                else:
                    if path.get_transmit_data_size() < min_path.get_transmit_data_size():
                        min_path = path

            if min_path is None:
                continue
            successful_ctl_id.append(ctl_node_id)
            for path in paths:
                if path != min_path:
                    path.set_transmit_data_size(-1)
                else:
                    self._pending_nodes.append((path.get_crush_node(), path))
                    path.put_crush_node_in_nodes()
                    path.set_transmit_data_size(-1)

        self.step()
        for ctl_id in successful_ctl_id:
            self._ready_crush_controll_node.remove(ctl_id)
        
    
    def _handle_unknown_request(self, msg: controller_pb2.Message) -> platform_pb2.Message:
        def get_function_id() -> str:
            if msg.type == controller_pb2.MessageType.APPEND_FUNCTION_ARG:
                return msg.append_function_arg.instance_id
            elif msg.type == controller_pb2.MessageType.INVOKE_FUNCTION:
                return msg.invoke_function.instance_id
        func_id = get_function_id()
        if self._visited.get(func_id) is None:
            return None
        path = self._visited.get(func_id)
        apply_worker_id = path.get_apply_to_worker()
        if apply_worker_id is None:
            return None
        return platform_pb2.Message(
            type=platform_pb2.MessageType.APPLY_TO_WORKER,
            apply_to_worker=platform_pb2.ApplyToWorker(
                controller_message=msg,
                worker_id=apply_worker_id
            )
        )

    
    def handle_unknown_requests(self) -> list[platform_pb2.Message]:
        self.handle_ready_controll_nodes()
        msgs = []
        while len(self._unknown_requests) > 0:
            msg = self._unknown_requests.pop(0)
            platform_msg = self._handle_unknown_request(msg)
            if platform_msg is not None:
                msgs.append(platform_msg)
        return msgs

    def schedule(self, msg: controller_pb2.Message) -> platform_pb2.Message:
        """
        决策每个报文的调度策略
        """
        start_t = time.time()
        msgs = []
        if msg.type == controller_pb2.MessageType.APPEND_FUNCTION:
            msgs.append(platform_pb2.Message(
                type=platform_pb2.MessageType.BROADCAST,
                broadcast=platform_pb2.Broadcast(
                    controller_message=msg
                )
            ))
        elif msg.type == controller_pb2.MessageType.APPEND_FUNCTION_ARG:
            arg = msg.append_function_arg
            func_id = arg.instance_id
            if self._visited.get(func_id) is not None and self._visited[func_id].get_apply_to_worker() is not None:
                apply_worker_id = self._visited[func_id].get_apply_to_worker()
                log.info(f"Function {func_id} is assigned to worker {apply_worker_id}")
                msgs.append(platform_pb2.Message(
                    type=platform_pb2.MessageType.APPLY_TO_WORKER,
                    apply_to_worker=platform_pb2.ApplyToWorker(
                        controller_message=msg,
                        worker_id=apply_worker_id
                    )
                ))
            else:
                self._unknown_requests.append(msg)  
        elif msg.type == controller_pb2.MessageType.INVOKE_FUNCTION:
            invoke_func = msg.invoke_function
            func_id = invoke_func.instance_id
            if self._visited.get(func_id) is None or self._visited[func_id].get_apply_to_worker() is None:
                self._unknown_requests.append(msg)
            else:
                apply_worker_id = self._visited[func_id].get_apply_to_worker()
                log.info(f"Function {func_id} is assigned to worker {apply_worker_id}")
                msgs.append(platform_pb2.Message(
                    type=platform_pb2.MessageType.APPLY_TO_WORKER,
                    apply_to_worker=platform_pb2.ApplyToWorker(
                        controller_message=msg,
                        worker_id=apply_worker_id
                    )
                ))
        msgs += self.handle_unknown_requests()
        self._scheduler_time += time.time() - start_t
        return msgs
        
    def shutdown(self):
        self._node_to_worker.clear()
        self._in_dags.clear()
        self._paths.clear()
        self._origin_in_dags.clear()
        self._paths.clear()
        self._visited.clear()
        self._crush_paths.clear()

