from concurrent.futures import Future

def func():
    # return 3
    raise ValueError("An error occurred")

def get_future() -> Future:
    f = Future()
    try:
        result = func()
        f.set_result(result)
    except Exception as e:
        f.set_exception(e)
    return f

f = get_future()
try:
    result = f.result()  # This will raise the ValueError with the message "An error occurred"
    print(f"Function result: {result}")
except Exception as e:
    print(f"Caught exception from future: {e}")