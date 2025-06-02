import asyncio
import time
from typing import List, Tuple

import pandas as pd
from agents import function_tool

from cache import *
from printer import AsyncPrinter, printer
from prompt import RELEVANCE_CONTENT_TEMPLATE, SPECBOOK_RELEVANCE_PROMPT
from schema import AgentName, Specbook, SpecbookRelevanceContent
from settings.constraints import *
from settings.log import logger
from utils.llm import acompletion_with_backoff
from utils.notebook import NotebookCellOutput
from utils.utils import num_tokens_from_text


# Start loading message task
async def print_loading_messages():
    idx = 0
    while True:
        await printer.write(LOADING_MESSAGES[idx], sender=AgentName.SPECBOOK_AGENT.value)
        idx = (idx + 1) % len(LOADING_MESSAGES)
        await asyncio.sleep(8)
    
@function_tool
async def get_relevant_specbook_content_by_query_partial_context(query: str):
    """
    Retrieves specbook contents relevant to the given query and formats them in XML.

    Args:
        query (str): The query to search for in specbooks.

    Returns:
        str: XML formatted string containing relevant specbook contents, with each specbook wrapped in <Specbook> tags including specbook number and filename.
    """
    logger.info(f"TOOL: get_specbook_content_by_query({query})")

    specbook_numbers = list(cache["specbooks"].keys())
    specbooks = cache["specbooks"]

    async def _process_one(spec_no: str) -> Tuple[SpecbookRelevanceContent, str]:      
        content = specbooks[spec_no].content
        try:
            async with SEM:
                async with asyncio.timeout(TIMEOUT_PER_SPECBOOK):
                    completion = await acompletion_with_backoff(
                        model="gpt-4o-mini",
                        input=[
                            {"role": "system", "content": SPECBOOK_RELEVANCE_PROMPT.format(query=query)}, 
                            {"role": "user", "content": content}
                        ],
                        text_format=SpecbookRelevanceContent
                    )
                    parsed = completion.output_parsed
        except Exception as e:
            # Return IRRELEVANT if error
            return SpecbookRelevanceContent(reasoning="LIMIT TOKEN / TIMEOUT", relevance_content="", is_relevant=False), spec_no

        return parsed, spec_no

    # Create and start loading message task
    loading_task = asyncio.create_task(print_loading_messages())

    # Run the main processing with timeout
    snippets = await asyncio.gather(*(_process_one(n) for n in specbook_numbers))

    # Cancel loading message task when the main processing is done or timeout
    await printer.write("\n\n---\n\n", sender=AgentName.SPECBOOK_AGENT.value)
    loading_task.cancel()

    # Sort snippets by relevance level in descending order
    sorted_snippets = [(parsed, spec_no) for parsed, spec_no in snippets if parsed.is_relevant]
    
    MAX_RELEVANCE_TOKENS = 180000
    infor, count = "", 0
    for parsed, spec_no in sorted_snippets:
        spec: Specbook = specbooks[spec_no]
        relevance_content = parsed.relevance_content
        if num_tokens_from_text(infor + relevance_content) < MAX_RELEVANCE_TOKENS:
            # logger.info(f"[RELEVANCE] - Specbook: {spec_no}")
            infor += RELEVANCE_CONTENT_TEMPLATE.format(num=spec.specbook_number, content=relevance_content)
            count += 1
        else:
            break

    logger.info(f"Count: {count} / {len(specbooks)}, TOKENS: {num_tokens_from_text(infor)}")
    logger.info(f"RELEVANCE CONTENT: {infor}")

    return infor, sorted_snippets

@function_tool
def get_specbook_content_by_specbook_numbers(specbook_numbers: List[str]):
    """
    Retrieves specbook contents by list of specbook numbers and formats them in XML.

    Args:
        specbook_numbers (List[str]): The list of specbook numbers to search for.

    Returns:
        str: XML formatted string containing the specbook contents of the list of specbook numbers.
    """
    specbooks: List[Specbook] = [cache["specbooks"].get(specbook_number, Specbook(specbook_number=specbook_number, content="Specbook number not found")) for specbook_number in specbook_numbers]
    return "\n".join([specbook.content for specbook in specbooks])

@function_tool
async def get_specbook_numbers_table():
    """
    Retrieves the dataframe of specbook numbers available.
    """
    df = pd.DataFrame(list(cache["specbooks"].keys()), columns=["specbook_number"])
    await printer.write(df, sender=AgentName.SPECBOOK_AGENT.value)
    return df

@function_tool
async def python_code_execution(python_code: str):
    """
    This function is used to execute Python code in a stateful Jupyter notebook environment. python will respond with the output of the execution. Internet access for this session is disabled. Do not make external web requests or API calls as they will fail.

    Args:
        python_code (str): The Python code to execute.

    Returns:
        str: The result of the Python code execution.
    """
    start_time = time.time()
    logger.info(f"TOOL: python_code_execution: \n{python_code}")
    
    output: NotebookCellOutput = notebook.exec(python_code)
    for var in output.vars:
        await printer.write(var, sender=AgentName.BOM_AGENT.value)
    
    duration = time.time() - start_time
    logger.info(f"Time to execute Python code: {duration:.2f}s")
    logger.info(f"Console: {output.console}")
    return output.console    
