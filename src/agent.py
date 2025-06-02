from agents import Agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from prompt import BOM_AGENT_PROMPT, SPECBOOK_AGENT_PROMPT, TRIAGE_AGENT_PROMPT
from schema import AgentName
from tool import *

specbook_agent = Agent(
    name=AgentName.SPECBOOK_AGENT.value,      
    instructions=f"{RECOMMENDED_PROMPT_PREFIX}\n---\n{SPECBOOK_AGENT_PROMPT}",
    handoff_description=f"A {AgentName.SPECBOOK_AGENT.value} capable of retrieving specbook contents and providing detailed, accurate responses",
    tools=[
        get_relevant_specbook_content_by_query_partial_context,
        get_specbook_content_by_specbook_numbers,
        get_specbook_numbers_table
    ],
    model="gpt-4.1"
)

bom_agent = Agent(
    name=AgentName.BOM_AGENT.value,
    instructions=f"{RECOMMENDED_PROMPT_PREFIX}\n---\n{BOM_AGENT_PROMPT}",
    handoff_description=f"A {AgentName.BOM_AGENT.value} capable of writing Python code (pandas, matplotlib, etc...) to analyze BOM data (available in the context), visualize charts and provide detailed, accurate responses",
    tools=[
        python_code_execution
    ],
    model="gpt-4.1"
)

triage_agent = Agent(
    name=AgentName.TRIAGE_AGENT.value,
    instructions=f"{RECOMMENDED_PROMPT_PREFIX}\n---\n{TRIAGE_AGENT_PROMPT}",
    handoffs=[bom_agent, specbook_agent],
    model="gpt-4.1"
)
