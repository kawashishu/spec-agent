import base64
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
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
        output: NotebookCellOutput = notebook.exec(python_code)
        for var in output.vars:
            wrapper.context.buffer.write(var)        
            if isinstance(var, pd.DataFrame):
                wrapper.context.buffer.write({"type": "dataframe", "data": var.to_json(orient="split")})
            elif isinstance(var, go.Figure):
                wrapper.context.buffer.write({"type": "plotly", "data": var.to_json()})
            elif isinstance(var, plt.Figure):
                buf = BytesIO()
                var.savefig(buf, format="png")
                encoded = base64.b64encode(buf.getvalue()).decode()
                wrapper.context.buffer.write({"type": "matplotlib", "data": encoded})
            else:
                wrapper.context.buffer.write(var)    
                
        return output.console    
    
    except Exception as e:
        logger.error(f"Error executing Python code: {e}")
        return f"Error executing Python code: {e}"