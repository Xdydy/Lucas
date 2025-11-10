from typing import Any, Callable
from lucas import Runtime, Function, ActorClass, ActorInstance
from lucas.serverless_function import Metadata
from lucas.workflow.executor import Executor
from lucas.workflow.dag import DAGNode, DataNode, ControlNode, ActorNode
from lucas.utils.logging import log

from .protos import controller_pb2, controller_pb2_grpc

from concurrent.futures import Future, wait
from queue import Queue
import cloudpickle
import grpc
import uuid
import time
import inspect
import threading

class Context:
    context: "Context | None" = None
    @staticmethod
    def create_context(master_addr: str = "localhost:50051"):
        if Context.context is None:
            Context.context = Context(master_addr)
        return Context.context
    
    def __init__(self, master_addr: str):
        self._master_addr = master_addr
        self._channel = grpc.insecure_channel(self._master_addr)
        self._stub = controller_pb2_grpc.ControllerServiceStub(self._channel)
        self._msg_queue = Queue()
        self._result: dict[str, Future] = {}
        self._result_lock = threading.Lock()
        self._resp_stream = self._stub.Session(self._message_generator())
        self._resp_thread = threading.Thread(target=self._handle_responses, daemon=True)
        self._resp_thread.start()
    
    def _message_generator(self):
        while True:
            msg = self._msg_queue.get()
            if msg is None:
                break
            yield msg
    
    def _handle_responses(self):
        for resp in self._resp_stream:
            resp: controller_pb2.Message
            if resp.type == controller_pb2.MessageType.RT_RESULT:
                self._handle_rt_result(resp.return_result)
            elif resp.type == controller_pb2.MessageType.ACK:
                self._handle_ack(resp.ack)
            else:
                log.warning(f"Unknown response type: {resp.type}")

    def _handle_rt_result(self, rt_result: controller_pb2.ReturnResult):
        log.info(f"Received runtime result: {rt_result.value}")
        if rt_result.value.type == controller_pb2.Data.ObjectType.OBJ_REF:
            obj_id = rt_result.value.ref
            with self._result_lock:
                if obj_id in self._result:
                    self._result[obj_id].set_result(rt_result.value)
                else:
                    f = Future()
                    f.set_result(rt_result.value)
                    self._result[obj_id] = f
        else:
            log.warning(f"Received non-object result: {rt_result.value}")

    def _handle_ack(self, ack: controller_pb2.Ack):
        log.info(f"Received ACK: {ack.message}")

    def wait_for_result(self, obj_id: str) -> Future:
        with self._result_lock:
            if obj_id in self._result:
                return self._result[obj_id].result()
            else:
                f = Future()
                self._result[obj_id] = f
        return self._result[obj_id]
    def send(self, msg: controller_pb2.Message):
        self._msg_queue.put(msg)
    
class ClusterRuntime(Runtime):
    def __init__(self, metadata: Metadata):
        super().__init__()
        self._input = metadata._params
        self._namespace = metadata._namespace
        self._router = metadata._router

    def input(self):
        return self._input

    def output(self, _out):
        return _out
    
    def call(self, fnName: str, fnParams: dict) -> Future:
        log.info(f"Calling function: {fnName} with params: {fnParams}")
        context = Context.create_context()
        session_id = fnParams['session_id']
        instance_id = fnParams['instance_id']
        msg = controller_pb2.Message(
            type=controller_pb2.MessageType.INVOKE_FUNCTION,
            invoke_function=controller_pb2.InvokeFunction(
                session_id=session_id,
                instance_id=instance_id,
                function_name=fnName,
            )
        )
        context.send(msg)
        key = f"{session_id}_{instance_id}_{fnName}"
        return context.wait_for_result(key)
    
    def tell(self, actorName: str, methodName: str, methodParams: dict):
        log.info(f"Calling actor method: {actorName}.{methodName} with params: {methodParams}")
        context = Context.create_context()
        session_id = methodParams['session_id']
        instance_id = methodParams['instance_id']
        msg = controller_pb2.Message(
            type=controller_pb2.MessageType.INVOKE_ACTOR_METHOD,
            invoke_actor_method=controller_pb2.InvokeActorMethod(
                session_id=session_id,
                instance_id=instance_id,
                actor_name=actorName,
                method_name=methodName,
            )
        )
        context.send(msg)


class ClusterFunction(Function):
    def __init__(self, fn, config = None):
        self._params = []
        super().__init__(fn, config)
    
    def onFunctionInit(self, fn):
        function_name = self._config.name
        function_code = cloudpickle.dumps(fn)
        dependcy = self._config.dependency
        params = inspect.signature(fn).parameters
        for param in params:
            self._params.append(param)
        context = Context.create_context()
        context.send(controller_pb2.Message(
            type=controller_pb2.MessageType.APPEND_FUNCTION,
            append_function=controller_pb2.AppendFunction(
                function_name=function_name,
                function_code=function_code,
                params=self._params,
                requirements=dependcy
            )
        ))
    
    def _transformfunction(self, fn):
        def cluster_function(args: dict):
            session_id = str(uuid.uuid4())
            context = Context.create_context()
            for key, value in args.items():
                if isinstance(value, controller_pb2.Data):
                    rpc_data = value
                else:
                    rpc_data = controller_pb2.Data(
                        type=controller_pb2.Data.ObjectType.OBJ,
                        encoded=cloudpickle.dumps(value)
                    )
                context.send(controller_pb2.Message(
                    type=controller_pb2.MessageType.APPEND_FUNCTION_ARG,
                    append_function_arg=controller_pb2.AppendFunctionArg(
                        session_id=session_id,
                        instance_id=session_id,
                        function_name=fn.__name__,
                        param_name=key,
                        value=rpc_data
                    )
                ))
            context.send(controller_pb2.Message(
                type=controller_pb2.MessageType.INVOKE_FUNCTION,
                invoke_function=controller_pb2.InvokeFunction(
                    session_id=session_id,
                    instance_id=session_id,
                    function_name=fn.__name__,
                )
            ))

        return cluster_function
    
class ClusterExecutor(Executor):
    def __init__(self, dag):
        super().__init__(dag)
        self._pending_tasks : list[Future] = []
        self._map_future_callback: dict[Future, Callable[[Future], Any]] = {}
    
    
    def execute(self):
        session_id = str(uuid.uuid4())
        task_lock = threading.Lock()
        tasks : list[DAGNode] = []
        for node in self.dag.get_nodes():
            if node._done:
                continue
            if isinstance(node, DataNode):
                if node._ready:
                    with task_lock: