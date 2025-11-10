from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class GetObjectRequest(_message.Message):
    __slots__ = ("object_ref",)
    OBJECT_REF_FIELD_NUMBER: _ClassVar[int]
    object_ref: str
    def __init__(self, object_ref: _Optional[str] = ...) -> None: ...

class GetObjectResponse(_message.Message):
    __slots__ = ("object_data", "error")
    OBJECT_DATA_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    object_data: bytes
    error: str
    def __init__(self, object_data: _Optional[bytes] = ..., error: _Optional[str] = ...) -> None: ...

class PutObjectRequest(_message.Message):
    __slots__ = ("object_data",)
    OBJECT_DATA_FIELD_NUMBER: _ClassVar[int]
    object_data: bytes
    def __init__(self, object_data: _Optional[bytes] = ...) -> None: ...

class PutObjectResponse(_message.Message):
    __slots__ = ("object_ref", "error")
    OBJECT_REF_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    object_ref: str
    error: str
    def __init__(self, object_ref: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...
