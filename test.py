from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

load_dotenv()

import logging
import sys

from agents import (set_default_openai_api, set_default_openai_client,
                    set_tracing_disabled)
from openai import AsyncAzureOpenAI, AzureOpenAI

# ANSI escape codes
RESET = "\033[0m"
COLOR_INFO = "\033[32m"     # Green
COLOR_WARNING = "\033[33m"  # Yellow
COLOR_ERROR = "\033[31m"    # Red

class LevelColorFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname

        if record.levelno == logging.INFO:
            color = COLOR_INFO
        elif record.levelno == logging.WARNING:
            color = COLOR_WARNING
        elif record.levelno == logging.ERROR:
            color = COLOR_ERROR
        else:
            color = RESET

        # Chỉ tô màu levelname
        record.levelname = f"{color}{levelname}{RESET}"

        return super().format(record)

# Setup logger
logger = logging.getLogger("spec")
logger.setLevel(logging.ERROR)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(LevelColorFormatter("%(levelname)s - %(message)s"))
logger.addHandler(console_handler)


token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)

client = AzureOpenAI(
    azure_ad_token_provider=token_provider,
    azure_endpoint="https://aoai-eastus2-0001.openai.azure.com/",
    api_version="2025-03-01-preview",
)

async_client = AsyncAzureOpenAI(
    azure_ad_token_provider=token_provider,
    azure_endpoint="https://aoai-eastus2-0001.openai.azure.com/",
    api_version="2025-03-01-preview",
)

set_default_openai_client(async_client, use_for_tracing=False)
set_tracing_disabled(disabled=True)
set_default_openai_api("chat_completions")


response = client.responses.create(
    model="gpt-4.1",
    input="Write a one-sentence bedtime story about a unicorn."
)

print(response.output_text)