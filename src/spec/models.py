
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

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

class SingletonMeta(type):
    """A Singleton metaclass."""

    _instances: Dict[Any, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:   
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Buffer:
    def __init__(self):
        pass

    async def write(self, obj: Any):
        raise NotImplementedError

    async def close(self):
        raise NotImplementedError

    async def stream(self):
        raise NotImplementedError

@dataclass    
class ContextHook:
    buffer: Buffer