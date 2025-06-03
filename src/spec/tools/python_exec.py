import time

from agents import function_tool

from spec.api.printer import printer
from spec.config import logger
from spec.data.cache import notebook
from spec.models import AgentName
from spec.utils.notebook import NotebookCellOutput


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