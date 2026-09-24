from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class SandboxConfig:
    timeout_seconds: int = 60
    max_memory_mb: int = 512
    allowed_modules: List[str] = field(default_factory=lambda: [
        "os", "sys", "json", "math", "datetime", "pathlib", "csv", "io", "re",
        "docx", "openpyxl", "pptx", "reportlab", "pandas", "pypdf", "mcp_docgen",
        "string", "random", "collections", "itertools", "functools", "typing",
        "copy", "time", "dataclasses", "enum", "numbers", "decimal", "fractions", "base64"
    ])
    block_network: bool = True
    workspace_dir: Optional[Path] = None


@dataclass
class ExecutionResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    artifacts: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "artifacts": self.artifacts,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
        }
