from __future__ import annotations

import asyncio
import os
from typing import Dict
from uuid import uuid4

from agents import Runner
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from openai.types.responses import ResponseTextDeltaEvent

from spec.agents import triage_agent
from spec.api.schema import (ChatRequest, CreateSessionRequest,
                             CreateSessionResponse, SerializedStreamBuffer,
                             Session)
from spec.config import settings
from spec.models import ContextHook
from spec.utils.utils import save_messages

app = FastAPI()
_sessions: Dict[str, Session] = {}


# ───── 1. New chat ─────────────────────────────────────────────
@app.post("/sessions", response_model=CreateSessionResponse, status_code=201)
async def create_session(req: CreateSessionRequest):
    session_id = str(uuid4())
    _sessions[session_id] = Session(id=session_id, username=req.username)
    return {"session_id": session_id}

async def run_chat_stream(session: Session, req: ChatRequest, buffer: SerializedStreamBuffer, hook: ContextHook):
    try:
        result = Runner.run_streamed(
            starting_agent=triage_agent,
            input=session.messages + [{"role": "user", "content": req.message}],
            context=hook,
        )
        
        async for ev in result.stream_events():
            if ev.type == "raw_response_event" and isinstance(ev.data, ResponseTextDeltaEvent):
                await buffer.write(ev.data.delta)
                
    finally:
        await buffer.close()

    session.messages = result.to_input_list()
    
    await asyncio.to_thread(
        save_messages,
        session.messages,
        folder=f"{settings.s3_folder}/{session.username}/logs",
        filename=f"{session.init_time}.json",
    )

@app.post("/chat/stream")
async def stream_messages(req: ChatRequest):
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid session")
 
    buffer = SerializedStreamBuffer()
    hook   = ContextHook(buffer)

    asyncio.create_task(run_chat_stream(session, req, buffer, hook))

    return StreamingResponse(buffer.stream(), media_type="application/x-ndjson")

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
    uvicorn.run(
        "spec.api.server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        debug=True,
        workers=1
    )


if __name__ == "__main__":
    main()