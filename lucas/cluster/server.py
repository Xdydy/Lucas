import grpc
import cloudpickle
import uuid
import threading
from lucas.utils.logging import log
from concurrent import futures
from .protos import cluster_pb2_grpc, cluster_pb2, controller_pb2, controller_pb2_grpc, store_pb2, store_pb2_grpc, platform_pb2, platform_pb2_grpc
from .executor import ExecutorSandBox, FunctionExecutor, ClassExecutor

from argparse import ArgumentParser
from queue import Queue
from typing import Any, Callable, List
from google.protobuf import empty_pb2

class ControllerContext:
    def __init__(self, peer_address: str):
        self._peer_address = peer_address
        self._channel = grpc.insecure_channel(peer_address)
        self._stub = controller_pb2_grpc.ControllerServiceStub(self._channel)
        # store stub to fetch object bytes from remote controller's store service
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

class StoreContext:
    def __init__(self, peer_address: str):
        self._peer_address = peer_address
        self._channel = grpc.insecure_channel(peer_address)
        self._stub = store_pb2_grpc.StoreServiceStub(self._channel)
        self._resp_stream = self._stub.PublishSession(empty_pb2.Empty())
        self._subscribe_stream = self._stub.Subscribe(empty_pb2.Empty())
        self._outgoing_queue = Queue()
        self._subscribe_outgoing_queue = Queue()
        self._resp_thread = threading.Thread(target=self._receive_messages, daemon=True)
        self._subscribe_resp_thread = threading.Thread(target=self._receive_subscribe_messages, daemon=True)
        self._resp_thread.start()
        self._subscribe_resp_thread.start()

    def _receive_messages(self):
        for publish in self._resp_stream:
            self._outgoing_queue.put(publish)

    def _receive_subscribe_messages(self):
        for publish in self._subscribe_stream:
            self._subscribe_outgoing_queue.put(publish)

    def get_outgoing_queue(self):
        return self._outgoing_queue
    
    def get_subscribe_outgoing_queue(self):
        return self._subscribe_outgoing_queue

class StorageService(store_pb2_grpc.StoreServiceServicer):
    def __init__(self):
        super().__init__()
        self._data_store = {}
        self._publish_obj = Queue()
        self._subscribe_obj = Queue()
        self._subscribe_list: dict[str, futures.Future] = {}

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
    
    def PublishSession(self, request, context):
        while True:
            publish_msg: store_pb2.Publish = self._publish_obj.get()
            yield publish_msg
        
    def Subscribe(self, request, context):
        while True:
            subscribe_ref = self._subscribe_obj.get()
            yield store_pb2.Publish(ref=subscribe_ref)
    
    def publish(self, publish_msg: store_pb2.Publish):
        self._publish_obj.put(publish_msg)

    def subscribe(self, ref: str) -> futures.Future:
        self._subscribe_obj.put(ref)
        self._subscribe_list[ref] = futures.Future()
        return self._subscribe_list[ref]
    
    def put(self, key: str, data: Any):
        self._data_store[key] = data
        if key in self._subscribe_list:
            self._subscribe_list[key].set_result(data)
        self.publish(store_pb2.Publish(ref=key))
        log.info(f"Data stored with key: {key}")
    def get(self, key: str) -> Any:
        if key not in self._data_store:
            return None
        return self._data_store[key]    

class Controller(controller_pb2_grpc.ControllerServiceServicer, StorageService):
    def __init__(self):
        controller_pb2_grpc.ControllerServiceServicer.__init__(self)
        StorageService.__init__(self)
        self._funcs: dict[str, FunctionExecutor] = {}
        self._classes: dict[str, ClassExecutor] = {}
        self._pending_funcs = []

    def _transmit_data(self, data: controller_pb2.Data):
        data_type = data.type
        if data_type == controller_pb2.Data.ObjectType.OBJ_REF:
            obj_id = data.ref
            if self.get(obj_id) is None:
                f = self.subscribe(obj_id)
                return f.result()
            return self.get(obj_id)
        elif data_type == controller_pb2.Data.ObjectType.OBJ_ENCODED:
            obj_data = data.encoded
            obj = cloudpickle.loads(obj_data)
            return obj
    
    def _transmit_result(self, result, session_id, instance_id, function_name) -> controller_pb2.Data:
        obj_id = f"{session_id}_{instance_id}_{function_name}"
        self.put(obj_id, result)
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



class Master(
    cluster_pb2_grpc.ClusterServiceServicer, 
    Controller, 
    platform_pb2_grpc.PlatformServicer
):
    class Metadata:
        def __init__(self, host: str, port: int, worker_id: str, rank: int):
            self._host = host
            self._port = port
            self._worker_id = worker_id
            self._rank = rank
            self._controller = ControllerContext(f"{host}:{port}")
            self._store = StoreContext(f"{host}:{port}")

    class StoreProxy:
        def __init__(self, out_store: StorageService):
            self._refs = {}
            self._refs_lock = threading.Lock()
            self._new_worker = Queue()
        
            self._listener_threads: List[threading.Thread] = []
            self._subscriber_workers = set()

            self._running = False

            self._metas: dict[str, Master.Metadata] = {}

            # self._subscribes = Queue()
            self._subscribes_out = Queue()
            self._out_store = out_store
        
        def handle_subscribe(self, msg: store_pb2.Publish):
            with self._refs_lock:
                worker_id = self._refs[msg.ref]
            sub_meta = self._metas[worker_id]
            channel = grpc.insecure_channel(f"{sub_meta._host}:{sub_meta._port}")
            stub = store_pb2_grpc.StoreServiceStub(channel)
            request = store_pb2.GetObjectRequest(ref=msg.ref)
            resp: store_pb2.GetObjectResponse = stub.GetObject(request)
            if resp.error != "":
                log.error(f"Error getting object: {resp.error}")
            else:
                self._out_store.put(msg.ref, cloudpickle.loads(resp.data))

        def _spawn_local_session_reader(self):
            def gen():
                yield 0
            def local_store_runner():
                try:
                    for resp in self._out_store.Subscribe(gen(), None):
                        self.handle_subscribe(resp)
                except Exception as e:
                    log.error(f"Error in local_store_runner: {e}")
            
            t = threading.Thread(target=local_store_runner, daemon=True)
            t.start()
            self._listener_threads.append(t)
        
        def listen(self):
            self._running = True
            def store_listener(wid, meta: Master.Metadata):
                q = meta._store.get_outgoing_queue()
                while self._running:
                    publish_msg: store_pb2.Publish = q.get()
                    if publish_msg is None:
                        continue
                    # Process the publish_msg as needed
                    with self._refs_lock:
                        self._refs[publish_msg.ref] = wid
            
            def subscriber_listener(wid, meta: Master.Metadata):
                q = meta._store.get_subscribe_outgoing_queue()
                while self._running:
                    subscribe_msg: store_pb2.Publish = q.get()
                    if subscribe_msg is None:
                        continue
                    # Process the subscribe_msg as needed
                    self.handle_subscribe(subscribe_msg)
                    

            
            def monitor_store():
                while self._running:
                    wid, meta = self._new_worker.get()
                    if wid not in self._subscriber_workers:
                        self._subscriber_workers.add(wid)
                        self._metas[wid] = meta
                        t = threading.Thread(target=store_listener, args=(wid, meta), daemon=True)
                        t_sub = threading.Thread(target=subscriber_listener, args=(wid, meta), daemon=True)
                        t.start()
                        t_sub.start()
                        self._listener_threads.append(t)
            
            self._spawn_local_session_reader()
            monitor_thread = threading.Thread(target=monitor_store, daemon=True)
            monitor_thread.start()
            self._listener_threads.append(monitor_thread)

        def exists(self, ref) -> bool:
            with self._refs_lock:
                return ref in self._refs
        
        def get_worker_id(self, ref) -> str | None:
            with self._refs_lock:
                return self._refs.get(ref, None)
            
        def add_worker(self, wid, meta: "Master.Metadata"):
            self._new_worker.put((wid, meta))
        
        def shutdown(self):
            self._running = False
            for t in self._listener_threads:
                t.join()

    class ControllerProxy:
        def __init__(self, out_controller: Controller):
            self._metas : dict[str, Master.Metadata] = {}
            self._new_worker = Queue()

            self._listener_threads: List[threading.Thread] = []
            self._subscriber_workers = set()

            self._running = False

            self._outgoing_q = Queue()
            self._input = Queue()

            self._out_controller = out_controller

        
        def _spawn_local_session_reader(self, tag: str = "local"):
            def gen():
                while self._running:
                    msg = self._input.get()
                    if msg is None or not self._running:
                        break
                    yield msg
            
            def local_runner():
                try:
                    for resp in self._out_controller.Session(gen(), None):
                        try:
                            self._outgoing_q.put((tag, resp))
                        except Exception:
                            log.exception("Failed to put local session response into outgoing_q")
                except Exception:
                    log.exception("local session reader error")
            
            t = threading.Thread(target=local_runner, daemon=True)
            t.start()
            self._listener_threads.append(t)
        
        def submit_local(self, controller_message: controller_pb2.Message):
            self._input.put(controller_message)

        def broadcast(self, controller_message: controller_pb2.Message):
            for meta in self._metas.values():
                meta._controller.send_message(controller_message)
        
        def listen(self):
            self._running = True
            def worker_listener(meta: Master.Metadata):
                q = meta._controller.get_outgoing_queue()
                while self._running:
                    msg = q.get()
                    if msg is None:
                        break
                    self._outgoing_q.put((meta._worker_id, msg))
            def monitor_controller():
                while self._running:
                    wid, meta = self._new_worker.get()
                    if wid not in self._subscriber_workers:
                        self._subscriber_workers.add(wid)
                        self._metas[wid] = meta
                        t = threading.Thread(target=worker_listener, args=(meta,), daemon=True)
                        t.start()
                        self._listener_threads.append(t)
            
            self._spawn_local_session_reader()
            monitor_thread = threading.Thread(target=monitor_controller, daemon=True)
            monitor_thread.start()
            self._listener_threads.append(monitor_thread)

        def is_running(self) -> bool:
            return self._running

        def get_outgoing_queue(self):
            return self._outgoing_q
        
        def exist_worker(self, worker_id) -> bool:
            return worker_id in self._metas

        def get_worker(self, worker_id):
            return self._metas[worker_id]
        
        def get_workers(self):
            return self._metas.values()
        
        def remove_worker(self, wid):
            del self._metas[wid]
    
        def add_worker(self, wid, meta: "Master.Metadata"):
            self._new_worker.put((wid, meta))

        def shutdown(self):
            self._running = False
            for t in self._listener_threads:
                t.join()
    
    
            
    def __init__(self):
        Controller.__init__(self)
        # self._controllers: dict[str, Master.Metadata] = {}
        self._store_proxy = Master.StoreProxy(self)
        self._store_proxy.listen()
        self._controller_proxy = Master.ControllerProxy(self)
        self._controller_proxy.listen()
    
    def _spawn_local_session_reader(self, outgoing_q: Queue, stop_event: threading.Event, tag: str = "local") -> tuple[threading.Thread, Callable[[controller_pb2.Message], None]]:
        """Spawn a background thread that runs a single-message Controller.Session locally
        and pushes any responses into outgoing_q as (tag, controller_message).
        Returns the Thread object (daemon).
        """

        input_q = Queue()

        def submit(controller_message: controller_pb2.Message):
            # submit a single message to the local controller session
            input_q.put(controller_message)

        def gen():
            while not stop_event.is_set():
                msg = input_q.get()
                # sentinel None => shutdown this local session generator
                if msg is None or stop_event.is_set():
                    break
                yield msg

        def runner():
            try:
                # Call the parent Controller.Session to avoid recursing into Master.Session
                for resp in Controller.Session(self, gen(), None):
                    try:
                        outgoing_q.put((tag, resp))
                    except Exception:
                        log.exception("Failed to put local session response into outgoing_q")
            except Exception:
                log.exception("local session reader error")

        t = threading.Thread(target=runner, daemon=True)
        t.start()
        return t, submit
    
    def Session(self, request_iterator, context):
        return super().Session(request_iterator, context)

    def PlatformSession(self, request_iterator, context):
        """
        Bidirectional session: accept incoming platform.Messages and forward to controllers (local or worker).
        Whenever any controller (local or remote) produces a response, convert it to platform.Message
        (using Ack.message to carry object refs or errors) and yield it back to the client immediately.
        """

        outgoing_q = self._controller_proxy.get_outgoing_queue()
        stop_event = threading.Event()

        def request_reader():
            try:
                for request in request_iterator:
                    request: platform_pb2.Message
                    if request.type == platform_pb2.MessageType.APPLY_TO_WORKER:
                        req = request.apply_to_worker
                        worker_id = req.worker_id
                        controller_message = req.controller_message
                        if worker_id is None or not self._controller_proxy.exist_worker(worker_id):
                            # handle locally: spawn a local session reader that will publish responses
                            try:
                                self._controller_proxy.submit_local(controller_message)
                            except Exception as e:
                                log.exception("Error starting local session reader")
                                outgoing_q.put(("local", platform_pb2.Message(type=platform_pb2.MessageType.ACK, ack=platform_pb2.Ack(error=str(e)))))
                        else:
                            # forward to worker controller asynchronously
                            meta = self._controller_proxy.get_worker(worker_id)
                            if meta is not None:
                                meta._controller.send_message(controller_message)
                    elif request.type == platform_pb2.MessageType.BROADCAST:
                        # try to call local broadcast if exists, otherwise send to all controllers
                        controller_message = request.broadcast.controller_message
                        try:
                            self._controller_proxy.submit_local(controller_message)
                            self._controller_proxy.broadcast(controller_message)
                        except Exception as e:
                            log.error(f"Error broadcasting to local and workers: {e}")
                    else:
                        log.error(f"Unknown message type received: {request.type}")
            except grpc.RpcError as e:
                log.info("Session request stream closed by client")
            except Exception:
                log.exception("Error reading session requests")
            finally:
                stop_event.set()


        # start background threads
        req_thread = threading.Thread(target=request_reader, daemon=True)
        req_thread.start()

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
                    yield platform_pb2.Message(
                        type=platform_pb2.MessageType.RT_RESULT,
                        return_result=platform_pb2.ReturnResult(
                            controller_message=ctrl_msg
                        )
                    )
                except Exception:
                    log.exception("Error converting controller message to cluster message")
        finally:
            stop_event.set()
            # attempt to join threads briefly
            req_thread.join()

    def AddWorkerCommand(self, request, context):
        return self.addWorker(request)
    

    
    def addWorker(self, add_worker_request: cluster_pb2.AddWorker):
        worker_metadata = Master.Metadata(
            add_worker_request.host,
            add_worker_request.port,
            add_worker_request.worker_id,
            add_worker_request.worker_rank
        )
        self._controller_proxy.add_worker(add_worker_request.worker_id, worker_metadata)
        self._store_proxy.add_worker(add_worker_request.worker_id, worker_metadata)
        log.info(f"Worker {add_worker_request.worker_id} added.")
        return cluster_pb2.Ack(
            message=f"Worker {add_worker_request.worker_id} added successfully."
        )
    def removeWorker(self, remove_worker_request: cluster_pb2.RemoveWorker):
        if remove_worker_request.worker_id in self._controller_proxy.get_workers():
            self._controller_proxy.remove_worker(remove_worker_request.worker_id)
            log.info(f"Worker {remove_worker_request.worker_id} removed.")
            return cluster_pb2.Ack(
                message=f"Worker {remove_worker_request.worker_id} removed successfully."
            )
        else:
            log.error(f"Worker {remove_worker_request.worker_id} not found.")
            return cluster_pb2.Ack(
                error=f"Worker {remove_worker_request.worker_id} not found."
            )
    def getWorkers(self):
        workers = []
        for controller in self._controller_proxy.get_workers():
            worker_id = controller._worker_id
            host = controller._host
            port = controller._port
            rank = controller._rank
            workers.append(cluster_pb2.AddWorker(
                host=host,
                port=port,
                worker_id=worker_id,
                worker_rank=rank
            ))
        return cluster_pb2.GetWorkersResponse(
            workers=workers
        )

    def RemoveWorkerCommand(self, request, context):
        return self.removeWorker(request)
    
    def GetWorkers(self, request, context):
        return self.getWorkers()
    


    def GetObject(self, request, context):
        resp = StorageService.GetObject(self, request, context)
        if resp.error == "":
            return resp
        return self.get_object(request)

    def get_object(self, request: store_pb2.GetObjectRequest) -> store_pb2.GetObjectResponse:
        ref = request.ref
        if not self._store_proxy.exists(ref):
            return store_pb2.GetObjectResponse(
                error=f"Reference {ref} not found."
            )
        worker_id = self._store_proxy.get_worker_id(ref)
        meta = self._controller_proxy.get_worker(worker_id)
        channel = grpc.insecure_channel(f"{meta._host}:{meta._port}")
        stub = store_pb2_grpc.StoreServiceStub(channel)
        resp: store_pb2.GetObjectResponse = stub.GetObject(request)
        if resp.error != "":
            log.error(f"Error getting object: {resp.error}")
        return resp
        
class Worker(
    Controller
):
    def __init__(self, master_address: str, worker_host: str, worker_port: int, rank=1):
        super().__init__()
        self._worker_id = str(uuid.uuid4())
        self._master_address = master_address
        self._worker_host = worker_host
        self._worker_port = worker_port
        self._rank = rank
    def connect_to_master(self):
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

    def Session(self, request_iterator, context):
        return super().Session(request_iterator, context)



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
    if args.role == "master":
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        master = Master()
        store_pb2_grpc.add_StoreServiceServicer_to_server(master, server)
        cluster_pb2_grpc.add_ClusterServiceServicer_to_server(master, server)
        controller_pb2_grpc.add_ControllerServiceServicer_to_server(master, server)
        platform_pb2_grpc.add_PlatformServicer_to_server(master, server)
        server.add_insecure_port(f"[::]:{args.port}")
        server.start()
        log.info(f"Master server started on port {args.port}")
        server.wait_for_termination()
    elif args.role == "worker":
        # Worker implementation would go here
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        worker = Worker(
            master_address=args.master_address,
            worker_host=args.worker_host,
            worker_port=args.worker_port,
            rank=args.rank,
        )
        controller_pb2_grpc.add_ControllerServiceServicer_to_server(worker, server)
        store_pb2_grpc.add_StoreServiceServicer_to_server(worker, server)
        server.add_insecure_port(f"[::]:{args.worker_port}")
        server.start()
        worker.connect_to_master()
        server.wait_for_termination()
