from enum import Enum
from typing import Any, Dict, List, Optional

from agents import TResponseInputItem
from pydantic import BaseModel, Field


class AgentName(Enum):
    BOM_AGENT = "BOM Agent"
    SPECBOOK_AGENT = "Specbook Agent"
    TRIAGE_AGENT = "Triage Agent"
    
    def __str__(self):
        return self.value

class SpecbookRelevanceContent(BaseModel):
    reasoning: str = Field(
        ...,
        description=(
            "A clear and detailed justification explaining the exact data types required by the provided query, "
            "the precise locations (section name, title, data table, page number, etc.) of these data types in the specbook, "
            "and explicit analysis or inference, including reasoning about abbreviations or acronyms when necessary."
        )
    )
    relevance_content: str = Field(
        ...,
        description=(
            "The explicitly extracted comprehensive content from the specbook document that accurately and completely "
            "addresses the specific data requirements identified in the query."
        )
    )
    is_relevant: bool = Field(
        ...,
        description=(
            "A boolean classification explicitly stating whether the provided specbook document contains exact, complete, "
            "and directly relevant information fully satisfying the query (True), or lacks the necessary information (False)."
        )
    )

class Specbook(BaseModel):
    specbook_number: str
    content: str

class Session(BaseModel):
    init_time: str
    context: List[TResponseInputItem]

class ChatRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None
    username: Optional[str] = None


class NewChatRequest(BaseModel):
    session_id: str         


class EndStream(BaseModel):
    status: bool = True
    
class SingletonMeta(type):
    """A Singleton metaclass."""

    _instances: Dict[Any, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:   
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
