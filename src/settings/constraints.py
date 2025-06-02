import asyncio
from pathlib import Path

MAX_TOKEN_LIMIT = 950000
PORT = 9001
URL = f"http://localhost:{PORT}"

PDF_URL = f"{URL}/pdf"
THREE_D_SINGLE_URL = f"{URL}/3d"
THREE_D_INDEX_URL = f"{URL}/3d/index"
THREE_D_COMPARE_URL = f"{URL}/3d/compare"
SLEEP = 0.03

AUTHEN_FILE = Path(__file__).parent.parent.parent / 'authen.yaml'

ERROR_MESSAGE = "Something went wrong. The context limit may have been reached. Please try your question again in a new chat or contact support via Teams/Email: phuongnh52@vinit.vn"

LOADING_MESSAGES = [
    "Gathering relevant information...\n\n",
    "Reviewing key data...\n\n",
    "Analyzing detailed findings...\n\n",
    "Cross-checking facts and insights...\n\n",
    "Finalizing your comprehensive report...\n\n",
    "Summarizing research results...\n\n"
]
SEM = asyncio.Semaphore(5000) 

TIMEOUT_PER_SPECBOOK = 60

TIMEOUT_MSG = (
    f"Timeout: The operation took too long and was stopped after {TIMEOUT_PER_SPECBOOK} seconds.\n"
    "This may be because the context is too large for the model to process in a single session.\n"
    "Please start a new chat session to continue your request."
)