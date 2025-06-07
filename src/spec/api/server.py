from typing import List
import asyncio

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents import Runner, TResponseInputItem
from spec.agents import triage_agent
from spec.models import ContextHook, LiveStream

app = FastAPI()

class ChatRequest(BaseModel):
    messages: List[TResponseInputItem]

@app.post("/chat")
async def chat(req: ChatRequest):
    buffer = LiveStream()
    hook = ContextHook(buffer)
    result = Runner.run_streamed(triage_agent, input=req.messages, context=hook)

    async def consume_events():
        async for ev in result.stream_events():
            if ev.type == "raw_response_event" and hasattr(ev.data, "delta"):
                hook.write(ev.data.delta)
        hook.finish()

    task = asyncio.create_task(consume_events())

    async def event_stream():
        async for chunk in buffer.stream():
            yield f"data: {chunk}\n\n"
        await task
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
