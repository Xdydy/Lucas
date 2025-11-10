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
    APPEND_FUNCTION: _ClassVar[MessageType]
    APPEND_FUNCTION_ARG: _ClassVar[MessageType]
    APPEND_CLASS: _ClassVar[MessageType]
    APPEND_CLASS_METHOD_ARG: _ClassVar[MessageType]
    INVOKE_FUNCTION: _ClassVar[MessageType]
    RT_RESULT: _ClassVar[MessageType]
UNSPECIFIED: MessageType
ACK: MessageType
APPEND_FUNCTION: MessageType
APPEND_FUNCTION_ARG: MessageType
APPEND_CLASS: MessageType
APPEND_CLASS_METHOD_ARG: MessageType
INVOKE_FUNCTION: MessageType
RT_RESULT: MessageType

class Data(_message.Message):
    __slots__ = ("type", "ref", "encoded")
    class ObjectType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        OBJ_UNSPECIFIED: _ClassVar[Data.ObjectType]
        OBJ_REF: _ClassVar[Data.ObjectType]
        OBJ_ENCODED: _ClassVar[Data.ObjectType]
        OBJ_STREAM: _ClassVar[Data.ObjectType]
    OBJ_UNSPECIFIED: Data.ObjectType
    OBJ_REF: Data.ObjectType
    OBJ_ENCODED: Data.ObjectType
    OBJ_STREAM: Data.ObjectType
    TYPE_FIELD_NUMBER: _ClassVar[int]
    REF_FIELD_NUMBER: _ClassVar[int]
    ENCODED_FIELD_NUMBER: _ClassVar[int]
    type: Data.ObjectType
    ref: str
    encoded: bytes
    def __init__(self, type: _Optional[_Union[Data.ObjectType, str]] = ..., ref: _Optional[str] = ..., encoded: _Optional[bytes] = ...) -> None: ...

class Ack(_message.Message):
    __slots__ = ("message", "error")
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    message: str
    error: str
    def __init__(self, message: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class AppendFunction(_message.Message):
    __slots__ = ("function_name", "function_code", "params", "requirements")
    FUNCTION_NAME_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_CODE_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    REQUIREMENTS_FIELD_NUMBER: _ClassVar[int]
    function_name: str
    function_code: bytes
    params: _containers.RepeatedScalarFieldContainer[str]
    requirements: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, function_name: _Optional[str] = ..., function_code: _Optional[bytes] = ..., params: _Optional[_Iterable[str]] = ..., requirements: _Optional[_Iterable[str]] = ...) -> None: ...

class AppendFunctionArg(_message.Message):
    __slots__ = ("session_id", "instance_id", "function_name", "param_name", "value")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_NAME_FIELD_NUMBER: _ClassVar[int]
    PARAM_NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    instance_id: str
    function_name: str
    param_name: str
    value: Data
    def __init__(self, session_id: _Optional[str] = ..., instance_id: _Optional[str] = ..., function_name: _Optional[str] = ..., param_name: _Optional[str] = ..., value: _Optional[_Union[Data, _Mapping]] = ...) -> None: ...

class AppendClass(_message.Message):
    __slots__ = ("class_name", "class_code", "requirements")
    class Method(_message.Message):
        __slots__ = ("method_name", "params")
        METHOD_NAME_FIELD_NUMBER: _ClassVar[int]
        PARAMS_FIELD_NUMBER: _ClassVar[int]
        method_name: str
        params: _containers.RepeatedScalarFieldContainer[str]
        def __init__(self, method_name: _Optional[str] = ..., params: _Optional[_Iterable[str]] = ...) -> None: ...
    CLASS_NAME_FIELD_NUMBER: _ClassVar[int]
    CLASS_CODE_FIELD_NUMBER: _ClassVar[int]
    REQUIREMENTS_FIELD_NUMBER: _ClassVar[int]
    class_name: str
    class_code: bytes
    requirements: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, class_name: _Optional[str] = ..., class_code: _Optional[bytes] = ..., requirements: _Optional[_Iterable[str]] = ...) -> None: ...

class AppendClassMethodArg(_message.Message):
    __slots__ = ("session_id", "instance_id", "class_name", "method_name", "param_name", "value")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    CLASS_NAME_FIELD_NUMBER: _ClassVar[int]
    METHOD_NAME_FIELD_NUMBER: _ClassVar[int]
    PARAM_NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    instance_id: str
    class_name: str
    method_name: str
    param_name: str
    value: Data
    def __init__(self, session_id: _Optional[str] = ..., instance_id: _Optional[str] = ..., class_name: _Optional[str] = ..., method_name: _Optional[str] = ..., param_name: _Optional[str] = ..., value: _Optional[_Union[Data, _Mapping]] = ...) -> None: ...

class InvokeFunction(_message.Message):
    __slots__ = ("session_id", "instance_id", "function_name")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_NAME_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    instance_id: str
    function_name: str
    def __init__(self, session_id: _Optional[str] = ..., instance_id: _Optional[str] = ..., function_name: _Optional[str] = ...) -> None: ...

class ReturnResult(_message.Message):
    __slots__ = ("session_id", "instance_id", "function_name", "value", "error")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    instance_id: str
    function_name: str
    value: Data
    error: str
    def __init__(self, session_id: _Optional[str] = ..., instance_id: _Optional[str] = ..., function_name: _Optional[str] = ..., value: _Optional[_Union[Data, _Mapping]] = ..., error: _Optional[str] = ...) -> None: ...

class Message(_message.Message):
    __slots__ = ("type", "ack", "append_function", "append_function_arg", "append_class", "append_class_method_arg", "invoke_function", "return_result")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ACK_FIELD_NUMBER: _ClassVar[int]
    APPEND_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    APPEND_FUNCTION_ARG_FIELD_NUMBER: _ClassVar[int]
    APPEND_CLASS_FIELD_NUMBER: _ClassVar[int]
    APPEND_CLASS_METHOD_ARG_FIELD_NUMBER: _ClassVar[int]
    INVOKE_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    RETURN_RESULT_FIELD_NUMBER: _ClassVar[int]
    type: MessageType
    ack: Ack
    append_function: AppendFunction
    append_function_arg: AppendFunctionArg
    append_class: AppendClass
    append_class_method_arg: AppendClassMethodArg
    invoke_function: InvokeFunction
    return_result: ReturnResult
    def __init__(self, type: _Optional[_Union[MessageType, str]] = ..., ack: _Optional[_Union[Ack, _Mapping]] = ..., append_function: _Optional[_Union[AppendFunction, _Mapping]] = ..., append_function_arg: _Optional[_Union[AppendFunctionArg, _Mapping]] = ..., append_class: _Optional[_Union[AppendClass, _Mapping]] = ..., append_class_method_arg: _Optional[_Union[AppendClassMethodArg, _Mapping]] = ..., invoke_function: _Optional[_Union[InvokeFunction, _Mapping]] = ..., return_result: _Optional[_Union[ReturnResult, _Mapping]] = ...) -> None: ...
