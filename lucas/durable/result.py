from .state import (
    DurableFunctionState,
    ScopedDurableStateClient
)

# import asyncio

class DurableWaitingResult:
    def __init__(self, task) -> None:
        self.task = task
        pass
    def waitResult(self):
        print("Waiting Durable result...")
        yield self.task
        result = self.task()
        return result
    def setResult(self, value):
        # self.queue.put(value)
        pass