import time

import chainlit as cl
import pandas as pd
from agents import RunContextWrapper, function_tool

from spec.cache import notebook
from spec.config import logger
from spec.models import AgentName, UIMessage
from spec.utils.notebook import NotebookCellOutput


@function_tool  
async def python_code_execution(wrapper: RunContextWrapper[UIMessage], python_code: str):
    """
    This function is used to execute Python code in a stateful Jupyter notebook environment. python will respond with the output of the execution. Internet access for this session is disabled. Do not make external web requests or API calls as they will fail.

    Args:
        python_code (str): The Python code to execute.

    Returns:
        str: The result of the Python code execution.
    """
    try:
        start_time = time.time()
        logger.info(f"TOOL: python_code_execution: \n{python_code}")
        
        output: NotebookCellOutput = notebook.exec(python_code)
        for var in output.vars:
            if isinstance(var, pd.DataFrame):
                e = cl.Dataframe(data=var, name="BOM", display="inline")
                wrapper.context.msg.elements.append(e)
        
        await wrapper.context.msg.send()
        
        duration = time.time() - start_time
        logger.info(f"Time to execute Python code: {duration:.2f}s")
        logger.info(f"Console: {output.console}")
        return output.console    
    
    except Exception as e:
        logger.error(f"Error executing Python code: {e}")
        return f"Error executing Python code: {e}"