import asyncio

from agents import Agent, ItemHelpers, Runner, trace
from settings.llm import *

"""
This example shows the parallelization pattern. We run the agent three times in parallel, and pick
the best result.
"""

english_agent = Agent(
    name="english_agent",
    instructions="You translate the user's message to english",
)

english_picker = Agent(
    name="english_picker",
    instructions="You pick the best english translation from the given options.",
)


async def main():
    
    msg = input("Hi! Enter a message, and we'll translate it to english.\n\n")

    res_1, res_2, res_3 = await asyncio.gather(
        Runner.run(
            english_agent,
            msg,
        ),
        Runner.run(
            english_agent,
            msg,
        ),
        Runner.run(
            english_agent,
            msg,
        ),
    )

    outputs = [
        ItemHelpers.text_message_outputs(res_1.new_items),
        ItemHelpers.text_message_outputs(res_2.new_items),
        ItemHelpers.text_message_outputs(res_3.new_items),
    ]

    translations = "\n\n".join(outputs)
    # print(f"\n\nTranslations:\n\n{translations}")

    best_translation = await Runner.run(
        english_picker,
        f"Input: {msg}\n\nTranslations:\n{translations}",
    )

    print("\n\n-----")

    print(f"Best translation: {best_translation.final_output}")


if __name__ == "__main__":
    asyncio.run(main())