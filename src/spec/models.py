import queue
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterator

from pydantic import BaseModel, Field


class LiveStream:
    def __init__(self):
        self.q: queue.Queue[Any] = queue.Queue()

    def write(self, chunk: Any):
        self.q.put(chunk)

    def finish(self):
        self.q.put(None)

    def stream(self) -> Iterator[Any]:
        while True:
            item = self.q.get()
            if item is None:
                break
            yield item
            
@dataclass    
class ContextHook:
    buffer: LiveStream

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
