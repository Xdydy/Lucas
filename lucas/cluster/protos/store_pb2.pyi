from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ObjectType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BYTES: _ClassVar[ObjectType]
    GENERATOR: _ClassVar[ObjectType]
BYTES: ObjectType
GENERATOR: ObjectType

class GetObjectRequest(_message.Message):
    __slots__ = ("ref",)
    REF_FIELD_NUMBER: _ClassVar[int]
    ref: str
    def __init__(self, ref: _Optional[str] = ...) -> None: ...

class GetObjectResponse(_message.Message):
    __slots__ = ("data", "error", "type")
    DATA_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    data: bytes
    error: str
    type: ObjectType
    def __init__(self, data: _Optional[bytes] = ..., error: _Optional[str] = ..., type: _Optional[_Union[ObjectType, str]] = ...) -> None: ...

class PutObjectRequest(_message.Message):
    __slots__ = ("data", "key", "type")
    DATA_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    data: bytes
    key: str
    type: ObjectType
    def __init__(self, data: _Optional[bytes] = ..., key: _Optional[str] = ..., type: _Optional[_Union[ObjectType, str]] = ...) -> None: ...

class DeleteObjectRequest(_message.Message):
    __slots__ = ("ref",)
    REF_FIELD_NUMBER: _ClassVar[int]
    ref: str
    def __init__(self, ref: _Optional[str] = ...) -> None: ...

class DeleteObjectResponse(_message.Message):
    __slots__ = ("success", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    error: str
    def __init__(self, success: bool = ..., error: _Optional[str] = ...) -> None: ...

class ClearStoreRequest(_message.Message):
    __slots__ = ("prefix",)
    PREFIX_FIELD_NUMBER: _ClassVar[int]
    prefix: str
    def __init__(self, prefix: _Optional[str] = ...) -> None: ...

class ClearStoreResponse(_message.Message):
    __slots__ = ("error",)
    ERROR_FIELD_NUMBER: _ClassVar[int]
    error: str
    def __init__(self, error: _Optional[str] = ...) -> None: ...

class PutObjectResponse(_message.Message):
    __slots__ = ("ref", "error")
    REF_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    ref: str
    error: str
    def __init__(self, ref: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class Publish(_message.Message):
    __slots__ = ("ref",)
    REF_FIELD_NUMBER: _ClassVar[int]
    ref: str
    def __init__(self, ref: _Optional[str] = ...) -> None: ...

class Subscribe(_message.Message):
    __slots__ = ("ref", "subscriber_id")
    REF_FIELD_NUMBER: _ClassVar[int]
    SUBSCRIBER_ID_FIELD_NUMBER: _ClassVar[int]
    ref: str
    subscriber_id: str
    def __init__(self, ref: _Optional[str] = ..., subscriber_id: _Optional[str] = ...) -> None: ...
