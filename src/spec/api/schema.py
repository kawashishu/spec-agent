import asyncio
import io
import json
from base64 import b64encode
from datetime import datetime
from typing import Any, AsyncIterator, List

import pandas as pd
import pyarrow as pa
import pytz
from matplotlib.figure import Figure
from PIL import Image
from pydantic import BaseModel

from spec.models import Buffer


def _b64(data: bytes) -> str:
    return b64encode(data).decode()

def _ser(obj: Any) -> dict:
    try:
        if isinstance(obj, str):
            return {"kind": "text", "data": obj}
        if isinstance(obj, bytes):
            return {"kind": "bytes", "b64": _b64(obj)}
        if isinstance(obj, pd.DataFrame):
            buf = pa.ipc.serialize_pandas(obj)
            return {"kind": "dataframe_arrow", "b64": _b64(buf)}
        if isinstance(obj, Image.Image):
            buf = io.BytesIO(); obj.save(buf, format="PNG")
            return {"kind": "image/png", "b64": _b64(buf.getvalue())}
        if isinstance(obj, Figure):
            buf = io.BytesIO(); obj.savefig(buf, format="png", bbox_inches="tight")
            return {"kind": "image/png", "b64": _b64(buf.getvalue())}
    except Exception as e:
        raise ValueError(f"Cannot serialize object: {e}")    

class Message(BaseModel):
    role: str
    content: str
    
class Session(BaseModel):
    id: str
    username: str
    messages: List[Message] = []
    init_time: str = datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).strftime("%Y%m%d_%H%M%S")

# ────── API payloads ───────────────────────────────────────────
class CreateSessionRequest(BaseModel):
    username: str

class CreateSessionResponse(BaseModel):
    session_id: str

class ChatRequest(BaseModel):
    session_id: str
    message: str

class SerializedStreamBuffer(Buffer):
    def __init__(self):
        super().__init__()
        self._queue: asyncio.Queue = asyncio.Queue()

    async def write(self, obj: Any):
        await self._queue.put(_ser(obj))

    async def close(self):
        await self._queue.put(None)

    async def stream(self) -> AsyncIterator[str]:
        while True:
            item = await self._queue.get()
            if item is None:
                break
            yield json.dumps(item, separators=(",", ":")) + "\n"
            