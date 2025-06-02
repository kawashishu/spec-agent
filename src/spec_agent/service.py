# services/runner.py
import asyncio

from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent
from spec_agent.api.printer import AsyncPrinter
from spec_agent.models import EndStream
from spec_agent.settings.log import logger


async def run_agent_streamed(context, agent: Agent, printer: AsyncPrinter | None = None):
    sender = agent.name
    try:
        run = Runner.run_streamed(agent, context)
        async for ev in run.stream_events():
            if ev.type == "raw_response_event" and isinstance(ev.data, ResponseTextDeltaEvent):
                if printer:
                    await printer.write(ev.data.delta, sender=sender)
                print(ev.data.delta, end="", flush=True)
            elif ev.type == "agent_updated_stream_event":
                sender = ev.new_agent.name
        return run.to_input_list()

    except Exception as exc:
        logger.error(f"service.run_agent_streamed: {exc}")
        if printer:
            await printer.write("ERROR", sender="system")
        return context    # giữ nguyên nếu fail

    finally:
        if printer:
            await printer.write(EndStream(status=False))
            await printer.close()
