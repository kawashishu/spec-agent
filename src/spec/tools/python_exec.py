import time

from agents import function_tool

from spec.api.printer import printer
from spec.config.logging import logger
from spec.data.cache import notebook
from spec.models import AgentName
from spec.utils.notebook import NotebookCellOutput


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
