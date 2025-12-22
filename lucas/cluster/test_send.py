import grpc
import cloudpickle
from .protos import store_pb2_grpc, store_pb2
from Crypto.Random import get_random_bytes

class GrpcOptions:
    options = [
        ('grpc.max_send_message_length', 100 * 1024 * 1024),
        ('grpc.max_receive_message_length', 100 * 1024 * 1024),
    ]
size_kb = 20000
class GrpcClient:
    def put_object(self, key: str, data, chunk_size: int = 4 * 1024 * 1024) -> str:
        """
        Stream the serialized object to the server in chunks.
        Returns the reference from server.
        """
        serialized_data = cloudpickle.dumps(data)

        def request_generator():
            # send the key in the first message, then stream data chunks
            for i in range(0, len(serialized_data), chunk_size):
                chunk = serialized_data[i : i + chunk_size]
                yield store_pb2.PutObjectRequest(key=key, data=chunk)

        channel = grpc.insecure_channel("localhost:50051", options=GrpcOptions.options)
        stub = store_pb2_grpc.StoreServiceStub(channel)
        response = stub.PutObject(request_generator())
        # try to close channel if supported (safe no-op on many grpc versions)
        try:
            channel.close()
        except Exception:
            pass
        return response.ref
    def get_object(self, key: str):
        request = store_pb2.GetObjectRequest(ref=key)
        channel = grpc.insecure_channel(
            'localhost:50051',
            options=GrpcOptions.options
        )
        stub = store_pb2_grpc.StoreServiceStub(channel)
        response_stream = stub.GetObject(request)
        # reassemble streamed chunks from server
        buf = bytearray()
        for response in response_stream:
            if response.error:
                raise KeyError(response.error)
            if response.data:
                buf.extend(response.data)
        try:
            obj = cloudpickle.loads(bytes(buf))
        finally:
            try:
                channel.close()
            except Exception:
                pass
        return obj

if __name__ == "__main__":
    client = GrpcClient()

    # Put an object
    key = "example_key"
    data = get_random_bytes(size_kb * 1024)  # Example data
    client.put_object(key, data)

    # Get the object
    retrieved_data = client.get_object(key)
    print(retrieved_data)  # Output: {'foo': 'bar'}
    