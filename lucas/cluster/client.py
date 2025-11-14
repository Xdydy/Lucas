from typing import Any, Callable, Tuple
from lucas import Runtime, Function, ActorClass, ActorInstance
from lucas.serverless_function import Metadata
from lucas.workflow.executor import Executor
from lucas.workflow.dag import DAGNode, DataNode, ControlNode, ActorNode
from lucas.utils.logging import log

from .protos import platform_pb2, platform_pb2_grpc, store_pb2, store_pb2_grpc, controller_pb2
from .scheduler import Scheduler

from concurrent.futures import Future, wait, FIRST_COMPLETED
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
        self._stub = platform_pb2_grpc.PlatformStub(self._channel)
        self._msg_queue = Queue()
        self._result: dict[str, Future] = {}
        self._result_lock = threading.Lock()
        self._resp_stream = self._stub.PlatformSession(self._message_generator())
        self._resp_thread = threading.Thread(target=self._handle_responses, daemon=True)
        self._resp_thread.start()
        self._scheduler: Scheduler | None = None
    
    def set_scheduler(self, scheduler: Scheduler):
        if self._scheduler is not None:
            self._scheduler.shutdown()
        self._scheduler = scheduler
    
    def _message_generator(self):
        while True:
            msg = self._msg_queue.get()
            yield msg
    
    def _handle_responses(self):
        for resp in self._resp_stream:
            resp: platform_pb2.Message
            if resp.type == platform_pb2.MessageType.RT_RESULT:
                self._handle_rt_result(resp.return_result)
            elif resp.type == platform_pb2.MessageType.ACK:
                self._handle_ack(resp.ack)
            else:
                log.warning(f"Unknown response type: {resp.type}")
    
    def _handle_controller_rt_result(self, rt_result: controller_pb2.ReturnResult):
        log.debug(f"Received runtime result: {rt_result.value}")
        if rt_result.value.type == controller_pb2.Data.ObjectType.OBJ_REF:
            obj_id = rt_result.value.ref
            with self._result_lock:
                if obj_id in self._result:
                    self._result[obj_id].set_result(rt_result.value)
                else:
                    f = Future()
                    f.set_result(rt_result.value)
                    self._result[obj_id] = f


    def _handle_controller_response(self, controller_message: controller_pb2.Message):
        log.debug(f"Received controller response: {controller_message}")
        if controller_message.type == controller_pb2.MessageType.RT_RESULT:
            self._handle_controller_rt_result(controller_message.return_result)
        elif controller_message.type == controller_pb2.MessageType.ACK:
            self._handle_ack(controller_message.ack)
        else:
            log.warning(f"Unknown controller response type: {controller_message.type}")

    def _handle_rt_result(self, rt_result: platform_pb2.ReturnResult):
        self._handle_controller_response(rt_result.controller_message)

    def _handle_ack(self, ack: controller_pb2.Ack):
        # log.info(f"Received ACK: {ack.message}")
        if ack.error != "":
            log.error(f"Error in ACK: {ack.error}")

    def wait_for_result(self, obj_id: str) -> Future:
        with self._result_lock:
            if obj_id in self._result:
                return self._result[obj_id].result()
            else:
                f = Future()
                self._result[obj_id] = f
        return self._result[obj_id]
    
    def schedule(self, msg: controller_pb2.Message) -> platform_pb2.Message:
        if self._scheduler is None:
            return platform_pb2.Message(
                type=platform_pb2.MessageType.APPLY_TO_WORKER,
                apply_to_worker=platform_pb2.ApplyToWorker(
                    controller_message=msg
                )
            )
        else:
            return self._scheduler.schedule(msg)

    def send(self, msg: controller_pb2.Message):
        platform_msg = self.schedule(msg)
        self._msg_queue.put(platform_msg)

    def get_obj(self, refid: str):
        channel = grpc.insecure_channel(self._master_addr)
        stub = store_pb2_grpc.StoreServiceStub(channel)
        resp: store_pb2.GetObjectResponse = stub.GetObject(store_pb2.GetObjectRequest(ref=refid))
        if resp.error != "":
            log.error(f"Error getting object {refid}: {resp.error}")
            return None
        else:
            return cloudpickle.loads(resp.data)
    
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
                rpc_data = transform_data(data=value)
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
            key = f"{session_id}_{session_id}_{fn.__name__}"
            data: controller_pb2.Data = context.wait_for_result(key).result()
            return transform_obj(data)


        return cluster_function



class ClusterExecutor(Executor):
    def __init__(self, dag):
        super().__init__(dag)
        self._pending_tasks : list[Future] = []
        self._map_future_callback: dict[Future, Callable[[Future], Any]] = {}
        self._map_future_params: dict[Future, Tuple[Future]] = {}
    
    def _has_pending_tasks(self):
        return len(self._pending_tasks) > 0
    
    def _pending_callback(self, fut: Future):
        self._pending_tasks.remove(fut)
        if fut in self._map_future_callback:
            callback = self._map_future_callback[fut]
            params = self._map_future_params[fut]
            callback(*params)
            del self._map_future_callback[fut]
            del self._map_future_params[fut]
    def _append_pending(self, fut: Future, c_node: ControlNode, d_node: DataNode, callback: Callable[[Future], Any]):
        self._pending_tasks.append(fut)
        self._map_future_callback[fut] = callback
        self._map_future_params[fut] = (fut, c_node, d_node)

    def _return_result(self):
        result = None
        for node in self.dag.get_nodes():
            if isinstance(node, DataNode) and node._is_end_node:
                from lucas.workflow import Lambda
                result = node._ld.value
                while isinstance(result, Lambda):
                    result = result.value
                if isinstance(result, controller_pb2.Data):
                    result = transform_obj(result)
                break
        return result
    
    def execute(self):
        session_id = str(uuid.uuid4())
        context = Context.create_context()
        task_lock = threading.Lock()
        tasks : list[DAGNode] = []
        for node in self.dag.get_nodes():
            if node._done:
                continue
            if isinstance(node, DataNode):
                if node._ready:
                    with task_lock:
                        tasks.append(node)
            elif isinstance(node, ControlNode):
                if len(node.get_pre_data_nodes()) == 0:
                    with task_lock:
                        tasks.append(node)
        
        while len(tasks) > 0 or self._has_pending_tasks():
            if len(tasks) == 0:
                done, _ = wait(self._pending_tasks, return_when=FIRST_COMPLETED)
                for fut in done:
                    self._pending_callback(fut)
            with task_lock:
                node = tasks.pop(0)
            node._done = True
            if isinstance(node, DataNode):
                data = node._ld.value
                for control_node in node.get_succ_control_nodes():
                    control_node: ControlNode
                    control_node_metadata = control_node.metadata()
                    params = control_node_metadata['params']
                    fn_type = control_node_metadata['functiontype']
                    if fn_type == "remote":
                        rpc_data = transform_data(data=data)
                        message = controller_pb2.Message(
                            type=controller_pb2.MessageType.APPEND_FUNCTION_ARG,
                            append_function_arg=controller_pb2.AppendFunctionArg(
                                session_id=session_id,
                                instance_id=control_node_metadata['id'],
                                function_name=control_node_metadata['functionname'],
                                param_name=params[node._ld.getid()],
                                value=rpc_data
                            )
                        )
                        context.send(message)
                    else:
                        data = transform_obj(data)
                        node.set_value(data)

                    log.info(f"{control_node.describe()} appargs {node._ld.value}")
                    if control_node.appargs(node._ld):
                        if fn_type == "remote":
                            control_node._datas['session_id'] = session_id
                            control_node._datas['instance_id'] = control_node_metadata['id']
                            control_node._datas['name'] = control_node_metadata['functionname']
                        with task_lock:
                            tasks.append(control_node)
            elif isinstance(node, ControlNode):
                fn = node._fn
                params = node._datas
                r_node: DataNode = node.get_data_node()
                result = fn(params)
                if isinstance(result, Future):
                    def set_datanode_ready(fut: Future, c_node: ControlNode, d_node: DataNode):
                        nonlocal task_lock, tasks
                        res = fut.result()
                        d_node.set_value(res)
                        d_node.set_ready()
                        log.info(f"{c_node.describe()} calculate {d_node.describe()}")
                        if d_node.is_ready():
                            with task_lock:
                                tasks.append(d_node)
                    self._append_pending(result,node,r_node,set_datanode_ready)
                else:
                    r_node.set_value(result)
                    r_node.set_ready()
                    log.info(f"{node.describe()} calculate {r_node.describe()}")
                    if r_node.is_ready():
                        with task_lock:
                            tasks.append(r_node)
        result = self._return_result()
        self.dag.reset()
        return result
        
def transform_data(data: Any) -> controller_pb2.Data:
    if isinstance(data, controller_pb2.Data):
        return data
    else:
        return controller_pb2.Data(
            type=controller_pb2.Data.ObjectType.OBJ_ENCODED,
            encoded=cloudpickle.dumps(data)
        )

def transform_obj(data: controller_pb2.Data | Any) -> Any:
    context = Context.create_context()
    if isinstance(data, controller_pb2.Data):
        return context.get_obj(data.ref)
    else:
        return data