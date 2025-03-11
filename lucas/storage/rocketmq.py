import os
import ctypes
from pathlib import Path

module_dir = Path(__file__).parent.parent

os.environ['LD_LIBRARY_PATH'] = f"{str(module_dir / 'lib')}:{os.environ.get('LD_LIBRARY_PATH', '')}"

from typing import Any, Callable
from rocketmq.client import Producer, Message, PushConsumer, ConsumeStatus

class RocketMQProducer:
    def __init__(self, name_server_address: str, port: int, name:str):
        self._name = name
        self._name_server_address = name_server_address
        self._port = port
        self._producer = Producer(self._name)
        self._producer.set_name_server_address(f'{self._name_server_address}:{self._port}')
        self._producer.start()
    def send(self, topic: str, body: Any):
        msg = Message(topic)
        msg.set_body(body)
        return self._producer.send_sync(msg)
    def stop(self):
        self._producer.shutdown()

class RocketMQConsumer:
    def __init__(self, 
                 name_server_address: str, 
                 port: int, 
                 name:str, 
                 topics: list[str],
                 callback:Callable[[ConsumeStatus], Any]):
        self._name = name
        self._name_server_address = name_server_address
        self._port = port
        self._consumer = PushConsumer(self._name)
        self._consumer.set_name_server_address(f'{self._name_server_address}:{self._port}')
        self._callback = callback
        for topic in topics:
            self._consumer.subscribe(topic, self._callback)
        self._consumer.start()
    def stop(self):
        self._consumer.shutdown()