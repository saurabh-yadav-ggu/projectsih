import pytest
from pathlib import Path
from app.sandbox.executor import SandboxExecutor
from app.sandbox.models import SandboxConfig
from app.sandbox.security import validate_code_safety


def test_sandbox_ast_security_blocks_forbidden_imports():
    unsafe_code = """
import socket
s = socket.socket()
"""
    is_safe, violations = validate_code_safety(unsafe_code)
    assert not is_safe
    assert any("socket" in v for v in violations)


def test_sandbox_ast_security_blocks_forbidden_calls():
    unsafe_code = """
import os
os.system("echo hacked")
"""
    is_safe, violations = validate_code_safety(unsafe_code)
    assert not is_safe
    assert any(".system()" in v for v in violations)


@pytest.mark.anyio
async def test_sandbox_executor_safe_execution(tmp_path: Path):
    executor = SandboxExecutor(SandboxConfig(workspace_dir=tmp_path))
    code = """
x = 10 + 25
print(f"Result: {x}")
"""
    result = await executor.execute(code=code, workspace=tmp_path)
    assert result.success is True
    assert result.exit_code == 0
    assert "Result: 35" in result.stdout


@pytest.mark.anyio
async def test_sandbox_executor_blocks_unsafe_execution(tmp_path: Path):
    executor = SandboxExecutor(SandboxConfig(workspace_dir=tmp_path))
    code = """
import subprocess
subprocess.run(["dir"], shell=True)
"""
    result = await executor.execute(code=code, workspace=tmp_path)
    assert result.success is False
    assert "Security Violation" in result.stderr
