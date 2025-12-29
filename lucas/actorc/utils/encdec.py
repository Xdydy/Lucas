import base64
import inspect
import json
import queue
import subprocess
import sys
import uuid

from typing import Any, TypedDict, Iterable

import cloudpickle
import sys
from protos.common import types_pb2 as common

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
            case common.LANG_GO:
                # Go 对象使用 gob 编码，Python 无法直接解码
                # 通过调用 Go 脚本将 gob 转换为 JSON
                return EncDec._decode_gob_to_json(data)
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
            case common.LANG_GO:
                # Go 对象使用 gob 编码，Python 无法直接解码
                # 通过调用 Go 脚本将 gob 转换为 JSON
                return EncDec._decode_gob_to_json(data)
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

    @staticmethod
    def _decode_gob_to_json(gob_data: bytes) -> Any:
        """
        将 Go gob 编码的数据转换为 JSON，然后解码为 Python 对象
        通过调用 Go 脚本实现转换
        """
        import tempfile
        import os

        # Go 脚本：解码 gob 并转换为 JSON
        go_script = '''package main

import (
	"encoding/gob"
	"encoding/json"
	"fmt"
	"os"
	"bytes"
)

func main() {
	// 从标准输入读取 gob 数据
	gob_data := make([]byte, 0)
	buf := make([]byte, 4096)
	for {
		n, err := os.Stdin.Read(buf)
		if n > 0 {
			gob_data = append(gob_data, buf[:n]...)
		}
		if err != nil {
			break
		}
	}

	if len(gob_data) == 0 {
		fmt.Fprintf(os.Stderr, "ERROR: no gob data received\\n")
		os.Exit(1)
	}

	// 使用 gob 解码对象
	// gob 解码时，如果编码端使用具体类型，解码端使用 interface{} 可能失败
	// 需要尝试多种常见类型的解码
	var obj interface{}
	
	// 尝试按顺序解码为常见类型
	// 1. 尝试 string（最常见）
	dec := gob.NewDecoder(bytes.NewReader(gob_data))
	var str string
	if err := dec.Decode(&str); err == nil {
		obj = str
	} else {
		// 2. 尝试 int
		dec = gob.NewDecoder(bytes.NewReader(gob_data))
		var i int
		if err := dec.Decode(&i); err == nil {
			obj = i
		} else {
			// 3. 尝试 int64
			dec = gob.NewDecoder(bytes.NewReader(gob_data))
			var i64 int64
			if err := dec.Decode(&i64); err == nil {
				obj = i64
			} else {
				// 4. 尝试 float64
				dec = gob.NewDecoder(bytes.NewReader(gob_data))
				var f float64
				if err := dec.Decode(&f); err == nil {
					obj = f
				} else {
					// 5. 尝试 bool
					dec = gob.NewDecoder(bytes.NewReader(gob_data))
					var b bool
					if err := dec.Decode(&b); err == nil {
						obj = b
					} else {
						// 6. 尝试 []string
						dec = gob.NewDecoder(bytes.NewReader(gob_data))
						var strSlice []string
						if err := dec.Decode(&strSlice); err == nil {
							obj = strSlice
						} else {
							// 7. 尝试 []int
							dec = gob.NewDecoder(bytes.NewReader(gob_data))
							var intSlice []int
							if err := dec.Decode(&intSlice); err == nil {
								obj = intSlice
							} else {
								// 8. 尝试 map[string]string
								dec = gob.NewDecoder(bytes.NewReader(gob_data))
								var m2 map[string]string
								if err := dec.Decode(&m2); err == nil {
									obj = m2
								} else {
									// 9. 尝试 map[string]interface{}（需要先注册类型）
									dec = gob.NewDecoder(bytes.NewReader(gob_data))
									gob.Register(map[string]interface{}(nil))
									var m map[string]interface{}
									if err := dec.Decode(&m); err == nil {
										obj = m
									} else {
										// 10. 尝试 []interface{}（需要先注册类型）
										dec = gob.NewDecoder(bytes.NewReader(gob_data))
										gob.Register([]interface{}(nil))
										var slice []interface{}
										if err := dec.Decode(&slice); err == nil {
											obj = slice
										} else {
											// 所有类型都失败，输出错误
											fmt.Fprintf(os.Stderr, "ERROR: failed to decode gob with any known type. Last error: %v\\n", err)
											os.Exit(1)
										}
									}
								}
							}
						}
					}
				}
			}
		}
	}

	// 转换为 JSON
	json_data, err := json.Marshal(obj)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: failed to marshal to JSON: %v\\n", err)
		os.Exit(1)
	}

	// 输出 JSON 字符串
	fmt.Print(string(json_data))
}
'''

        try:
            # 创建临时文件保存 Go 脚本
            with tempfile.NamedTemporaryFile(mode='w', suffix='.go', delete=False) as f:
                f.write(go_script)
                temp_go_file = f.name

            try:
                # 执行 Go 脚本，将 gob 数据通过标准输入传递
                result = subprocess.run(
                    ['go', 'run', temp_go_file],
                    input=gob_data,
                    capture_output=True,
                    check=False,
                    timeout=10
                )

                # 检查是否有错误
                if result.returncode != 0:
                    error_msg = result.stderr.decode('utf-8', errors='replace').strip() if result.stderr else "unknown error"
                    raise ValueError(f"Go script execution failed: {error_msg}")

                # 解析 JSON 输出
                json_str = result.stdout.decode('utf-8', errors='replace').strip()
                if json_str.startswith("ERROR:"):
                    raise ValueError(f"Go script error: {json_str}")

                # 返回解码后的 Python 对象
                return json.loads(json_str)

            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_go_file)
                except Exception:
                    pass

        except subprocess.TimeoutExpired:
            raise ValueError("Go script execution timeout")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode JSON from Go script: {e}")
        except Exception as e:
            raise ValueError(f"Failed to decode gob data: {e}")
