# printer.py
import asyncio
import base64
import io
import json
import pickle
from typing import Any, Dict, Optional

import pandas as pd
from matplotlib.figure import Figure
from PIL import Image

from spec.api.context import current_sid
from spec.models import EndStream


def _ser(obj: Any, sender: str | None) -> dict:
    if isinstance(obj, str):
        return {"kind": "text", "data": obj, "sender": sender}
    if isinstance(obj, bytes):
        return {"kind": "bytes", "b64": base64.b64encode(obj).decode(), "sender": sender}
    if isinstance(obj, pd.DataFrame):
        return {"kind": "dataframe", "data": obj.to_dict("split"), "sender": sender}
    if isinstance(obj, Image.Image):
        buf = io.BytesIO(); obj.save(buf, format="PNG")
        return {"kind": "image/png", "b64": base64.b64encode(buf.getvalue()).decode(), "sender": sender}
    if isinstance(obj, Figure):
        buf = io.BytesIO(); obj.savefig(buf, format="png", bbox_inches="tight")
        return {"kind": "image/png", "b64": base64.b64encode(buf.getvalue()).decode(), "sender": sender}
    if isinstance(obj, EndStream):
        return {"kind": "end_stream", "status": obj.status, "sender": sender}
    return {"kind": "pickle", "b64": base64.b64encode(pickle.dumps(obj)).decode(), "sender": sender}

class AsyncPrinter:
    def __init__(self):
        self._queues: Dict[str, asyncio.Queue[Optional[dict]]] = {}

    async def write(self, obj, *, sender: str | None = None):
        sid = current_sid.get()
        if sid is None:
            raise RuntimeError("current_sid chưa set()")
        self._queues.setdefault(sid, asyncio.Queue())
        await self._queues[sid].put(_ser(obj, sender))

    async def close(self):
        q = self._queues.get(current_sid.get())
        if q: await q.put(None)

    async def stream(self):
        q = self._queues.setdefault(current_sid.get(), asyncio.Queue())
        while (item := await q.get()) is not None:
            yield json.dumps(item, separators=(",", ":")) + "\n"

printer = AsyncPrinter()
