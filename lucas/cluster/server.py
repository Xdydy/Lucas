import grpc
import cloudpickle
import uuid
from lucas.utils.logging import log
from concurrent import futures
from .protos import cluster_pb2_grpc, cluster_pb2, controller_pb2, controller_pb2_grpc
from .executor import ExecutorSandBox, FunctionExecutor, ClassExecutor

from argparse import ArgumentParser
from queue import Queue

class Controller(controller_pb2_grpc.ControllerServiceServicer):
    def __init__(self):
        super().__init__()
        self._funcs: dict[str, FunctionExecutor] = {}
        self._classes: dict[str, ClassExecutor] = {}
        self._pending_funcs = []
        self._data_obj = {}

    def _transmit_data(self, data: controller_pb2.Data):
        data_type = data.type
        if data_type == controller_pb2.Data.ObjectType.OBJ_REF:
            obj_id = data.ref
            if obj_id not in self._data_obj:
                log.error(f"Object reference {obj_id} not found.")
                raise RuntimeError(f"Object reference {obj_id} not found.")
            return self._data_obj[obj_id]
        elif data_type == controller_pb2.Data.ObjectType.OBJ_ENCODED:
            obj_data = data.encoded
            obj = cloudpickle.loads(obj_data)
            return obj
    
    def _transmit_result(self, result, session_id, instance_id, function_name) -> controller_pb2.Data:
        obj_id = f"{session_id}_{instance_id}_{function_name}"
        self._data_obj[obj_id] = result
        return controller_pb2.Data(
            type=controller_pb2.Data.ObjectType.OBJ_REF,
            ref=obj_id
        )

    def _append_function(self, append_fn_request: controller_pb2.AppendFunction) -> controller_pb2.Message:
        function_name = append_fn_request.function_name
        function_code = append_fn_request.function_code
        fn = cloudpickle.loads(function_code)
        function_params = append_fn_request.params
        executor = FunctionExecutor(fn, function_params)
        self._funcs[function_name] = executor
        log.info(f"Appended function: {function_name}")
        return controller_pb2.Message(
            type=controller_pb2.MessageType.ACK,
            ack=controller_pb2.Ack(
                message=f"Function {function_name} appended successfully."
            )
        )
    def _append_function_arg(self, append_fn_arg_request: controller_pb2.AppendFunctionArg) -> controller_pb2.Message:
        function_name = append_fn_arg_request.function_name
        session_id = append_fn_arg_request.session_id
        instance_id = append_fn_arg_request.instance_id
        args_data = append_fn_arg_request.value
        param_name = append_fn_arg_request.param_name
        if function_name not in self._funcs:
            log.error(f"Function {function_name} not found.")
            return controller_pb2.Message(
                type=controller_pb2.MessageType.ACK,
                error=controller_pb2.Ack(
                    error=f"Function {function_name} not found."
                )
            )
        executor = self._funcs[function_name]
        sandbox = executor.create_instance(instance_id)
        data = self._transmit_data(args_data)
        sandbox.apply_args({param_name: data})
        log.info(f"Appended args for function: {function_name}, instance: {instance_id}")
        if sandbox.can_run():
            log.info(f"Function {function_name} is ready to run.")
            result = sandbox.run()
            result_data = self._transmit_result(result, session_id, instance_id, function_name)
            log.info(f"Invoked function: {function_name}")
            return controller_pb2.Message(
                type=controller_pb2.MessageType.RT_RESULT,
                return_result=controller_pb2.ReturnResult(
                    value=result_data
                )
            )
        else:
            log.info(f"Function {function_name} is not ready to run.")
            return controller_pb2.Message(
                type=controller_pb2.MessageType.ACK,
                ack=controller_pb2.Ack(
                    message=f"Args for function {function_name}, instance {instance_id} appended successfully."
                )
            )
    def _invoke_function(self, invoke_fn_request: controller_pb2.InvokeFunction) -> controller_pb2.Message:
        function_name = invoke_fn_request.function_name
        instance_id = invoke_fn_request.instance_id
        if function_name not in self._funcs:
            log.error(f"Function {function_name} not found.")
            return controller_pb2.Message(
                type=controller_pb2.MessageType.ACK,
                error=controller_pb2.Ack(
                    error=f"Function {function_name} not found."
                )
            )
        executor = self._funcs[function_name]
        sandbox = executor.create_instance(instance_id)
        sandbox.set_run()
        if sandbox.can_run():
            result = sandbox.run()
            result_data = self._transmit_result(result, invoke_fn_request.session_id, instance_id, function_name)
            log.info(f"Invoked function: {function_name}")
            return controller_pb2.Message(
                type=controller_pb2.MessageType.RT_RESULT,
                return_result=controller_pb2.ReturnResult(
                    value=result_data
                )
            )
        else:
            log.info(f"Function {function_name} is not ready to run.")
            return controller_pb2.Message(
                type=controller_pb2.MessageType.ACK,
                ack=controller_pb2.Ack(
                    message=f"Function {function_name} is not ready to run."
                )
            )
    def Session(self, request_iterator, context):
        for request in request_iterator:
            request: controller_pb2.Message
            log.info(f"Received controller message: {request}")
            if request.type == controller_pb2.MessageType.APPEND_FUNCTION:
                resp = self._append_function(request.append_function)
            elif request.type == controller_pb2.MessageType.APPEND_FUNCTION_ARG:
                resp = self._append_function_arg(request.append_function_arg)
            elif request.type == controller_pb2.MessageType.INVOKE_FUNCTION:
                resp = self._invoke_function(request.invoke_function)
            yield resp

class Master(cluster_pb2_grpc.ClusterServiceServicer):
    class WorkerMetadata:
        def __init__(self, host: str, port: int, worker_id: str, rank: int):
            self._host = host
            self._port = port
            self._worker_id = worker_id
            self._rank = rank
            
    def __init__(self, controller: Controller):
        super().__init__()
        self._workers: dict[str, Master.WorkerMetadata] = {}
        self._controller = controller

    def Session(self, request_iterator, context):
        for request in request_iterator:
            request: cluster_pb2.Message
            log.info(f"Received session request: {request}")
            if request.type == cluster_pb2.MessageType.ADD_WORKER:
                add_worker_request = request.add_worker
                worker_metadata = Master.WorkerMetadata(
                    add_worker_request.host,
                    add_worker_request.port,
                    add_worker_request.worker_id,
                    add_worker_request.worker_rank
                )
                self._workers[add_worker_request.worker_id] = worker_metadata
                log.info(f"Worker {add_worker_request.worker_id} added.")
            elif request.type == cluster_pb2.MessageType.REMOVE_WORKER:
                remove_worker_request = request.remove_worker
                if remove_worker_request.worker_id in self._workers:
                    del self._workers[remove_worker_request.worker_id]
                    log.info(f"Worker {remove_worker_request.worker_id} removed.")
            else:
                log.error(f"Unknown message type received: {request.type}")


class Worker:
    def __init__(self, master_address: str, worker_host: str, worker_port: int,controller: Controller, rank=1):
        super().__init__()
        self._worker_id = str(uuid.uuid4())
        self._master_address = master_address
        self._worker_host = worker_host
        self._worker_port = worker_port
        self._rank = rank
        self._controller = controller
    def _connect_to_master(self):
        self._channel = grpc.insecure_channel(self._master_address)
        self._stub = cluster_pb2_grpc.ClusterServiceStub(self._channel)
        self._cluster_msg_queue = Queue()
        # communicate to master
        self._resp_stream = self._stub.Session(self._generate_cluster_session_messages())
    
    def _receive_cluster_messages(self):
        for response in self._resp_stream:
            log.info(f"Received cluster message: {response}")
            # Handle different types of messages from the master
            response: cluster_pb2.Message
            if response.type == cluster_pb2.MessageType.ACK:
                # Process the message accordingly
                pass

    def _generate_cluster_session_messages(self):
        # Example of sending an ADD_WORKER message
        add_worker_msg = cluster_pb2.Message(
            type=cluster_pb2.MessageType.ADD_WORKER,
            add_worker=cluster_pb2.AddWorker(
                host=self._worker_host,
                port=self._worker_port,
                worker_id=self._worker_id,
                worker_rank=self._rank
            )
        )
        yield add_worker_msg
        # Additional messages can be yielded here
        while True:
            msg = self._cluster_msg_queue.get()
            yield msg



if __name__ == "__main__":
    arg_parser = ArgumentParser()
    role_parser = arg_parser.add_subparsers(dest="role", required=True)
    
    master_parser = role_parser.add_parser("master", help="Start the master server")
    worker_parser = role_parser.add_parser("worker", help="Start a worker server")

    master_parser.add_argument("port", type=int, help="Port for the master server to listen on")

    worker_parser.add_argument("master_address", type=str, help="Address of the master server", required=True)
    worker_parser.add_argument("worker_host", type=str, help="Host for the worker server", required=True)
    worker_parser.add_argument("worker_port", type=int, help="Port for the worker server to listen on", required=True)
    worker_parser.add_argument("rank", type=int, help="Rank of the worker", default=1)

    args = arg_parser.parse_args()
    controller = Controller()
    if args.role == "master":
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        cluster_pb2_grpc.add_ClusterServiceServicer_to_server(Master(controller), server)
        controller_pb2_grpc.add_ControllerServiceServicer_to_server(controller)
        server.add_insecure_port(f"[::]:{args.port}")
        server.start()
        log.info(f"Master server started on port {args.port}")
        server.wait_for_termination()
    elif args.role == "worker":
        # Worker implementation would go here
        worker = Worker(
            master_address=args.master_address,
            worker_host=args.worker_host,
            worker_port=args.worker_port,
            controller=controller,
            rank=args.rank
        )
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        controller_pb2_grpc.add_ControllerServiceServicer_to_server(controller, server)
        server.add_insecure_port(f"[::]:{args.worker_address}")
        server.start()
        server.wait_for_termination()        
        log.info(f"Worker server started on port {args.worker_address}, connected to master at {args.master_address}")
