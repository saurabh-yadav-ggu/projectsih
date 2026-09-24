import ast
from typing import List, Tuple, Set


FORBIDDEN_MODULES: Set[str] = {
    "socket", "http", "urllib", "requests", "httpx", "aiohttp",
    "subprocess", "posix", "pty", "commands",
    "shlex", "multiprocessing", "threading"
}

FORBIDDEN_CALLS: Set[str] = {
    "system", "popen", "spawn", "fork", "execv", "execve",
    "kill", "terminate", "rmdir", "remove", "unlink"
}

FORBIDDEN_BUILTINS: Set[str] = {
    "eval", "exec", "__import__", "compile", "breakpoint"
}


class SecurityVisitor(ast.NodeVisitor):
    def __init__(self, allowed_modules: List[str] = None):
        self.violations: List[str] = []
        self.allowed_modules = set(allowed_modules or [])

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base_mod = alias.name.split(".")[0]
            if base_mod in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden module import: '{alias.name}'")
            elif self.allowed_modules and base_mod not in self.allowed_modules:
                self.violations.append(f"Module '{base_mod}' is not in allowed sandbox modules")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base_mod = node.module.split(".")[0]
            if base_mod in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden from-import: '{node.module}'")
            elif self.allowed_modules and base_mod not in self.allowed_modules:
                self.violations.append(f"Module '{base_mod}' is not in allowed sandbox modules")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Check direct calls like eval() or exec()
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_BUILTINS:
                self.violations.append(f"Forbidden built-in call: '{node.func.id}()'")
        # Check attribute calls like os.system()
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in FORBIDDEN_CALLS:
                self.violations.append(f"Forbidden function call: '.{node.func.attr}()'")
        self.generic_visit(node)


def validate_code_safety(code: str, allowed_modules: List[str] = None) -> Tuple[bool, List[str]]:
    """
    Parses code into an AST and inspects for forbidden imports and calls.
    Returns (is_safe, list_of_violations).
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, [f"Syntax error during security parsing: {str(e)}"]

    visitor = SecurityVisitor(allowed_modules=allowed_modules)
    visitor.visit(tree)

    if visitor.violations:
        return False, visitor.violations
    return True, []
