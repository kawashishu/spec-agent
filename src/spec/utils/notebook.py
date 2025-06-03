
import asyncio
import io
import re
import sys
from typing import Any

from pydantic import BaseModel


class NotebookCellOutput:
    def __init__(self, console: str, vars: Any):
        if isinstance(vars, tuple):
            self.vars = vars
        else:
            self.vars = (vars,)
        self.console = console

class Cell:
    def __init__(self, code: str, output: NotebookCellOutput):
        self.code = code
        self.output = output

class Notebook:
    def __init__(self, env=None):
        if env is None:
            env = {"__builtins__": __builtins__}
        
        self.env = env
        self.cells = []

    def exec(self, code: str) -> NotebookCellOutput:
        old_stdout, buf = sys.stdout, io.StringIO()
        sys.stdout = buf

        vars_ = None
        orig_print = self.env.get("print", print)

        def _print(*args, **kwargs):
            orig_print(*map(self._resolve, args), **kwargs)
        self.env["print"] = _print

        try:
            lines = code.strip().splitlines()
            if lines:
                *body, last = lines
                body_code = "\n".join(body)
                if body_code:
                    exec(body_code, self.env)

                try:
                    vars_ = self._resolve(eval(last, self.env))
                except Exception:
                    exec(last, self.env)
                    vars_ = None

                if vars_ is not None:
                    _print(vars_)
            else:
                exec(code, self.env)

        except Exception as e:
            _print(f"Error: {e}")

        finally:
            sys.stdout = old_stdout
            self.env["print"] = orig_print

        console = buf.getvalue()
        output = NotebookCellOutput(console=console, vars=vars_)
        self.cells.append(Cell(code=code, output=output))
        return output
    
    def vars(self, print_all=True):
        vals = {
            k: v for k, v in self.env.items() if not (k.startswith("__") and k.endswith("__"))
        }
        if print_all:
            for k, v in vals.items():
                print(f"{k} = {v}")
        return vals

    def parse_code(self, text: str):
        pattern = r'```python(.*?)(?:```|``|`|$)'
        blocks = re.findall(pattern, text, flags=re.DOTALL)
        return [b.strip() for b in blocks]

    def _resolve(self, obj):
        """Return *obj* if it isn't a coroutine; otherwise run it to completion."""
        if asyncio.iscoroutine(obj):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:                  # no loop yet → make one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # nest_asyncio has already patched the loop, so re-entrancy is OK
            return loop.run_until_complete(obj)

        # Lists / tuples of possible coroutines (e.g. print(*objs))
        if isinstance(obj, (list, tuple)):
            return type(obj)(self._resolve(v) for v in obj)

        return obj

