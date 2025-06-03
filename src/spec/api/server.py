# fastapi_app.py
import asyncio
from datetime import datetime

import pytz
from agents import Runner
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from openai.types.responses import ResponseTextDeltaEvent

from spec.agents import triage_agent
from spec.api.context import current_sid, sessions
from spec.api.printer import printer
from spec.data.cache import cache
from spec.models import ChatRequest, EndStream, NewChatRequest, Session
from spec.settings.constraints import *
from spec.settings.llm import *
from spec.settings.log import logger
from spec.utils.utils import save_messages

# ---------------------------------------------------------------------------

app = FastAPI(
    title="Streaming Agent API",
    description="Runs an Agent, returns tokens as they are generated (SSE).",
    version="1.0.0",
)

@app.middleware("http")
async def sid_middleware(req: Request, call_next):
    sid = (await req.json()).get("session_id") if req.url.path == "/chat" else None
    token = current_sid.set(sid)
    try:
        return await call_next(req)
    finally:
        current_sid.reset(token)

async def _run_and_stream():
    sid = current_sid.get()
    ctx = sessions.ctx[sid]
    sender = triage_agent.name
    try:
        run = Runner.run_streamed(triage_agent, ctx)
        async for ev in run.stream_events():
            if ev.type == "raw_response_event" and isinstance(ev.data, ResponseTextDeltaEvent):
                await printer.write(ev.data.delta, sender=sender)
            elif ev.type == "agent_updated_stream_event":
                sender = ev.new_agent.name
        
        # Update context
        sessions.ctx[sid] = run.to_input_list()
        
        # Save context to S3
        await asyncio.to_thread(
            save_messages,
            sessions.ctx[sid],
            filename=f"{sessions.init_time[sid]}.json",
            folder=f"PDF_search/logs/{sessions.user[sid]}",
            s3=cache["s3"],
        )
    except Exception as e:
        logger.error(f"runner err {e}")
        await printer.write("ERROR", sender="system")
    finally:
        await printer.write(EndStream(status=False))
        await printer.close()
    
@app.post("/chat")
async def chat(req: ChatRequest):
    sid = req.session_id
    lock = sessions.get_lock()
    async with lock:
        # Init session
        if sid not in sessions.ctx:
            init_time = datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).strftime("%Y%m%d_%H%M%S")
            sessions.init_time[sid] = init_time
            sessions.user[sid] = req.username

        sessions.ctx[sid].append({"role": "user", "content": req.prompt})

    asyncio.create_task(_run_and_stream())

    return StreamingResponse(printer.stream(), media_type="application/x-ndjson")

@app.post("/new_chat")
async def new_chat(req: NewChatRequest):
    sessions.drop(req.session_id)
    return {"status": "ok"}

@app.exception_handler(Exception)
async def any_err(_, exc: Exception):
    logger.error(f"Unhandled: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal error"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("spec.api.server:app", host="0.0.0.0", port=9000, reload=True)