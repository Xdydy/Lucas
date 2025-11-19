import logging
import atexit
from typing import Optional

from protos.common import logger_pb2 as common_logger_pb2
from protos.logger import logger_pb2, logger_pb2_grpc

import grpc
import time
import queue
import threading

# logging 级别到 proto LogLevel 的映射
_LEVEL_MAP = {
    logging.DEBUG: common_logger_pb2.LOG_LEVEL_DEBUG,
    logging.INFO: common_logger_pb2.LOG_LEVEL_INFO,
    logging.WARNING: common_logger_pb2.LOG_LEVEL_WARN,
    logging.ERROR: common_logger_pb2.LOG_LEVEL_ERROR,
    logging.CRITICAL: common_logger_pb2.LOG_LEVEL_FATAL,
}


_SENTINEL = object()


def setup_logging(logger: logging.Logger, application_id: str, logger_addr: str):
    handler = RemoteLogHandler(application_id, logger_addr)
    logger.addHandler(handler)
    atexit.register(handler.close)
    return handler


class RemoteLogHandler(logging.Handler):

    def __init__(self, application_id: str, logger_addr: str):
        super().__init__()

        self._logger_addr = logger_addr
        self._application_id = application_id
        self._closed = False
        self._stop_event = threading.Event()

        # 创建 gRPC 连接
        self._channel = grpc.insecure_channel(
            logger_addr,
            options=[("grpc.max_receive_message_length", 512 * 1024 * 1024)],
        )
        self._stub = logger_pb2_grpc.LoggerServiceStub(self._channel)
        self._q = queue.Queue()
        self._response_stream = self._stub.StreamLogs(self._generate())
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _generate(self):
        while not self._stop_event.is_set():
            try:
                msg = self._q.get(timeout=0.1)
            except queue.Empty:
                continue
            if msg is _SENTINEL:
                break
            yield msg

    def _run(self):
        while not self._stop_event.is_set():
            try:
                for response in self._response_stream:
                    if self._stop_event.is_set():
                        break
                    if not response.success and response.error:
                        print(f"Log service error: {response.error}")
            except Exception as e:
                if self._stop_event.is_set():
                    break
                print(f"Stream error: {e}")
                time.sleep(1)

    def emit(self, record: logging.LogRecord):
        if self._closed:
            return
        try:
            proto_level = _LEVEL_MAP.get(
                record.levelno, common_logger_pb2.LOG_LEVEL_UNKNOWN)

            fields = []
            standard_attrs = {
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message',
                'pathname', 'process', 'processName', 'relativeCreated', 'thread',
                'threadName', 'exc_info', 'exc_text', 'stack_info', 'getMessage', "asctime"
            }
            
            # 遍历 LogRecord 的所有属性，找出自定义字段
            import json
            for key, value in record.__dict__.items():
                # 跳过标准属性和私有属性
                if key in standard_attrs or key.startswith('_'):
                    continue
                # 将自定义字段添加到 fields
                field = common_logger_pb2.LogField(
                    key=key,
                    value=json.dumps(value) if not isinstance(value, str) else value
                )
                fields.append(field)
            
            # 添加异常信息（如果有）
            if record.exc_info:
                exc_text = self.formatException(record.exc_info)
                fields.append(common_logger_pb2.LogField(
                    key='exception',
                    value=exc_text
                ))

            stream_msg = logger_pb2.LogStreamMessage(
                application_id=self._application_id,
                entry=common_logger_pb2.LogEntry(
                    timestamp=int(time.time_ns()),
                    level=proto_level,
                    message=record.getMessage(),
                    fields=fields,
                    caller=common_logger_pb2.CallerInfo(
                        file=record.filename,
                        line=record.lineno,
                        function=record.funcName,
                    ),
                )
            )
            self._q.put(stream_msg)
        except Exception as e:
            print(f"Log emit error: {e}")

    def flush(self):
        deadline = time.time() + 2.0
        while not self._q.empty() and time.time() < deadline:
            time.sleep(0.05)

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.flush()
            self._stop_event.set()
            self._q.put(_SENTINEL)
            if self._thread.is_alive():
                self._thread.join(timeout=2.0)
            try:
                self._response_stream.cancel()
            except Exception:
                pass
            self._channel.close()
        finally:
            super().close()
