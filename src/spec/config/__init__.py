from dotenv import load_dotenv

load_dotenv()

from .llm import async_client, client
from .logging import logger
from .settings import settings

__all__ = [
    "settings",
    "logger",
    "client",
    "async_client",
]

# Aliases for backward compatibility
llm_client = client
async_llm_client = async_client
