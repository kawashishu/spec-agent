import chainlit as cl

from spec.agents import triage_agent
from spec.service import run_agent_streamed


@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Q&A about a specific Specbook",
            message="Please summarize the specbook information VFDSXNBEX0013",
            icon="/public/idea.svg",
            ),

        cl.Starter(
            label="Q&A about all Specbooks (15-30s)",
            message="Tell me all the chassis group information that is in all the specbooks",
            icon="/public/learn.svg",
            ),
        cl.Starter(
            label="Query BOM, Part Master data table",
            message="Find components belonging to VF8",
            icon="/public/terminal.svg",
            ),
        cl.Starter(
            label="Draw chart, graph",
            message="Draw a graph showing the number of parent Parts that have more than 6 direct child parts.",
            icon="/public/write.svg",
            )
        ]

@cl.on_chat_start
async def on_start():
    cl.user_session.set("context", [])

@cl.on_message
async def on_message(message: cl.Message):
    context: list = cl.user_session.get("context")
    context.append({"role": "user", "content": message.content})
    
    msg = cl.Message(content="", elements=[])
    await msg.send()

    context = await run_agent_streamed(context, triage_agent, msg)
    
    await msg.send()
    
    cl.user_session.set("context", context)