import sys
import os
sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),"protos"))
import grpc
import cloudpickle
from concurrent import futures 
from .protos.controller import controller_pb2, controller_pb2_grpc
from .protos import platform_pb2

class FunctionToExecute:
    def __init__(self, fn,params):
        self._fn = fn
        self._args = {}
        self._params = params
    def set_args(self, data:dict):
        for key,val in data.items():
            self._args[key] = val
    def can_run(self)-> bool:
        for params in self._params:
            if params not in self._args:
                print(f"{params} not in {self._args}")
                return False
        return True
    def run(self):
        result = self._fn(**self._args)
        return result

class ClassMethodToExecute:
    def __init__(self, obj, methods: list[controller_pb2.AppendPyClass.ClassMethod]):
        self._obj = obj
        self._methods = methods
        self._methods_to_args = {}
        for method in methods:
            self._methods_to_args[method.Name] = {}
    def set_method(self, method_name, data:dict):
        if method_name not in self._methods_to_args:
            raise ValueError(f"Method {method_name} not found")
        for key,val in data.items():
            self._methods_to_args[method_name][key] = val
    def can_run(self, method_name) -> bool:
        if method_name not in self._methods_to_args:
            raise ValueError(f"Method {method_name} not found")
        params = None
        for method in self._methods:
            if method.Name == method_name:
                params = method.Params
                break
        if params is None:
            raise ValueError(f"Method {method_name} not found")
        for param in params:
            if param not in self._methods_to_args[method_name]:
                return False
        return True
    def run(self, method_name):
        if method_name not in self._methods_to_args:
            raise ValueError(f"Method {method_name} not found")
        method = getattr(self._obj, method_name.split(".")[-1])
        if not callable(method):
            raise ValueError(f"Attribute {method_name} is not callable")
        args = self._methods_to_args[method_name]
        result = method(**args)
        return result


class GRPCServer(controller_pb2_grpc.ServiceServicer):
    def __init__(self):
        self._funcs = {}
        self._data_obj = {}
        self._classes = {}
    def Session(self, request_iterator, context):
        for request in request_iterator:
            request: controller_pb2.Message
            if request.Type == controller_pb2.CommandType.FR_APPEND_PY_FUNC:
                pyFunc = request.AppendPyFunc
                name = pyFunc.Name
                params = pyFunc.Params
                fn = pyFunc.PickledObject
                fn = cloudpickle.loads(fn)
                
                func = FunctionToExecute(fn, params)
                self._funcs[name] = func
                print(f"Function {name} registered, params: {params}")

                response = controller_pb2.Message(
                    Type=controller_pb2.CommandType.ACK,
                    Ack=controller_pb2.Ack(Error="")
                )
                yield response
            elif request.Type == controller_pb2.CommandType.FR_APPEND_PY_CLASS:
                pyClass = request.AppendPyClass
                name = pyClass.Name
                obj = pyClass.PickledObject
                obj = cloudpickle.loads(obj)
                print(f"Class {name} registered, methods: {[method.Name for method in pyClass.Methods]}")
                class_to_execute = ClassMethodToExecute(obj, pyClass.Methods)
                self._classes[name] = class_to_execute
                response = controller_pb2.Message(
                    Type=controller_pb2.CommandType.ACK,
                    Ack=controller_pb2.Ack(Error="")
                )
                yield response
            elif request.Type == controller_pb2.CommandType.FR_APPEND_ARG:
                appendArg = request.AppendArg
                sessionID = appendArg.SessionID
                instanceID = appendArg.InstanceID
                functionname = appendArg.Name
                args_name = appendArg.Param
                value:controller_pb2.Data = appendArg.Value
                print(f"Receive arg for function {functionname}, param: {args_name}, value: {value}")
                if value.Type == controller_pb2.Data.ObjectType.OBJ_REF:
                    ref = value.Ref
                    data = self._data_obj[ref.ID]
                elif value.Type == controller_pb2.Data.ObjectType.OBJ_ENCODED:
                    data = value.Encoded
                    data = data.Data
                    data = cloudpickle.loads(data)
                print(f"data: {data}")
                func: FunctionToExecute = self._funcs[functionname]
                func.set_args({args_name:data})
                if func.can_run():
                    result = func.run()
                    print(f"result: {result}")
                    key = f"{sessionID}-{instanceID}-{functionname}"
                    self._data_obj[key] = result
                    response = controller_pb2.Message(
                        Type=controller_pb2.CommandType.BK_RETURN_RESULT,
                        ReturnResult=controller_pb2.ReturnResult(
                            SessionID=sessionID,
                            InstanceID=instanceID,
                            Name=functionname,
                            Value=controller_pb2.Data(
                                Type=controller_pb2.Data.ObjectType.OBJ_REF,
                                Ref=platform_pb2.Flow(
                                    ID=key,
                                    Source={}
                                )
                            )
                        )
                    )
                    print(response)
                    yield response
                else:
                    response = controller_pb2.Message(
                        Type=controller_pb2.CommandType.ACK,
                        Ack=controller_pb2.Ack(Error="")
                    )
                    yield response
            elif request.Type == controller_pb2.CommandType.FR_APPEND_CLASS_METHOD_ARG:
                appendArg = request.AppendClassMethodArg
                sessionID = appendArg.SessionID
                instanceID = appendArg.InstanceID
                method_name = appendArg.MethodName
                args_name = appendArg.Param
                print(f"Receive arg for class {instanceID}, method {method_name}, param: {args_name}")
                value:controller_pb2.Data = appendArg.Value
                if value.Type == controller_pb2.Data.ObjectType.OBJ_REF:
                    ref = value.Ref
                    data = self._data_obj[ref.ID]
                elif value.Type == controller_pb2.Data.ObjectType.OBJ_ENCODED:
                    data = value.Encoded
                    data = data.Data
                    data = cloudpickle.loads(data)
                print(f"data: {data}")
                class_to_execute: ClassMethodToExecute = self._classes[instanceID]
                class_to_execute.set_method(method_name, {args_name:data})
                if class_to_execute.can_run(method_name):
                    result = class_to_execute.run(method_name)
                    print(f"result: {result}")
                    key = f"{sessionID}-{instanceID}-{method_name}"
                    self._data_obj[key] = result
                    response = controller_pb2.Message(
                        Type=controller_pb2.CommandType.BK_RETURN_RESULT,
                        ReturnResult=controller_pb2.ReturnResult(
                            SessionID=sessionID,
                            InstanceID=instanceID,
                            Name=method_name,
                            Value=controller_pb2.Data(
                                Type=controller_pb2.Data.ObjectType.OBJ_REF,
                                Ref=platform_pb2.Flow(
                                    ID=key,
                                    Source={}
                                )
                            )
                        )
                    )
                    print(response)
                    yield response

server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
controller_pb2_grpc.add_ServiceServicer_to_server(GRPCServer(), server)
server.add_insecure_port('[::]:50051')
server.start()
print("start")
try:
    import time
    time.sleep(3600)
except KeyboardInterrupt:
    server.stop(0)