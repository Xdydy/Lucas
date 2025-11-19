from common import logger_pb2 as _logger_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SubmitLogRequest(_message.Message):
    __slots__ = ("application_id", "entry")
    APPLICATION_ID_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    application_id: str
    entry: _logger_pb2.LogEntry
    def __init__(self, application_id: _Optional[str] = ..., entry: _Optional[_Union[_logger_pb2.LogEntry, _Mapping]] = ...) -> None: ...

class SubmitLogResponse(_message.Message):
    __slots__ = ("success", "error", "log_id")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    LOG_ID_FIELD_NUMBER: _ClassVar[int]
    success: bool
    error: str
    log_id: str
    def __init__(self, success: bool = ..., error: _Optional[str] = ..., log_id: _Optional[str] = ...) -> None: ...

class BatchSubmitLogRequest(_message.Message):
    __slots__ = ("application_id", "entries")
    APPLICATION_ID_FIELD_NUMBER: _ClassVar[int]
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    application_id: str
    entries: _containers.RepeatedCompositeFieldContainer[_logger_pb2.LogEntry]
    def __init__(self, application_id: _Optional[str] = ..., entries: _Optional[_Iterable[_Union[_logger_pb2.LogEntry, _Mapping]]] = ...) -> None: ...

class BatchSubmitLogResponse(_message.Message):
    __slots__ = ("success", "error", "accepted_count", "rejected_count", "log_ids")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    ACCEPTED_COUNT_FIELD_NUMBER: _ClassVar[int]
    REJECTED_COUNT_FIELD_NUMBER: _ClassVar[int]
    LOG_IDS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    error: str
    accepted_count: int
    rejected_count: int
    log_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, success: bool = ..., error: _Optional[str] = ..., accepted_count: _Optional[int] = ..., rejected_count: _Optional[int] = ..., log_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class LogStreamMessage(_message.Message):
    __slots__ = ("application_id", "entry", "control")
    APPLICATION_ID_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    CONTROL_FIELD_NUMBER: _ClassVar[int]
    application_id: str
    entry: _logger_pb2.LogEntry
    control: _logger_pb2.StreamControl
    def __init__(self, application_id: _Optional[str] = ..., entry: _Optional[_Union[_logger_pb2.LogEntry, _Mapping]] = ..., control: _Optional[_Union[_logger_pb2.StreamControl, _Mapping]] = ...) -> None: ...

class LogStreamResponse(_message.Message):
    __slots__ = ("success", "error", "processed_count", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    PROCESSED_COUNT_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    error: str
    processed_count: int
    message: str
    def __init__(self, success: bool = ..., error: _Optional[str] = ..., processed_count: _Optional[int] = ..., message: _Optional[str] = ...) -> None: ...
