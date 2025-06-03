import chainlit as cl

from spec.agents import triage_agent
from spec.service import run_agent_streamed


@cl.on_chat_start
async def on_start():
    cl.user_session.set("context", [])

@cl.on_message
async def on_message(message: cl.Message):
    context = cl.user_session.get("context")
    context.append({"role": "user", "content": message.content})
    
    msg = cl.Message(content="", elements=[])
    await msg.send()

    context = await run_agent_streamed(context, triage_agent, msg)
    
    await msg.send()
    
    cl.user_session.set("context", context)