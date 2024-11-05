from .runtime import (
    Runtime,
    createRuntimeMetadata,
    FaasitResult,
    RuntimeMetadata,
    CallResult,
    InputType,
    TellParams
)

def load_runtime(provider) -> Runtime:
    match provider:
        case 'aliyun':
            from .aliyun_runtime import AliyunRuntime
            return AliyunRuntime
        case 'local':
            from .local_runtime import LocalRuntime
            return LocalRuntime
        case 'local-once':
            from .local_once_runtime import LocalOnceRuntime
            return LocalOnceRuntime
        case 'knative':
            from .kn_runtime import KnativeRuntime
            return KnativeRuntime
        case _:
            raise ValueError(f"Invalid provider {provider}")

__all__ = [
    "Runtime",
    "createRuntimeMetadata",
    "FaasitResult",
    "RuntimeMetadata",
    "CallResult",
    "InputType",
    "TellParams",
    "load_runtime"
]