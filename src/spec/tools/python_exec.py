import time

import chainlit as cl
import pandas as pd
from agents import RunContextWrapper, function_tool

from spec.cache import notebook
from spec.config import logger
from spec.models import ContextHook
from spec.utils.notebook import NotebookCellOutput


@function_tool  
async def code_interpreter(wrapper: RunContextWrapper[ContextHook], python_code: str):
    """
    This function is used to execute Python code in a stateful Jupyter notebook environment. python will respond with the output of the execution. Internet access for this session is disabled. Do not make external web requests or API calls as they will fail.

    Args:
        python_code (str): The Python code to execute.

    Returns:
        str: The result of the Python code execution.
    """
    try:
        logger.info(f"TOOL: code_interpreter: \n{python_code}")
        
        output: NotebookCellOutput = notebook.exec(python_code)
        for var in output.vars:
            wrapper.context.buffer.write(var)        
                
        return output.console    
    
    except Exception as e:
        logger.error(f"Error executing Python code: {e}")
        return f"Error executing Python code: {e}"