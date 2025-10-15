import platform_pb2 as _platform_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MessageType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNSPECIFIED: _ClassVar[MessageType]
    OBJECT_REQUEST: _ClassVar[MessageType]
    OBJECT_RESPONSE: _ClassVar[MessageType]
    STREAM_CHUNK: _ClassVar[MessageType]
UNSPECIFIED: MessageType
OBJECT_REQUEST: MessageType
OBJECT_RESPONSE: MessageType
STREAM_CHUNK: MessageType

class ObjectRequest(_message.Message):
    __slots__ = ("ID", "ReplyTo")
    ID_FIELD_NUMBER: _ClassVar[int]
    REPLYTO_FIELD_NUMBER: _ClassVar[int]
    ID: str
    ReplyTo: _platform_pb2.StoreRef
    def __init__(self, ID: _Optional[str] = ..., ReplyTo: _Optional[_Union[_platform_pb2.StoreRef, _Mapping]] = ...) -> None: ...

class ObjectResponse(_message.Message):
    __slots__ = ("ID", "Value", "Error")
    ID_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    ID: str
    Value: _platform_pb2.EncodedObject
    Error: str
    def __init__(self, ID: _Optional[str] = ..., Value: _Optional[_Union[_platform_pb2.EncodedObject, _Mapping]] = ..., Error: _Optional[str] = ...) -> None: ...

class Envelope(_message.Message):
    __slots__ = ("Store", "Type", "ObjectRequest", "ObjectResponse", "StreamChunk")
    STORE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    OBJECTREQUEST_FIELD_NUMBER: _ClassVar[int]
    OBJECTRESPONSE_FIELD_NUMBER: _ClassVar[int]
    STREAMCHUNK_FIELD_NUMBER: _ClassVar[int]
    Store: _platform_pb2.StoreRef
    Type: MessageType
    ObjectRequest: ObjectRequest
    ObjectResponse: ObjectResponse
    StreamChunk: _platform_pb2.StreamChunk
    def __init__(self, Store: _Optional[_Union[_platform_pb2.StoreRef, _Mapping]] = ..., Type: _Optional[_Union[MessageType, str]] = ..., ObjectRequest: _Optional[_Union[ObjectRequest, _Mapping]] = ..., ObjectResponse: _Optional[_Union[ObjectResponse, _Mapping]] = ..., StreamChunk: _Optional[_Union[_platform_pb2.StreamChunk, _Mapping]] = ...) -> None: ...
