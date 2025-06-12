import queue
from typing import Any, AsyncIterator

from spec.models import Buffer


class RawObjectBuffer(Buffer):
    def __init__(self):
        super().__init__()
        self._queue: queue.Queue[Any] = queue.Queue()

    async def write(self, obj: Any):
        self._queue.put(obj)

    async def close(self):
        self._queue.put(None)

    async def stream(self) -> AsyncIterator[Any]:
        while True:
            item = self._queue.get()
            if item is None:
                break
            yield item