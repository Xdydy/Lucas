import base64
import inspect
import json
import queue
import sys
import uuid

from typing import Any, TypedDict, Iterable

import cloudpickle
import sys
from ..protos.common import types_pb2 as common

LANG_PYTHON = common.LANG_PYTHON
LANG_GO = common.LANG_GO
LANG_JSON = common.LANG_JSON


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
    def decode(obj: common.EncodedObject):
        if obj.IsStream:  # receives stream (field name changed from Stream to IsStream)
            return Streams.register(obj.ID)

        data = obj.Data
        match obj.Language:
            case common.LANG_PYTHON:
                return cloudpickle.loads(data)
            case common.LANG_JSON:
                return json.loads(data)
            case _:
                raise ValueError(f"dec: unsupported language {obj.Language}")

    @staticmethod
    def decode_dict(obj: EncodedObject):
        data = base64.decodebytes(obj["Data"].encode())
        match lang := obj["Language"]:
            case common.LANG_PYTHON:
                return cloudpickle.loads(data)
            case common.LANG_JSON:
                return json.loads(data)
            case _:
                raise ValueError(f"dec: unsupported language {lang}")

    @classmethod
    def encode(
        cls, obj: Any, language: common.Language = LANG_JSON
    ) -> common.EncodedObject:
        if inspect.isgenerator(obj):
            print(f"get generator {obj}", file=sys.stderr)
            return common.EncodedObject(
                ID=cls.next_id(), IsStream=True, Language=language  # Field name changed from Stream to IsStream
            )

        match language:
            case common.LANG_PYTHON:
                data = cloudpickle.dumps(obj)
            case common.LANG_JSON:
                data = json.dumps(obj).encode()
            case _:
                raise ValueError(f"enc: unsupported language {language}")
        return common.EncodedObject(ID=cls.next_id(), Data=data, Language=language)
