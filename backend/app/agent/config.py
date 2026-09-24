from dataclasses import dataclass


@dataclass
class AgentConfig:
    max_iterations: int = 5
    enable_verification: bool = True
    default_doc_format: str = "docx"
    allow_sandbox_code_execution: bool = True
