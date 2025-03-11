from rocketmq.client import PushConsumer, ConsumeStatus

def callback(msg):
    print(msg)
    return ConsumeStatus.CONSUME_SUCCESS

try:
    consumer = PushConsumer('test')
    consumer.set_name_server_address('10.0.0.101:9876')
    consumer.subscribe('test',callback)
    consumer.start()
    import time
    time.sleep(5)
    consumer.shutdown()
except Exception as e:
    print(f"Exception: {e.__doc__}")