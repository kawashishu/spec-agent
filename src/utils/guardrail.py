import ast
import re

SUSPICIOUS_BUILTINS = {
    "eval",
    "exec",
    "__import__",
    "compile",   # can be used similarly to exec
}

SUSPICIOUS_MODULES = {
    "os", "sys", "subprocess", "shutil", "ctypes", "pickle",
    "importlib", "socket", "requests", "paramiko", "ftplib",
    "urllib", "yaml", "marshal", "inspect"
}

SUSPICIOUS_ATTRIBUTES = {
    # os module
    ("os", "system"),
    ("os", "popen"),
    ("os", "spawnl"),
    ("os", "spawnle"),
    ("os", "spawnlp"),
    ("os", "spawnlpe"),
    ("os", "spawnv"),
    ("os", "spawnve"),
    ("os", "spawnvp"),
    ("os", "spawnvpe"),
    ("os", "fork"),
    ("os", "execv"),
    ("os", "execve"),
    ("os", "execvp"),
    ("os", "execvpe"),
    ("os", "remove"),
    ("os", "rmdir"),
    ("os", "setuid"),
    ("os", "setgid"),
    ("os", "chroot"),
    ("os", "chmod"),
    ("os", "chown"),

    # subprocess
    ("subprocess", "call"),
    ("subprocess", "run"),
    ("subprocess", "Popen"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),

    # shutil
    ("shutil", "rmtree"),
    ("shutil", "move"),
    ("shutil", "copy"),

    # builtins
    (None, "eval"),
    (None, "exec"),
    (None, "__import__"),
    (None, "compile"),
}

# For naive substring checks:
SUSPICIOUS_TEXT_PATTERNS = [
    r"os\.system",
    r"subprocess",
    r"eval\s*\(",
    r"exec\s*\(",
    r"paramiko",
    r"requests",
    r"pickle",
    r"ctypes",
    # Add more as desired...
]

class SecurityNodeVisitor(ast.NodeVisitor):
    """
    This AST visitor collects suspicious usages in the code.
    """
    def __init__(self):
        self.suspicious_findings = []

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in SUSPICIOUS_MODULES:
                self.suspicious_findings.append(
                    f"Importing suspicious module '{alias.name}' at line {node.lineno}"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module in SUSPICIOUS_MODULES:
            self.suspicious_findings.append(
                f"Importing from suspicious module '{node.module}' at line {node.lineno}"
            )
        self.generic_visit(node)

    def visit_Call(self, node):
        """
        Check calls like os.system(), subprocess.Popen(), eval(), etc.
        """
        # If it's a simple name call, e.g., eval(...)
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in SUSPICIOUS_BUILTINS:
                self.suspicious_findings.append(
                    f"Call to suspicious builtin '{func_name}' at line {node.lineno}"
                )

        # If it's an attribute call, e.g., os.system(...)
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            # Get the value part, which might be a Name node
            if isinstance(node.func.value, ast.Name):
                module_name = node.func.value.id
                if (module_name, attr_name) in SUSPICIOUS_ATTRIBUTES:
                    self.suspicious_findings.append(
                        f"Call to suspicious function '{module_name}.{attr_name}' at line {node.lineno}"
                    )

        self.generic_visit(node)


def detect_suspicious_code(code_str):
    """
    Analyze the input Python code string for suspicious imports, builtins,
    calls, and suspicious text patterns. Returns a list of findings.
    """
    findings = []

    # 1. AST-based analysis
    try:
        tree = ast.parse(code_str)
        visitor = SecurityNodeVisitor()
        visitor.visit(tree)
        findings.extend(visitor.suspicious_findings)
    except SyntaxError as e:
        findings.append(f"Cannot parse code (syntax error): {e}")

    # 2. Naive string-based checks
    for pattern in SUSPICIOUS_TEXT_PATTERNS:
        matches = re.findall(pattern, code_str)
        if matches:
            findings.append(f"Code contains suspicious pattern: '{pattern}'")

    return findings

