from concurrent.futures import Future
from threading import Lock
count = 0
lock = Lock()

def test_future_set_result():
    future = Future()
    future.set_result(42)
    return future

def call_back(future):
    global count
    with lock:
        count += 1


for i in range(10):
    result = test_future_set_result()
    result.add_done_callback(call_back)
print(count)