from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class LogLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LOG_LEVEL_UNKNOWN: _ClassVar[LogLevel]
    LOG_LEVEL_TRACE: _ClassVar[LogLevel]
    LOG_LEVEL_DEBUG: _ClassVar[LogLevel]
    LOG_LEVEL_INFO: _ClassVar[LogLevel]
    LOG_LEVEL_WARN: _ClassVar[LogLevel]
    LOG_LEVEL_ERROR: _ClassVar[LogLevel]
    LOG_LEVEL_FATAL: _ClassVar[LogLevel]
    LOG_LEVEL_PANIC: _ClassVar[LogLevel]
LOG_LEVEL_UNKNOWN: LogLevel
LOG_LEVEL_TRACE: LogLevel
LOG_LEVEL_DEBUG: LogLevel
LOG_LEVEL_INFO: LogLevel
LOG_LEVEL_WARN: LogLevel
LOG_LEVEL_ERROR: LogLevel
LOG_LEVEL_FATAL: LogLevel
LOG_LEVEL_PANIC: LogLevel

class LogField(_message.Message):
    __slots__ = ("key", "value")
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    key: str
    value: str
    def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class CallerInfo(_message.Message):
    __slots__ = ("file", "line", "function")
    FILE_FIELD_NUMBER: _ClassVar[int]
    LINE_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    file: str
    line: int
    function: str
    def __init__(self, file: _Optional[str] = ..., line: _Optional[int] = ..., function: _Optional[str] = ...) -> None: ...

class LogEntry(_message.Message):
    __slots__ = ("timestamp", "level", "message", "fields", "caller")
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    CALLER_FIELD_NUMBER: _ClassVar[int]
    timestamp: int
    level: LogLevel
    message: str
    fields: _containers.RepeatedCompositeFieldContainer[LogField]
    caller: CallerInfo
    def __init__(self, timestamp: _Optional[int] = ..., level: _Optional[_Union[LogLevel, str]] = ..., message: _Optional[str] = ..., fields: _Optional[_Iterable[_Union[LogField, _Mapping]]] = ..., caller: _Optional[_Union[CallerInfo, _Mapping]] = ...) -> None: ...

class StreamControl(_message.Message):
    __slots__ = ("type", "metadata")
    class ControlType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        CONTROL_UNKNOWN: _ClassVar[StreamControl.ControlType]
        CONTROL_HEARTBEAT: _ClassVar[StreamControl.ControlType]
        CONTROL_FLUSH: _ClassVar[StreamControl.ControlType]
        CONTROL_CLOSE: _ClassVar[StreamControl.ControlType]
    CONTROL_UNKNOWN: StreamControl.ControlType
    CONTROL_HEARTBEAT: StreamControl.ControlType
    CONTROL_FLUSH: StreamControl.ControlType
    CONTROL_CLOSE: StreamControl.ControlType
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TYPE_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    type: StreamControl.ControlType
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, type: _Optional[_Union[StreamControl.ControlType, str]] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...
