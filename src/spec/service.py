
import chainlit as cl
from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent

from spec.config import logger
from spec.models import UIMessage


async def run_agent_streamed(messages, agent: Agent, msg: cl.Message):
    ui_message = UIMessage(msg=msg)
    try:
        run = Runner.run_streamed(agent, input=messages, context=ui_message)
        async for ev in run.stream_events():
            if ev.type == "raw_response_event" and isinstance(ev.data, ResponseTextDeltaEvent):
                await msg.stream_token(ev.data.delta)
            elif ev.type == "agent_updated_stream_event":
                sender = ev.new_agent.name
        return run.to_input_list()

    except Exception as exc:
        logger.error(f"service.run_agent_streamed: {exc}")
        return messages