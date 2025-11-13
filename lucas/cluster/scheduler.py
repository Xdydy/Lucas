from lucas.utils.logging import log

from .protos import cluster_pb2, cluster_pb2_grpc, controller_pb2, platform_pb2
from queue import Queue
import grpc

class Scheduler:
    def __init__(self, master_addr: str):
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
        pass