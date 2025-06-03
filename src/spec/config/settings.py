import asyncio
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    max_token_limit: int = 950000
    sleep: float = 0.03
    authen_file: Path = Path(__file__).parent.parent.parent / 'authen.yaml'
    error_message: str = "Something went wrong. The context limit may have been reached. Please try your question again in a new chat or contact support via Teams/Email: phuongnh52@vinit.tech"
    loading_messages: list[str] = [
        "Gathering relevant information...\n\n",
        "Reviewing key data...\n\n",
        "Analyzing detailed findings...\n\n",
        "Cross-checking facts and insights...\n\n",
        "Finalizing your comprehensive report...\n\n",
        "Summarizing research results...\n\n"
    ]
    semaphore: asyncio.Semaphore = asyncio.Semaphore(5000)
    timeout_per_specbook: int = 60
    timeout_msg: str = (
        f"Timeout: The operation took too long and was stopped after {timeout_per_specbook} seconds.\n"
        "This may be because the context is too large for the model to process in a single session.\n"
        "Please start a new chat session to continue your request."
    )
    
settings = Settings()
