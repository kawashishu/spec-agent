import asyncio
from typing import List, Tuple

import pandas as pd
from agents import RunContextWrapper, function_tool

from spec.agents.prompts import (RELEVANCE_CONTENT_TEMPLATE,
                                 SPECBOOK_RELEVANCE_PROMPT)
from spec.cache import *
from spec.config import logger, settings
from spec.models import ContextHook, Specbook, SpecbookRelevanceContent
from spec.utils.llm import acompletion_with_backoff
from spec.utils.utils import num_tokens_from_text


@function_tool
async def get_relevant_specbook_content_by_query_partial_context(wrapper: RunContextWrapper[ContextHook],query: str):
    """
    Retrieves specbook contents relevant to the given query and formats them in XML.

    Args:
        query (str): The query to search for in specbooks.

    Returns:
        str: XML formatted string containing relevant specbook contents, with each specbook wrapped in <Specbook> tags including specbook number and filename.
    """
    logger.info(f"TOOL: get_specbook_content_by_query({query})")
    
    # Start loading message task
    async def print_loading_messages():
        # Separator
        wrapper.context.buffer.write("\n\n---\n\n")
        
        idx = 0
        ms = settings.loading_messages
        while True:
            wrapper.context.buffer.write(ms[idx])
            idx = (idx + 1) % len(ms)
            await asyncio.sleep(8)

    specbook_numbers = list(cache.specbooks.keys())
    specbooks = cache.specbooks

    async def _process_one(spec_no: str) -> Tuple[SpecbookRelevanceContent, str]:      
        content = specbooks[spec_no].content
        try:
            async with settings.semaphore:
                async with asyncio.timeout(settings.timeout_per_specbook):
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
    loading_task.cancel()
    wrapper.context.buffer.write("\n\n---\n\n")

    # Sort snippets by relevance level in descending order
    sorted_snippets = [(parsed, spec_no) for parsed, spec_no in snippets if parsed.is_relevant]
    
    MAX_RELEVANCE_TOKENS = 5000000
    infor, count = "", 0
    for parsed, spec_no in sorted_snippets:
        spec: Specbook = specbooks[spec_no]
        relevance_content = parsed.relevance_content
        if num_tokens_from_text(infor + relevance_content) < MAX_RELEVANCE_TOKENS:
            infor += RELEVANCE_CONTENT_TEMPLATE.format(num=spec.specbook_number, content=relevance_content)
            count += 1
        else:
            break

    logger.info(f"Count: {count} / {len(specbooks)}, TOKENS: {num_tokens_from_text(infor)}")

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
    specbooks: List[Specbook] = [cache.specbooks.get(specbook_number, Specbook(specbook_number=specbook_number, content="Specbook number not found")) for specbook_number in specbook_numbers]
    return "\n".join([specbook.content for specbook in specbooks])

@function_tool
async def get_specbook_numbers_table(wrapper: RunContextWrapper[ContextHook]):
    """
    Retrieves the dataframe of specbook numbers available.
    
    Returns:
        str: a Dataframe of specbook numbers
    """
    df = pd.DataFrame(list(cache.specbooks.keys()), columns=["specbook_number"])
    wrapper.context.buffer.write(df)
    return df