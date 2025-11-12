import controller_pb2 as _controller_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MessageType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNSPECIFIED: _ClassVar[MessageType]
    ACK: _ClassVar[MessageType]
    APPLY_TO_WORKER: _ClassVar[MessageType]
    BROADCAST: _ClassVar[MessageType]
    RT_RESULT: _ClassVar[MessageType]
UNSPECIFIED: MessageType
ACK: MessageType
APPLY_TO_WORKER: MessageType
BROADCAST: MessageType
RT_RESULT: MessageType

class Ack(_message.Message):
    __slots__ = ("message", "error")
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    message: str
    error: str
    def __init__(self, message: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class AddWorker(_message.Message):
    __slots__ = ("worker_id", "host", "port", "worker_rank")
    WORKER_ID_FIELD_NUMBER: _ClassVar[int]
    HOST_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    WORKER_RANK_FIELD_NUMBER: _ClassVar[int]
    worker_id: str
    host: str
    port: int
    worker_rank: int
    def __init__(self, worker_id: _Optional[str] = ..., host: _Optional[str] = ..., port: _Optional[int] = ..., worker_rank: _Optional[int] = ...) -> None: ...

class RemoveWorker(_message.Message):
    __slots__ = ("worker_id",)
    WORKER_ID_FIELD_NUMBER: _ClassVar[int]
    worker_id: str
    def __init__(self, worker_id: _Optional[str] = ...) -> None: ...

class GetWorkersRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetWorkersResponse(_message.Message):
    __slots__ = ("workers",)
    WORKERS_FIELD_NUMBER: _ClassVar[int]
    workers: _containers.RepeatedCompositeFieldContainer[AddWorker]
    def __init__(self, workers: _Optional[_Iterable[_Union[AddWorker, _Mapping]]] = ...) -> None: ...

class ApplyToWorker(_message.Message):
    __slots__ = ("worker_id", "controller_message")
    WORKER_ID_FIELD_NUMBER: _ClassVar[int]
    CONTROLLER_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    worker_id: str
    controller_message: _controller_pb2.Message
    def __init__(self, worker_id: _Optional[str] = ..., controller_message: _Optional[_Union[_controller_pb2.Message, _Mapping]] = ...) -> None: ...

class Broadcast(_message.Message):
    __slots__ = ("controller_message",)
    CONTROLLER_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    controller_message: _controller_pb2.Message
    def __init__(self, controller_message: _Optional[_Union[_controller_pb2.Message, _Mapping]] = ...) -> None: ...

class ReturnResult(_message.Message):
    __slots__ = ("controller_message",)
    CONTROLLER_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    controller_message: _controller_pb2.Message
    def __init__(self, controller_message: _Optional[_Union[_controller_pb2.Message, _Mapping]] = ...) -> None: ...

class Message(_message.Message):
    __slots__ = ("type", "ack", "apply_to_worker", "broadcast", "return_result")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ACK_FIELD_NUMBER: _ClassVar[int]
    APPLY_TO_WORKER_FIELD_NUMBER: _ClassVar[int]
    BROADCAST_FIELD_NUMBER: _ClassVar[int]
    RETURN_RESULT_FIELD_NUMBER: _ClassVar[int]
    type: MessageType
    ack: Ack
    apply_to_worker: ApplyToWorker
    broadcast: Broadcast
    return_result: ReturnResult
    def __init__(self, type: _Optional[_Union[MessageType, str]] = ..., ack: _Optional[_Union[Ack, _Mapping]] = ..., apply_to_worker: _Optional[_Union[ApplyToWorker, _Mapping]] = ..., broadcast: _Optional[_Union[Broadcast, _Mapping]] = ..., return_result: _Optional[_Union[ReturnResult, _Mapping]] = ...) -> None: ...
