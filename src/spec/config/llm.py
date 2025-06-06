from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

load_dotenv()

from agents import (set_default_openai_api, set_default_openai_client,
                    set_tracing_disabled)
from openai import AsyncAzureOpenAI, AzureOpenAI

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