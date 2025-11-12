from lucas.utils.logging import log

from .protos import cluster_pb2, cluster_pb2_grpc
from queue import Queue
import grpc

class Scheduler:
    def __init__(self, master_addr: str):
        self._master_addr = master_addr
        self._connect_to_master()
        
        self._workers = self.get_workers().workers
        for worker in self._workers:
            log.info(f"Worker {worker.worker_id} is available at {worker.host}:{worker.port} with worker rank {worker.worker_rank}")
    def _connect_to_master(self):
        # Connect to the master server
        self._channel = grpc.insecure_channel(self._master_addr)
        self._stub = cluster_pb2_grpc.ClusterServiceStub(self._channel)
        self._msg_queue = Queue()
        self._response_stream = self._stub.Session(self._message_generator())
    def _message_generator(self):
        while True:
            msg = self._msg_queue.get()
            if msg is None:  # Sentinel to end the stream
                break
            yield msg
    def get_workers(self) -> cluster_pb2.GetWorkersResponse:
        request = cluster_pb2.GetWorkersRequest()
        channel = grpc.insecure_channel(self._master_addr)
        stub = cluster_pb2_grpc.ClusterServiceStub(channel)
        response = stub.GetWorkers(request)
        return response
    
    def shutdown(self):
        self._msg_queue.put(None)  # Send sentinel to end the stream
        self._channel.close()