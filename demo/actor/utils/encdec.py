import base64
import inspect
import json
import queue
import sys
import uuid

from typing import Any, TypedDict, Iterable

import cloudpickle

from ..protos import platform_pb2 as platform

LANG_PYTHON = platform.LANG_PYTHON
LANG_GO = platform.LANG_GO
LANG_JSON = platform.LANG_JSON


class EncodedObject(TypedDict):
    Data: str
    Language: int


class Streams:
    streams: dict[str, queue.Queue[Any]] = {}

    @classmethod
    def register(cls, name: str) -> Iterable[Any]:
        print(f"register {name}", file=sys.stderr)
        q = queue.Queue[Any]()
        cls.streams[name] = q

        def generator(q):
            while True:
                obj = q.get()
                cls.streams[name].task_done()
                if obj is None:
                    break

                yield obj

        return generator(q)

    @classmethod
    def put(cls, name: str, obj: Any):
        if name not in cls.streams:
            return
        cls.streams[name].put(obj)

    @classmethod
    def close(cls, name: str):
        if name not in cls.streams:
            return
        print(f"close {name}", file=sys.stderr)
        cls.streams[name].put(None)


class EncDec:
    @staticmethod
    def next_id() -> str:
        return "obj." + str(uuid.uuid4())

    @staticmethod
    def decode(obj: platform.EncodedObject):
        if obj.Stream:  # receives stream
            return Streams.register(obj.ID)

        data = obj.Data
        match obj.Language:
            case platform.LANG_PYTHON:
                return cloudpickle.loads(data)
            case platform.LANG_JSON:
                return json.loads(data)
            case _:
                raise ValueError(f"dec: unsupported language {obj.Language}")

    @staticmethod
    def decode_dict(obj: EncodedObject):
        data = base64.decodebytes(obj["Data"].encode())
        match lang := obj["Language"]:
            case platform.LANG_PYTHON:
                return cloudpickle.loads(data)
            case platform.LANG_JSON:
                return json.loads(data)
            case _:
                raise ValueError(f"dec: unsupported language {lang}")

    @classmethod
    def encode(
        cls, obj: Any, language: platform.Language = LANG_JSON
    ) -> platform.EncodedObject:
        if inspect.isgenerator(obj):
            print(f"get generator {obj}", file=sys.stderr)
            return platform.EncodedObject(
                ID=cls.next_id(), Stream=True, Language=language
            )

        match language:
            case platform.LANG_PYTHON:
                data = cloudpickle.dumps(obj)
            case platform.LANG_JSON:
                data = json.dumps(obj).encode()
            case _:
                raise ValueError(f"enc: unsupported language {language}")
        return platform.EncodedObject(ID=cls.next_id(), Data=data, Language=language)
