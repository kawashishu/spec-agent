# agent_streamlit_buffer_stream.py
import asyncio
import queue
import threading
from dataclasses import dataclass
from typing import Any, Iterator

import pandas as pd
import streamlit as st
from agents import (Agent, RunContextWrapper, RunHooks, Runner, Tool, Usage,
                    function_tool)
from openai.types.responses import ResponseTextDeltaEvent
from pydantic import BaseModel

# ──────── TOOL & AGENT ──────────────────────────────────────────


# ──────── STREAM BUFFER (thread-safe) ───────────────────────────
class LiveStream:
    def __init__(self):
        self.q: queue.Queue[Any] = queue.Queue()

    def push(self, chunk: Any):
        self.q.put(chunk)

    def finish(self):
        self.q.put(None)

    def stream(self) -> Iterator[Any]:
        while True:
            item = self.q.get()
            if item is None:
                break
            yield item

@dataclass    
class ContextHook:
    buffer: LiveStream


@function_tool
def get_data(wrapper: RunContextWrapper[ContextHook]) -> pd.DataFrame:          # không tham số
    """Get data from the dataframe."""
    df = pd.DataFrame(
        {"name": ["John", "Jane", "Jim", "Jill"],
         "age": [25, 30, 35, 40],
         "city": ["NY", "LA", "CHI", "HOU"]}
    )
    wrapper.context.buffer.push(df)
    return df

agent = Agent(
    name="Agent",
    instructions="You are a helpful assistant that can get data from a pandas dataframe.",
    tools=[get_data],
)

# ──────── STREAMLIT APP ─────────────────────────────────────────
st.title("💬 Agent SDK × Streamlit (run_streamed)")

if st.button("🎲 Chạy"):
    with st.chat_message("user"):
        st.write("Hãy lấy dữ liệu")

    with st.chat_message("assistant"):
        buffer = LiveStream()
        context_hook = ContextHook(buffer)

        # chạy Runner.run_streamed trong thread
        def run_agent_stream():
            async def _runner():
                result = Runner.run_streamed(
                    agent,
                    input="Get the data",
                    context=context_hook
                )
                # lấy delta text
                async for ev in result.stream_events():
                    if ev.type == "raw_response_event" and isinstance(ev.data, ResponseTextDeltaEvent):
                        buffer.push(ev.data.delta)
                    elif ev.type == "run_item_stream_event":
                        if ev.item.type == "tool_call_item":
                            print("-- Tool was called")
                buffer.finish()
            asyncio.run(_runner())

        threading.Thread(target=run_agent_stream, daemon=True).start()

        # Streamlit hiển thị liên tục
        response = st.write_stream(buffer.stream())
        print(response)
