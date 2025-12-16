import os
from typing import Any, Callable, Tuple
from utils.memory import parse_memory_string
from utils.mapper import to_proto_append_dag_node_list
from utils.logger import setup_logging
from lucas import Runtime, Function, ActorClass, ActorInstance
from lucas.serverless_function import Metadata
from lucas.workflow.executor import Executor
from lucas.workflow.dag import DAGNode, DataNode, ControlNode, ActorNode
from lucas.utils.logging import log
from protos.common import types_pb2 as common
from protos.controller import controller_pb2, controller_pb2_grpc
from utils import EncDec

from concurrent.futures import Future, wait
import cloudpickle
import grpc
import uuid
import queue
import time
import inspect
import threading

actorContext: "ActorContext | None" = None


class ActorContext:
    @staticmethod
    def createContext(master_address: str = None, app_id: str = None):
        global actorContext
        if actorContext is None:
            if master_address is None:
                master_address = os.getenv("MASTER_ADDR", "localhost:50051")
            if app_id is None:
                app_id = os.getenv("APP_ID", None)
            logger_addr = os.getenv("LOGGER_ADDR", None)
            if logger_addr is not None:
                log.info(f"setup logging to {logger_addr}")
                setup_logging(log, app_id, logger_addr)
            actorContext = ActorContext(master_address, app_id)
        return actorContext

    def __init__(self, master_address: str = None, app_id: str = None):
        if master_address is None:
            log.error("MASTER_ADDR is not set")
            raise ValueError("MASTER_ADDR is not set")
        if app_id is None:
            log.error("APP_ID is not set")
            raise ValueError("APP_ID is not set")
        self._master_address = master_address
        self._app_id = app_id
        self._channel = grpc.insecure_channel(
            master_address,
            options=[("grpc.max_receive_message_length", 512 * 1024 * 1024)],
        )
        self._stub = controller_pb2_grpc.ServiceStub(self._channel)
        self._q = queue.Queue()
        self._response_stream = self._stub.Session(self._generate())
        self._result_map: dict[str, Future] = {}
        self._obj_map: dict[str, Future] = {}
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _generate(self):
        while True:
            msg = self._q.get()
            yield msg

    def _run(self):
        while True:
            for response in self._response_stream:
                response: controller_pb2.Message
                if response.Type == controller_pb2.CommandType.BK_RETURN_RESULT:
                    result: controller_pb2.ReturnResult = response.ReturnResult
                    sessionID = result.SessionID
                    instanceID = result.InstanceID
                    name = result.Name
                    value = result.Value
                    key = f"{sessionID}-{instanceID}-{name}"
                    with self._lock:
                        if key in self._result_map:
                            future = self._result_map[key]
                            if not future.done():
                                future.set_result(value)
                        else:
                            future = Future()
                            future.set_result(value)
                            self._result_map[key] = future
                elif response.Type == controller_pb2.CommandType.BK_RESPONSE_OBJECT:
                    response_object: controller_pb2.ResponseObject = response.ResponseObject
                    obj_id = response_object.ID
                    value = EncDec.decode(response_object.Value)
                    with self._lock:
                        if obj_id in self._obj_map:
                            future = self._obj_map[obj_id]
                            if not future.done():
                                future.set_result(value)
                        else:
                            future = Future()
                            future.set_result(value)
                            self._obj_map[obj_id] = future
            time.sleep(1)

    def get_result(self, key: str) -> Future:
        with self._lock:
            if key not in self._result_map:
                self._result_map[key] = Future()
        return self._result_map.get(key)

    def get_obj(self, obj_id: str) -> Future:
        with self._lock:
            if obj_id not in self._obj_map:
                self._obj_map[obj_id] = Future()
        return self._obj_map.get(obj_id)

    def send(self, message: controller_pb2.Message):
        message.AppID = self._app_id
        self._q.put(message)
    

class ActorRuntime(Runtime):
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
        log.info(f"call {fnName}")
        sessionID = fnParams["sessionID"]
        instanceID = fnParams["instanceID"]
        name = fnParams["name"]
        actorContext.send(controller_pb2.Message(
            Type=controller_pb2.CommandType.FR_INVOKE,
            Invoke=controller_pb2.Invoke(
                SessionID=sessionID,
                InstanceID=instanceID,
                Name=name,
            ),
        ))
        key = f"{sessionID}-{instanceID}-{name}"
        log.info(f"find key: {key}")
        result = actorContext.get_result(key)
        return result

    def tell(self, fnName: str, fnParams: dict):
        log.info("tell function here")
        fn = self._router.get(fnName)
        if fn is None:
            raise ValueError(f"Function {fnName} not found in router")

        return {"function": fnName, "params": fnParams, "data": fn(fnParams)}


class ActorFunction(Function):
    def __init__(self, fn, config = None):
        self._params = []
        self._instance_id = str(uuid.uuid4())
        super().__init__(fn, config)
    def onFunctionInit(self, fn):
        dependcy = self._config.dependency
        fn_name = self._config.name
        venv = self._config.venv
        cpu = None
        memory = None
        try:
            cpu = self._config.cpu
        except AttributeError:
            cpu = None
        try:
            memory = self._config.memory
        except AttributeError:
            memory = None
        try:
            replicas = self._config.replicas
        except AttributeError:
            replicas = 1
        try:
            tags = self._config.tags
        except AttributeError:
            tags = []
        if tags is None:
            tags = []
        sig = inspect.signature(fn)
        for name, param in sig.parameters.items():
            self._params.append(name)
        message = controller_pb2.Message(
            Type=controller_pb2.CommandType.FR_APPEND_PY_FUNC,
            AppendPyFunc=controller_pb2.AppendPyFunc(
                Name=fn_name,
                Params=self._params,
                Venv=venv,
                Requirements=dependcy,
                PickledObject=cloudpickle.dumps(fn),
                Language=common.LANG_PYTHON,
                Resources=controller_pb2.Resources(
                    CPU=cpu,
                    Memory=parse_memory_string(memory),
                ),
                Replicas=replicas,
                Tags=tags,
            ),
        )
        actorContext.send(message)

    def _transformfunction(self, fn):
        def actor_function(args: dict):
            sessionID = str(uuid.uuid4())
            for key, value in args.items():
                if isinstance(value, controller_pb2.Data):
                    rpc_data = value
                else:
                    rpc_data = controller_pb2.Data(
                        Type=controller_pb2.Data.ObjectType.OBJ_ENCODED,
                        Encoded=EncDec.encode(
                            value, language=common.LANG_PYTHON
                        ),
                    )
                actorContext.send(controller_pb2.Message(
                    Type=controller_pb2.CommandType.FR_APPEND_ARG,
                    AppendArg=controller_pb2.AppendArg(
                        SessionID=sessionID,
                        InstanceID=self._instance_id,
                        Name=self._config.name,
                        Param=key,
                        Value=rpc_data,
                    ),
                ))
            actorContext.send(controller_pb2.Message(
                Type=controller_pb2.CommandType.FR_INVOKE,
                Invoke=controller_pb2.Invoke(
                    SessionID=sessionID,
                    InstanceID=self._instance_id,
                    Name=self._config.name,
                ),
            ))
            key = f"{sessionID}-{self._instance_id}-{self._config.name}"
            result = actorContext.get_result(key)
            result = result.result()
            actorContext.send(controller_pb2.Message(
                Type=controller_pb2.CommandType.FR_REQUEST_OBJECT,
                RequestObject=controller_pb2.RequestObject(
                    ID=key,
                    Target=None,
                ),
            ))
            result = actorContext.get_obj(key)
            result = result.result()
            return result
        return actor_function

class ActorRuntimeInstance(ActorInstance):
    def __init__(self, instance):
        super().__init__(instance)
    def remote(self, method_name, data:dict):
        if not hasattr(self._instance, method_name):
            raise AttributeError(f"Object {self._instance} has no method {method_name}")
        method = getattr(self._instance, method_name)
        if not callable(method):
            raise TypeError(f"{method_name} is not callable")
        
        sessionID = str(uuid.uuid4())
        method_name = self._instance.__class__.__name__ + "." + method_name
        for key, value in data.items():
            if isinstance(value, controller_pb2.Data):
                rpc_data = value
            else:
                rpc_data = controller_pb2.Data(
                    Type=controller_pb2.Data.ObjectType.OBJ_ENCODED,
                    Encoded=EncDec.encode(
                        value, language=common.LANG_PYTHON
                    ),
                )
            appendClassMethodArg = controller_pb2.AppendClassMethodArg(
                SessionID=sessionID,
                InstanceID=self._id,
                MethodName=method_name,
                Param=key,
                Value=rpc_data,
            )
            message = controller_pb2.Message(
                Type=controller_pb2.CommandType.FR_APPEND_CLASS_METHOD_ARG,
                AppendClassMethodArg=appendClassMethodArg,
            )
            actorContext.send(message)
        message = controller_pb2.Message(
            Type=controller_pb2.CommandType.FR_INVOKE,
            Invoke=controller_pb2.Invoke(
                SessionID=sessionID,
                InstanceID=self._id,
                Name=method_name,
            ),
        )
        actorContext.send(message)
        key = f"{sessionID}-{self._id}-{method_name}"
        result = actorContext.get_result(key)
        result = result.result()
        actorContext.send(controller_pb2.Message(
            Type=controller_pb2.CommandType.FR_REQUEST_OBJECT,
            RequestObject=controller_pb2.RequestObject(
                ID=key,
                Target=None,
            ),
        ))
        real_result = actorContext.get_obj(key)
        return real_result.result()
        

class ActorRuntimeClass(ActorClass):
    def _get_class_methods(self, instance) -> list[controller_pb2.AppendPyClass.ClassMethod]:
        methods = []
        all_methods = inspect.getmembers(instance, predicate=inspect.ismethod)
        for name, method in all_methods:
            sig = inspect.signature(method)
            params = sig.parameters.keys()
            params = list(params)
            methods.append(controller_pb2.AppendPyClass.ClassMethod(
                Name=f"{self._config.name}.{name}",
                Params=params
            ))
        return methods

    def onClassInit(self, instance):
        dependcy = self._config.dependency
        class_name = self._config.name
        instance.__class__.__name__ = class_name
        venv = self._config.venv
        cpu = None
        memory = None
        try:
            cpu = self._config.cpu
        except AttributeError:
            cpu = None
        
        try:
            memory = self._config.memory
        except AttributeError:
            memory = None


        try:
            replicas = self._config.replicas
        except AttributeError:
            replicas = 1
        obj = cloudpickle.dumps(instance)
        actorInstance = ActorRuntimeInstance(instance)
        message = controller_pb2.Message(
            Type=controller_pb2.CommandType.FR_APPEND_PY_CLASS,
            AppendPyClass=controller_pb2.AppendPyClass(
                Name=f"{actorInstance._id}",
                Methods=self._get_class_methods(instance),
                Venv=venv,
                Requirements=dependcy,
                PickledObject=obj,
                Language=common.LANG_PYTHON,
                Resources=controller_pb2.Resources(
                    CPU=cpu,
                    Memory=memory,
                ),
                Replicas=replicas,
            )
        )
        actorContext.send(message)
        return actorInstance

class ActorExecutor(Executor):
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

    def _get_real_result(self, data: controller_pb2.Data):
        message = controller_pb2.Message(
            Type = controller_pb2.CommandType.FR_REQUEST_OBJECT,
            RequestObject = controller_pb2.RequestObject(
                ID = data.Ref.ID,
                Source = data.Ref.Source,  # Source is now a string, not an object
            ),
        )
        actorContext.send(message)
        result_f = actorContext.get_obj(data.Ref.ID)
        result = result_f.result()
        return result

    def execute(self):
        session_id = str(uuid.uuid4())
        
        # send DAG nodes to controller
        proto_append_dag_node_list = to_proto_append_dag_node_list(self.dag, session_id)
        for node in proto_append_dag_node_list:
            message = controller_pb2.Message(
                Type=controller_pb2.CommandType.FR_APPEND_DAG_NODE,
                AppendDAGNode=node,
            )
            actorContext.send(message)

        while not self.dag.hasDone():
            _task_lock = threading.Lock()
            task: list[DAGNode] = []
            for node in self.dag.get_nodes():
                if node._done:
                    continue
                if isinstance(node, DataNode):
                    if node._ready:
                        with _task_lock:
                            task.append(node)
                if isinstance(node, ControlNode):
                    if node.get_pre_data_nodes() == []:
                        with _task_lock:
                            task.append(node)

            _end = False
            while len(task) != 0 or self._has_pending_tasks():
                if len(task) == 0:
                    done, _ = wait(self._pending_tasks, return_when='FIRST_COMPLETED')
                    # _futures = [fut for fut in _futures if not fut.done()]
                    for future in done:
                        self._pending_callback(future)
                    continue
                with _task_lock:
                    node = task.pop(0)
                node._done = True
                if isinstance(node, DataNode):
                    for control_node in node.get_succ_control_nodes():
                        control_node: ControlNode
                        control_node_metadata = control_node.metadata()
                        params = control_node_metadata["params"]
                        fn_type = control_node_metadata["functiontype"]
                        data = node._ld.value

                        if fn_type == "remote":  # 要调用的函数是远程函数时才需要
                            if isinstance(data, controller_pb2.Data):
                                rpc_data = data
                            else:
                                rpc_data = controller_pb2.Data(
                                    Type=controller_pb2.Data.ObjectType.OBJ_ENCODED,
                                    Encoded=EncDec.encode(
                                        data, language=common.LANG_PYTHON
                                    ),
                                )
                            if isinstance(control_node, ActorNode):
                                actorNode: ActorNode = control_node
                                appendClassMethodArg = controller_pb2.AppendClassMethodArg(
                                    SessionID=session_id,
                                    InstanceID=actorNode._obj._id,
                                    MethodName=control_node_metadata["functionname"],
                                    Param=params[node._ld.getid()],
                                    Value=rpc_data,
                                )
                                message = controller_pb2.Message(
                                    Type=controller_pb2.CommandType.FR_APPEND_CLASS_METHOD_ARG,
                                    AppendClassMethodArg=appendClassMethodArg,
                                )
                            else:    
                                appendArg = controller_pb2.AppendArg(
                                    SessionID=session_id,
                                    InstanceID=control_node_metadata["id"],
                                    Name=control_node_metadata["functionname"],
                                    Param=params[node._ld.getid()],
                                    Value=rpc_data,
                                )
                                message = controller_pb2.Message(
                                    Type=controller_pb2.CommandType.FR_APPEND_ARG,
                                    AppendArg=appendArg,
                                )
                            actorContext.send(message)
                        else: # 本地调用函数
                            log.info(f"Local function data: {data}")
                            if isinstance(data, controller_pb2.Data): # 需要获取实际值，不能传引用
                                data = self._get_real_result(data)
                                node.set_value(data)
                            


                        log.info(f"{control_node.describe()} appargs {node._ld.value}")
                        if control_node.appargs(node._ld):
                            if control_node._fn_type == "remote":
                                control_node._datas["sessionID"] = session_id
                                if isinstance(control_node, ActorNode):
                                    control_node._datas['instanceID'] = control_node._obj._id
                                else:
                                    control_node._datas["instanceID"] = control_node_metadata["id"]
                                    
                                control_node._datas["name"] = control_node_metadata[
                                    "functionname"
                                ]
                            with _task_lock:
                                task.append(control_node)
                elif isinstance(node, ControlNode):
                    fn = node._fn
                    params = node._datas
                    r_node: DataNode = node.get_data_node()
                    result = fn(params)
                    if isinstance(result, Future):
                        def set_datanode_ready(future: Future, c_node: ControlNode, d_node: DataNode):
                            nonlocal _task_lock, task
                            d_node.set_value(future.result())
                            d_node.set_ready()
                            log.info(f"{c_node.describe()} calculate {d_node.describe()}")
                            if d_node.is_ready():
                                with _task_lock:
                                    task.append(d_node)
                        self._append_pending(result, c_node=node, d_node=r_node, callback=set_datanode_ready)
                    else:
                        r_node.set_value(result)
                        r_node.set_ready()
                        log.info(f"{node.describe()} calculate {r_node.describe()}")
                        if r_node.is_ready():
                            with _task_lock:
                                task.append(r_node)
                
                with open("dag.json", 'w') as f:
                    import json
                    f.write(json.dumps(self.dag.metadata(fn_export=False), indent=2))
            if _end:
                break
        result = None
        for node in self.dag.get_nodes():
            if isinstance(node, DataNode) and node._is_end_node:
                from lucas.workflow import Lambda
                result = node._ld.value
                while isinstance(result, Lambda):
                    result = result.value
                if isinstance(result, controller_pb2.Data):
                    result = self._get_real_result(result)
                break
        self.dag.reset()
        return result