from __future__ import annotations

import asyncio
import json
import os
from typing import Dict, List
from uuid import uuid4

from agents import Runner
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from openai.types.responses import ResponseTextDeltaEvent
from pydantic import BaseModel

from spec.agents import triage_agent
from spec.config import settings
from spec.models import ContextHook, LiveStream
from spec.utils.utils import save_messages

# In-memory sessions keyed by UUID
_sessions: Dict[str, "Session"] = {}


class Message(BaseModel):
    role: str
    content: str

class Session(BaseModel):
    username: str
    messages: List[Message] = []

# ────── API payloads ───────────────────────────────────────────
class CreateSessionRequest(BaseModel):
    username: str

class CreateSessionResponse(BaseModel):
    session_id: str

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str

app = FastAPI()
_sessions: Dict[str, Session] = {}

# ───── 1. New chat ─────────────────────────────────────────────
@app.post("/sessions", response_model=CreateSessionResponse, status_code=201)
async def create_session(req: CreateSessionRequest):
    session_id = str(uuid4())
    _sessions[session_id] = Session(username=req.username)
    return {"session_id": session_id}

# ───── 2. Chat / post message ──────────────────────────────────
@app.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def chat(session_id: str, req: ChatRequest):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Invalid session")

    # append user message 
    session.messages.append({"role": "user", "content": req.message})

    # stream LLM response
    buffer = LiveStream()
    hook = ContextHook(buffer)
    
    result = Runner.run_streamed(
        starting_agent=triage_agent,
        input=session.messages,
        context=hook
    )
    async for ev in result.stream_events():
        if ev.type == "raw_response_event" and isinstance(ev.data, ResponseTextDeltaEvent):
            buffer.write(ev.data.delta)
    buffer.finish()

    response = "".join(buffer.stream())
    session.messages.append({"role": "assistant", "content": response})

    # Save messages asynchronously
    asyncio.create_task(
        asyncio.to_thread(
            save_messages,
            session.messages,
            folder=f"{settings.s3_folder}/{session.username}/logs",
            filename=f"{session_id}.json",
        )
    )
    return {"response": response}

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid session")

    user_msg = {"role": "user", "content": req.message}
    session.messages.append(user_msg)

    buffer = LiveStream()
    hook = ContextHook(buffer)

    result = Runner.run_streamed(starting_agent=triage_agent, input=session.messages, context=hook)

    async def event_stream():
        async for ev in result.stream_events():
            if ev.type == "raw_response_event" and isinstance(ev.data, ResponseTextDeltaEvent):
                buffer.write(ev.data.delta)
                chunk = ev.data.delta
                buffer.write(chunk)
                yield f"data: {json.dumps({'type': 'text', 'data': chunk})}\n\n"
        buffer.finish()

        items = list(buffer.stream())
        session.messages = result.to_input_list()

        save_messages(
            session.messages,
            folder=f"{settings.s3_folder}/{session.username}/logs",
            filename=f"{req.session_id}.json",
        )

        for item in items:
            if isinstance(item, dict):
                yield f"data: {json.dumps(item)}\n\n"

        yield "event: done\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

# ───── 3. Retrieve a session ───────────────────────────────────
@app.get("/sessions/{session_id}", response_model=Session)
async def get_session(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Invalid session")
    return session

# ───── 4. Health check ─────────────────────────────────────────
@app.get("/healthz")
async def health_check():
    return {"status": "ok"}

def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "9000"))
    uvicorn.run("spec.api.server:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()