import asyncio
import io
import json
from base64 import b64encode
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

import pandas as pd
import pyarrow as pa
import pytz
from matplotlib.figure import Figure
from PIL import Image
from pydantic import BaseModel, Field


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


class BufferListener:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()

    async def write(self, obj: Any):
        await self._queue.put(_ser(obj))

    async def close(self):
        await self._queue.put(None)

    async def stream(self):
        while (item := await self._queue.get()) is not None:
            yield json.dumps(item, separators=(",", ":")) + "\n"

@dataclass    
class ContextHook:
    buffer: BufferListener

class AgentName(Enum):
    BOM_AGENT = "BOM Agent"
    SPECBOOK_AGENT = "Specbook Agent"
    TRIAGE_AGENT = "Triage Agent"
    
    def __str__(self):
        return self.value

class SpecbookRelevanceContent(BaseModel):
    reasoning: str = Field(
        ...,
        description=(
            "A clear and detailed justification explaining the exact data types required by the provided query, "
            "the precise locations (section name, title, data table, page number, etc.) of these data types in the specbook, "
            "and explicit analysis or inference, including reasoning about abbreviations or acronyms when necessary."
        )
    )
    relevance_content: str = Field(
        ...,
        description=(
            "The explicitly extracted comprehensive content from the specbook document that accurately and completely "
            "addresses the specific data requirements identified in the query."
        )
    )
    is_relevant: bool = Field(
        ...,
        description=(
            "A boolean classification explicitly stating whether the provided specbook document contains exact, complete, "
            "and directly relevant information fully satisfying the query (True), or lacks the necessary information (False)."
        )
    )

class Specbook(BaseModel):
    specbook_number: str
    content: str

class SingletonMeta(type):
    """A Singleton metaclass."""

    _instances: Dict[Any, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:   
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
