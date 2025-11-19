from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Language(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LANG_UNKNOWN: _ClassVar[Language]
    LANG_JSON: _ClassVar[Language]
    LANG_GO: _ClassVar[Language]
    LANG_PYTHON: _ClassVar[Language]
LANG_UNKNOWN: Language
LANG_JSON: Language
LANG_GO: Language
LANG_PYTHON: Language

class ObjectRef(_message.Message):
    __slots__ = ("ID", "Source")
    ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    ID: str
    Source: str
    def __init__(self, ID: _Optional[str] = ..., Source: _Optional[str] = ...) -> None: ...

class EncodedObject(_message.Message):
    __slots__ = ("ID", "Data", "Source", "Language", "IsStream")
    ID_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    ISSTREAM_FIELD_NUMBER: _ClassVar[int]
    ID: str
    Data: bytes
    Source: str
    Language: Language
    IsStream: bool
    def __init__(self, ID: _Optional[str] = ..., Data: _Optional[bytes] = ..., Source: _Optional[str] = ..., Language: _Optional[_Union[Language, str]] = ..., IsStream: bool = ...) -> None: ...

class StreamChunk(_message.Message):
    __slots__ = ("ObjectID", "Offset", "EoS", "Value", "Error")
    OBJECTID_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    EOS_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    ObjectID: str
    Offset: int
    EoS: bool
    Value: EncodedObject
    Error: str
    def __init__(self, ObjectID: _Optional[str] = ..., Offset: _Optional[int] = ..., EoS: bool = ..., Value: _Optional[_Union[EncodedObject, _Mapping]] = ..., Error: _Optional[str] = ...) -> None: ...
