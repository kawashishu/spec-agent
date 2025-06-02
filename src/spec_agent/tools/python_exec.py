import time

from agents import function_tool

from spec_agent.api.printer import printer
from spec_agent.models import AgentName
from spec_agent.settings.log import logger
from spec_agent.utils.notebook import NotebookCellOutput

from spec_agent.data.cache import notebook


@function_tool
async def python_code_execution(python_code: str):
    """Execute Python code in the shared notebook environment."""
    start_time = time.time()
    logger.info(f"TOOL: python_code_execution: \n{python_code}")

    output: NotebookCellOutput = notebook.exec(python_code)
    for var in output.vars:
        await printer.write(var, sender=AgentName.BOM_AGENT.value)

    duration = time.time() - start_time
    logger.info(f"Time to execute Python code: {duration:.2f}s")
    logger.info(f"Console: {output.console}")
    return output.console
