from rocketmq.client import Producer, Message

producer = Producer('test')
producer.set_name_server_address('10.0.0.101:9876')
producer.start()

msg = Message('test')
msg.set_body('hello')
ret = producer.send_sync(msg)
print(ret)

