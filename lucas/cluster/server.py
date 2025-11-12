import grpc
import cloudpickle
import uuid
import threading
from lucas.utils.logging import log
from concurrent import futures
from .protos import cluster_pb2_grpc, cluster_pb2, controller_pb2, controller_pb2_grpc, store_pb2, store_pb2_grpc
from .executor import ExecutorSandBox, FunctionExecutor, ClassExecutor

from argparse import ArgumentParser
from queue import Queue
from typing import Any
from google.protobuf import empty_pb2

class ControllerContext:
    def __init__(self, peer_address: str):
        self._peer_address = peer_address
        self._channel = grpc.insecure_channel(peer_address)
        self._stub = controller_pb2_grpc.ControllerServiceStub(self._channel)
        # store stub to fetch object bytes from remote controller's store service
        self._store_stub = store_pb2_grpc.StoreServiceStub(self._channel)
        self._msg_queue = Queue()
        # queue where this ControllerContext will publish incoming controller responses
        self._outgoing_queue = Queue()
        self._resp_stream = self._stub.Session(self._message_generator())
        self._result_lock = threading.Lock()
        # map obj_id -> concurrent.futures.Future
        self._results = {}
        self._resp_thread = threading.Thread(target=self._receive_messages, daemon=True)
        self._resp_thread.start()
        self._test()
    def _test(self):
        resp: controller_pb2.Ack = self._stub.Ping(empty_pb2.Empty())
        log.info(f"Received response from controller: {resp.message}")
    def _message_generator(self):
        while True:
            msg = self._msg_queue.get()
            if msg is None:
                break
            yield msg
    def send_message(self, msg: controller_pb2.Message):
        self._msg_queue.put(msg)
    def _receive_messages(self):
        for response in self._resp_stream:
            response: controller_pb2.Message
            if response.type == controller_pb2.MessageType.RT_RESULT:
                self._handle_rt_result(response.return_result)
            elif response.type == controller_pb2.MessageType.ACK:
                self._handle_ack(response.ack)
            else:
                log.warning(f"Unknown response type: {response.type}")
            # publish raw controller message to outgoing queue for master/session forwarding
            try:
                self._outgoing_queue.put(response)
            except Exception:
                log.exception("Failed to put controller response into outgoing queue")

    def get_outgoing_queue(self):
        return self._outgoing_queue
    def _handle_rt_result(self, rt_result: controller_pb2.ReturnResult):
        log.debug(f"Received runtime result: {rt_result.value}")
        if rt_result.value.type == controller_pb2.Data.ObjectType.OBJ_REF:
            obj_id = rt_result.value.ref
            with self._result_lock:
                self._results[obj_id] = None  # Placeholder for the result
        else:
            log.warning(f"Received non-object result: {rt_result.value}")
    def _handle_ack(self, ack: controller_pb2.Ack):
        if ack.error != "":
            log.error(f"Error in ACK: {ack.error}")
    def wait_for_result(self, obj_id: str) -> futures.Future:
        with self._result_lock:
            if obj_id in self._results:
                future = futures.Future()
                future.set_result(self._results[obj_id])
                return future
            else:
                future = futures.Future()
                self._results[obj_id] = future
                return future

class Controller(controller_pb2_grpc.ControllerServiceServicer):
    def __init__(self, data_store: "StorageService"):
        super().__init__()
        self._funcs: dict[str, FunctionExecutor] = {}
        self._classes: dict[str, ClassExecutor] = {}
        self._pending_funcs = []
        self._data_store = data_store

    def _transmit_data(self, data: controller_pb2.Data):
        data_type = data.type
        if data_type == controller_pb2.Data.ObjectType.OBJ_REF:
            obj_id = data.ref
            if self._data_store.get(obj_id) is None:
                log.error(f"Object reference {obj_id} not found.")
                raise RuntimeError(f"Object reference {obj_id} not found.")
            return self._data_store.get(obj_id)
        elif data_type == controller_pb2.Data.ObjectType.OBJ_ENCODED:
            obj_data = data.encoded
            obj = cloudpickle.loads(obj_data)
            return obj
    
    def _transmit_result(self, result, session_id, instance_id, function_name) -> controller_pb2.Data:
        obj_id = f"{session_id}_{instance_id}_{function_name}"
        self._data_store.put(obj_id, result)
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

    def apply(self, request) -> controller_pb2.Message:
        request: controller_pb2.Message
        log.info(f"Received controller message: {request}")
        if request.type == controller_pb2.MessageType.APPEND_FUNCTION:
            resp = self._append_function(request.append_function)
        elif request.type == controller_pb2.MessageType.APPEND_FUNCTION_ARG:
            resp = self._append_function_arg(request.append_function_arg)
        elif request.type == controller_pb2.MessageType.INVOKE_FUNCTION:
            resp = self._invoke_function(request.invoke_function)
        return resp
    def Session(self, request_iterator, context):
        for request in request_iterator:
            resp = self.apply(request)
            yield resp
    def Ping(self, request, context):
        return controller_pb2.Ack(
            message="Pong")

class StorageService(store_pb2_grpc.StoreServiceServicer):
    def __init__(self):
        super().__init__()
        self._data_store = {}

    def GetObject(self, request, context):
        request: store_pb2.GetObjectRequest
        key = request.ref
        data = self.get(key)
        if data is None:
            return store_pb2.GetObjectResponse(
                error=f"Object with key {key} not found."
            )
        return store_pb2.GetObjectResponse(data=cloudpickle.dumps(data))
    
    def PutObject(self, request, context):
        request: store_pb2.PutObjectRequest
        data = request.data
        key = request.key
        self.put(key, data)
        return store_pb2.PutObjectResponse(ref=key)
    
    def put(self, key: str, data: Any):
        self._data_store[key] = data
        log.info(f"Data stored with key: {key}")
    def get(self, key: str) -> Any:
        if key not in self._data_store:
            return None
        return self._data_store[key]

class Master(cluster_pb2_grpc.ClusterServiceServicer):
    class ControllerMetadata:
        def __init__(self, host: str, port: int, worker_id: str, rank: int):
            self._host = host
            self._port = port
            self._worker_id = worker_id
            self._rank = rank
            self._controller = ControllerContext(f"{host}:{port}")
            
    def __init__(self, controller: Controller):
        super().__init__()
        self._controllers: dict[str, Master.ControllerMetadata] = {}
        self._controller = controller

    def _apply_to_worker(self, apply_to_worker_request: cluster_pb2.ApplyToWorker):
        worker_id = apply_to_worker_request.worker_id
        controller_message = apply_to_worker_request.controller_message
        if worker_id == None or worker_id not in self._controllers:
            # Master Controller
            # apply locally and convert controller response to cluster Message
            resp = self._controller.apply(controller_message)
            return resp
        else:
            context = self._controllers[worker_id]._controller
            context.send_message(controller_message)

    def _broadcast(self, broadcast_request: cluster_pb2.Broadcast) -> cluster_pb2.Message:
        controller_message = broadcast_request.controller_message
        self._controller.broadcast(controller_message)
        return controller_message

    def Session(self, request_iterator, context):
        """
        Bidirectional session: accept incoming cluster.Messages and forward to controllers (local or worker).
        Whenever any controller (local or remote) produces a response, convert it to cluster Message
        (using Ack.message to carry object refs or errors) and yield it back to the client immediately.
        """
        import time

        outgoing_q = Queue()
        stop_event = threading.Event()

        # track which worker listeners have been started for this session
        subscribed_workers = set()
        listener_threads = []

        def request_reader():
            try:
                for request in request_iterator:
                    request: cluster_pb2.Message
                    log.info(f"Received session request: {request}")
                    if request.type == cluster_pb2.MessageType.APPLY_TO_WORKER:
                        req = request.apply_to_worker
                        worker_id = req.worker_id
                        controller_message = req.controller_message
                        if worker_id is None or worker_id not in self._controllers:
                            # handle locally and publish response
                            try:
                                resp = self._controller.apply(controller_message)
                                outgoing_q.put(("local", resp))
                            except Exception as e:
                                log.exception("Error applying to local controller")
                                outgoing_q.put(("local", controller_pb2.Message(type=controller_pb2.MessageType.ACK, ack=controller_pb2.Ack(error=str(e)))))
                        else:
                            # forward to worker controller asynchronously
                            meta = self._controllers[worker_id]
                            meta._controller.send_message(controller_message)
                    elif request.type == cluster_pb2.MessageType.BROADCAST:
                        # try to call local broadcast if exists, otherwise send to all controllers
                        try:
                            self._controller.broadcast(request.broadcast.controller_message)
                        except Exception:
                            for meta in list(self._controllers.values()):
                                try:
                                    meta._controller.send_message(request.broadcast.controller_message)
                                except Exception:
                                    log.exception("Failed to send broadcast to worker")
                    else:
                        log.error(f"Unknown message type received: {request.type}")
            except Exception:
                log.exception("Error reading session requests")
            finally:
                stop_event.set()
                # put sentinel to unblock main sender
                try:
                    outgoing_q.put(None)
                except Exception:
                    pass

        def worker_listener(meta: Master.ControllerMetadata):
            q = None
            try:
                q = meta._controller.get_outgoing_queue()
            except Exception:
                log.exception("ControllerContext has no outgoing queue")
                return
            while not stop_event.is_set():
                try:
                    msg = q.get()
                except Exception:
                    continue
                # publish tuple (worker_id, controller_message)
                outgoing_q.put((meta._worker_id, msg))

        def monitor_new_controllers():
            while not stop_event.is_set():
                for wid, meta in list(self._controllers.items()):
                    if wid not in subscribed_workers:
                        t = threading.Thread(target=worker_listener, args=(meta,), daemon=True)
                        t.start()
                        listener_threads.append(t)
                        subscribed_workers.add(wid)
                time.sleep(0.5)

        # start background threads
        req_thread = threading.Thread(target=request_reader, daemon=True)
        req_thread.start()
        monitor_thread = threading.Thread(target=monitor_new_controllers, daemon=True)
        monitor_thread.start()

        # main loop: forward controller responses to client as cluster messages
        try:
            while not stop_event.is_set():
                item = outgoing_q.get()
                if item is None:
                    break
                source, ctrl_msg = item
                # ctrl_msg is a controller_pb2.Message
                ctrl_msg: controller_pb2.Message
                try:
                    yield cluster_pb2.Message(
                        type=cluster_pb2.MessageType.RT_RESULT,
                        return_result=cluster_pb2.ReturnResult(
                            controller_message=ctrl_msg
                        )
                    )
                except Exception:
                    log.exception("Error converting controller message to cluster message")
        finally:
            stop_event.set()
            # attempt to join threads briefly
            try:
                req_thread.join(timeout=1)
            except Exception:
                pass
            try:
                monitor_thread.join(timeout=1)
            except Exception:
                pass

    def AddWorkerCommand(self, request, context):
        return self.addWorker(request)
    

    
    def addWorker(self, add_worker_request: cluster_pb2.AddWorker):
        worker_metadata = Master.ControllerMetadata(
            add_worker_request.host,
            add_worker_request.port,
            add_worker_request.worker_id,
            add_worker_request.worker_rank
        )
        self._controllers[add_worker_request.worker_id] = worker_metadata
        log.info(f"Worker {add_worker_request.worker_id} added.")
        return cluster_pb2.Ack(
            message=f"Worker {add_worker_request.worker_id} added successfully."
        )
    def removeWorker(self, remove_worker_request: cluster_pb2.RemoveWorker):
        if remove_worker_request.worker_id in self._controllers:
            del self._controllers[remove_worker_request.worker_id]
            log.info(f"Worker {remove_worker_request.worker_id} removed.")
            return cluster_pb2.Ack(
                message=f"Worker {remove_worker_request.worker_id} removed successfully."
            )
        else:
            log.error(f"Worker {remove_worker_request.worker_id} not found.")
            return cluster_pb2.Ack(
                error=f"Worker {remove_worker_request.worker_id} not found."
            )

    def RemoveWorkerCommand(self, request, context):
        return self.removeWorker(request)

class Worker:
    def __init__(self, master_address: str, worker_host: str, worker_port: int,controller: Controller, rank=1):
        super().__init__()
        self._worker_id = str(uuid.uuid4())
        self._master_address = master_address
        self._worker_host = worker_host
        self._worker_port = worker_port
        self._rank = rank
        self._controller = controller
        self._connect_to_master()
    def _connect_to_master(self):
        self._channel = grpc.insecure_channel(self._master_address)
        self._stub = cluster_pb2_grpc.ClusterServiceStub(self._channel)
        # communicate to master
        resp : cluster_pb2.Ack = self._stub.AddWorkerCommand(cluster_pb2.AddWorker(
            host=self._worker_host,
            port=self._worker_port,
            worker_id=self._worker_id,
            worker_rank=self._rank
        ))
        if resp.error != "":
            log.error(f"Error adding worker: {resp.error}")
        else:
            log.info(resp.message)



if __name__ == "__main__":
    arg_parser = ArgumentParser()
    role_parser = arg_parser.add_subparsers(dest="role", required=True)
    
    master_parser = role_parser.add_parser("master", help="Start the master server")
    worker_parser = role_parser.add_parser("worker", help="Start a worker server")

    master_parser.add_argument("--port", type=int, help="Port for the master server to listen on")

    worker_parser.add_argument("--master_address", type=str, help="Address of the master server", required=True)
    worker_parser.add_argument("--worker_host", type=str, help="Host for the worker server", required=True)
    worker_parser.add_argument("--worker_port", type=int, help="Port for the worker server to listen on", required=True)
    worker_parser.add_argument("--rank", type=int, help="Rank of the worker", default=1)

    args = arg_parser.parse_args()
    store_service = StorageService()
    controller = Controller(store_service)
    if args.role == "master":
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        store_pb2_grpc.add_StoreServiceServicer_to_server(store_service, server)
        cluster_pb2_grpc.add_ClusterServiceServicer_to_server(Master(controller), server)
        controller_pb2_grpc.add_ControllerServiceServicer_to_server(controller, server)
        server.add_insecure_port(f"[::]:{args.port}")
        server.start()
        log.info(f"Master server started on port {args.port}")
        server.wait_for_termination()
    elif args.role == "worker":
        # Worker implementation would go here
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        controller_pb2_grpc.add_ControllerServiceServicer_to_server(controller, server)
        store_pb2_grpc.add_StoreServiceServicer_to_server(store_service, server)
        server.add_insecure_port(f"[::]:{args.worker_port}")
        server.start()
        worker = Worker(
            master_address=args.master_address,
            worker_host=args.worker_host,
            worker_port=args.worker_port,
            controller=controller,
            rank=args.rank
        )
        server.wait_for_termination()
