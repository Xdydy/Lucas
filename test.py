from threading import Thread
import time
def func(i):
    time.sleep(1)
    raise Exception("error")
    print(f"thread {i} finished")
    return i

task1 = Thread(target=func, args=(1,))
task2 = Thread(target=func, args=(2,))
task1.start()
task2.start()
while task1.is_alive():
    time.sleep(0.1)
    print("waiting")