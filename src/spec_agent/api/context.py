# context.py
import asyncio
import contextvars
from collections import defaultdict
from typing import Dict, List

from agents import TResponseInputItem

# ❶ ContextVar giữ session-id hiện hành
current_sid: contextvars.ContextVar[str | None] = contextvars.ContextVar("sid", default=None)

class SessionStore:
    def __init__(self): 
        self.init_time: Dict[str, str] = {}
        self.user: Dict[str, str] = {}
        self.locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.ctx:  Dict[str, List[TResponseInputItem]] = defaultdict(list)

    def get_lock(self) -> asyncio.Lock:  
        return self.locks[current_sid.get()]

    def drop(self, sid: str):
        self.ctx.pop(sid, None)
        self.init_time.pop(sid, None)
        self.user.pop(sid, None)
        self.locks.pop(sid, None)
        
sessions = SessionStore()