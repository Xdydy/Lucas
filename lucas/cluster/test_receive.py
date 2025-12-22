from concurrent import futures
import grpc
import cloudpickle
from .protos import store_pb2_grpc, store_pb2

class GrpcOptions:
    options = [
        ('grpc.max_send_message_length', 100 * 1024 * 1024),
        ('grpc.max_receive_message_length', 100 * 1024 * 1024),
    ]

class StoreService(store_pb2_grpc.StoreServiceServicer):
    def __init__(self):
        self._store = {}

    def GetObject(self, request, context):
        request: store_pb2.GetObjectRequest
        key = request.ref
        if key not in self._store:
            yield store_pb2.GetObjectResponse(
                error=f"Object with key {key} not found."
            )
            return
        # Stream the serialized object in chunks to avoid sending a huge
        # single message. The client will reassemble the bytes and
        # cloudpickle.loads them.
        data = self._store[key]
        serialized = cloudpickle.dumps(data)
        chunk_size = 4 * 1024 * 1024  # 4 MB
        for i in range(0, len(serialized), chunk_size):
            yield store_pb2.GetObjectResponse(data=serialized[i : i + chunk_size])

    def PutObject(self, request_stream, context):
        # The client may stream multiple PutObjectRequest messages carrying
        # parts of the serialized object. Reassemble the bytes and decode once.
        received_key = None
        buffer = bytearray()
        for request in request_stream:
            request: store_pb2.PutObjectRequest
            if received_key is None:
                received_key = request.key
            # accumulate bytes
            if request.data:
                buffer.extend(request.data)

        if received_key is None:
            return store_pb2.PutObjectResponse(ref="", error="no key provided")

        try:
            obj = cloudpickle.loads(bytes(buffer))
        except Exception as e:
            return store_pb2.PutObjectResponse(ref=received_key, error=str(e))

        self._store[received_key] = obj
        return store_pb2.PutObjectResponse(ref=received_key)
    
    def DeleteObject(self, request, context):
        request: store_pb2.DeleteObjectRequest
        key = request.key
        if key in self._store:
            del self._store[key]
        return store_pb2.DeleteObjectResponse()
    

if __name__ == "__main__":
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=GrpcOptions.options
    )
    store_pb2_grpc.add_StoreServiceServicer_to_server(StoreService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("StoreService gRPC server started on port 50051")
    server.wait_for_termination()