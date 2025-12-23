from common import logger_pb2 as _logger_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class LogStreamMessage(_message.Message):
    __slots__ = ("application_id", "entry")
    APPLICATION_ID_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    application_id: str
    entry: _logger_pb2.LogEntry
    def __init__(self, application_id: _Optional[str] = ..., entry: _Optional[_Union[_logger_pb2.LogEntry, _Mapping]] = ...) -> None: ...

class LogStreamResponse(_message.Message):
    __slots__ = ("application_id", "success", "error", "processed_count", "message")
    APPLICATION_ID_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    PROCESSED_COUNT_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    application_id: str
    success: bool
    error: str
    processed_count: int
    message: str
    def __init__(self, application_id: _Optional[str] = ..., success: bool = ..., error: _Optional[str] = ..., processed_count: _Optional[int] = ..., message: _Optional[str] = ...) -> None: ...
