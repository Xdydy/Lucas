from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

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
