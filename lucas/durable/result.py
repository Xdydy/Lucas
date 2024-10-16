from .state import (
    DurableFunctionState,
    ScopedDurableStateClient
)

import asyncio

class DurableWaitingResult:
    def __init__(self) -> None:
        self.queue = asyncio.Queue()
        pass
    async def waitResult(self):
        # result = await self._task
        # if isinstance(result,DurableWaitingResult):
        #     result = await result.waitResult()
        # if not isinstance(result,DurableWaitingResult):
        #     await self._state.saveResult(self._client,result)
        print("Waiting Durable result...")
        result = await self.queue.get()
        return result
    async def setResult(self, value):
        await self.queue.put(value)
        pass