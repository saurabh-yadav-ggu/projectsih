import ast
from typing import Tuple, List


def verify_code_syntax(code: str) -> Tuple[bool, List[str]]:
    """Verify that Python code has valid syntax."""
    try:
        ast.parse(code)
        return True, ["Syntax is valid"]
    except SyntaxError as e:
        return False, [f"SyntaxError on line {e.lineno}: {e.msg}"]
    except Exception as e:
        return False, [f"Failed to parse code: {str(e)}"]
