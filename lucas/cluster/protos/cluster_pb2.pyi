from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MessageType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNSPECIFIED: _ClassVar[MessageType]
    ACK: _ClassVar[MessageType]
    ADD_WORKER: _ClassVar[MessageType]
    REMOVE_WORKER: _ClassVar[MessageType]
UNSPECIFIED: MessageType
ACK: MessageType
ADD_WORKER: MessageType
REMOVE_WORKER: MessageType

class Ack(_message.Message):
    __slots__ = ("error",)
    ERROR_FIELD_NUMBER: _ClassVar[int]
    error: str
    def __init__(self, error: _Optional[str] = ...) -> None: ...

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

class Message(_message.Message):
    __slots__ = ("type", "ack", "add_worker", "remove_worker")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ACK_FIELD_NUMBER: _ClassVar[int]
    ADD_WORKER_FIELD_NUMBER: _ClassVar[int]
    REMOVE_WORKER_FIELD_NUMBER: _ClassVar[int]
    type: MessageType
    ack: Ack
    add_worker: AddWorker
    remove_worker: RemoveWorker
    def __init__(self, type: _Optional[_Union[MessageType, str]] = ..., ack: _Optional[_Union[Ack, _Mapping]] = ..., add_worker: _Optional[_Union[AddWorker, _Mapping]] = ..., remove_worker: _Optional[_Union[RemoveWorker, _Mapping]] = ...) -> None: ...
