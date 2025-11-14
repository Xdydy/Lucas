from lucas.utils.logging import log
from lucas.workflow.dag import DAG, ControlNode, DataNode

from .protos import cluster_pb2, cluster_pb2_grpc, controller_pb2, platform_pb2
import grpc

class Scheduler:
    def __init__(self, master_addr: str = "localhost:50051"):
        self._master_addr = master_addr
        
        self._workers = self.get_workers().workers
        for worker in self._workers:
            log.info(f"Worker {worker.worker_id} is available at {worker.host}:{worker.port} with worker rank {worker.worker_rank}")
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