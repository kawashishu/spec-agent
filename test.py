from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AzureOpenAI

load_dotenv()

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)

client = AsyncAzureOpenAI(
    azure_ad_token_provider=token_provider,
    azure_endpoint="https://aoai-eastus2-0001.openai.azure.com/",
    api_version="2025-03-01-preview",
)

import tiktoken


def num_tokens_from_text(string: str, encoding_name: str = "o200k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

WORDS = (
    "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua ut enim ad minim "
    "veniam quis nostrud exercitation ullamco laboris nisi ut aliquip ex "
    "ea commodo consequat duis aute irure dolor in reprehenderit in "
    "voluptate velit esse cillum dolore eu fugiat nulla pariatur in"
)

# corpus = WORDS * 4200 # 252000 tokens --> OK
corpus = WORDS * 13000 # 264000 tokens --> LIMIT TOKEN

print(num_tokens_from_text(corpus))

import asyncio

from agents import (Agent, Runner, set_default_openai_api,
                    set_default_openai_client, set_tracing_disabled)
from openai.types.responses import ResponseTextDeltaEvent

# set_default_openai_api("chat_completions")
set_default_openai_client(client)
set_tracing_disabled(disabled=True)
set_default_openai_api("chat_completions")


async def main():
    agent = Agent(
        name="Joker",
        instructions="You are a helpful assistant.",
        model="gpt-4.1-nano",
    )

    result = Runner.run_streamed(agent, input="Translate to English: " + corpus)
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())