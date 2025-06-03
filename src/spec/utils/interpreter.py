from __future__ import annotations

import ast
import base64
import io
import sys
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Tuple

from .guardrail import detect_suspicious_code

# Default list of allowed libraries. Only top level module names should be used.
DEFAULT_ALLOWED_LIBRARIES = {
    "math",
    "statistics",
    "numpy",
    "pandas",
    "matplotlib",
    "plotly",
}

@dataclass
class InterpreterOutput:
    """Returned by :class:`CodeInterpreter.exec`."""

    console: str
    vars: Tuple[Any, ...]
    charts: List[str] = field(default_factory=list)

class CodeInterpreter:
    """Execute Python snippets in a restricted environment."""

    def __init__(self, allowed_modules: Iterable[str] | None = None, env: dict[str, Any] | None = None):
        self.allowed_modules = set(allowed_modules or DEFAULT_ALLOWED_LIBRARIES)
        self.env = env or {"__builtins__": __builtins__}
        self.cells: List[Tuple[str, InterpreterOutput]] = []

    def exec(self, code: str) -> InterpreterOutput:
        """Execute *code* and return console output, figures and last expression."""
        findings = detect_suspicious_code(code)
        if findings:
            raise ValueError("Suspicious code detected: " + "; ".join(findings))

        self._validate_imports(code)
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        result = None
        try:
            lines = [ln for ln in code.strip().splitlines() if ln.strip()]
            if lines:
                *body, last = lines
                if body:
                    exec("\n".join(body), self.env)
                try:
                    result = eval(last, self.env)
                except Exception:
                    exec(last, self.env)
                    result = None
                if result is not None:
                    print(result)
            else:
                exec(code, self.env)
        finally:
            sys.stdout = old_stdout

        charts = self._extract_charts()
        out = InterpreterOutput(console=buf.getvalue(), vars=(result,), charts=charts)
        self.cells.append((code, out))
        return out

    def _validate_imports(self, code: str) -> None:
        """Raise ImportError if *code* imports modules outside the whitelist."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Let exec handle syntax errors
            return
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root not in self.allowed_modules:
                        raise ImportError(f"Import of '{alias.name}' is not allowed")
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                root = node.module.split(".")[0]
                if root not in self.allowed_modules:
                    raise ImportError(f"Import of '{node.module}' is not allowed")

    def _extract_charts(self) -> List[str]:
        """Return list of base64 encoded figures from matplotlib/plotly."""
        charts: List[str] = []
        if "matplotlib.pyplot" in sys.modules:
            import matplotlib.pyplot as plt
            for num in plt.get_fignums():
                fig = plt.figure(num)
                b = io.BytesIO()
                fig.savefig(b, format="png")
                b.seek(0)
                charts.append(base64.b64encode(b.read()).decode())
                plt.close(fig)
        if "plotly" in sys.modules:
            try:
                import plotly.graph_objects as go
            except Exception:
                return charts
            for val in self.env.values():
                if isinstance(val, go.Figure):
                    charts.append(val.to_json())
        return charts
