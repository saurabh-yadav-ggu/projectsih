import asyncio
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Optional

from app.config import settings
from app.sandbox.models import SandboxConfig, ExecutionResult
from app.sandbox.executor import SandboxExecutor, _RUNTIME_SHIMS
from app.sandbox.security import validate_code_safety

logger = logging.getLogger("app.sandbox.docker_executor")


class DockerSandboxExecutor:
    """
    Real Docker container sandbox runner for Python execution.
    Executes Python code inside an isolated container with volume-mounted workspace,
    memory/CPU quotas, process limit, and network disabled by default.
    """

    def __init__(self, config: Optional[SandboxConfig] = None, image: Optional[str] = None):
        self.config = config or SandboxConfig()
        self.image = image or settings.SANDBOX_IMAGE
        self.local_fallback = SandboxExecutor(self.config)
        self.docker_available: Optional[bool] = None

    async def is_docker_available(self) -> bool:
        if self.docker_available is not None:
            return self.docker_available

        docker_path = shutil.which("docker")
        if not docker_path:
            self.docker_available = False
            return False

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.wait(), timeout=10)
            self.docker_available = (proc.returncode == 0)
        except Exception:
            self.docker_available = False

        return self.docker_available

    async def execute(
        self,
        code: str,
        workspace: Optional[Path] = None,
        timeout: Optional[int] = None,
        check_security: bool = False,
    ) -> ExecutionResult:
        start_time = time.perf_counter()

        # Check sandbox backend configuration mode
        if settings.SANDBOX_BACKEND.lower().strip() == "local":
            logger.warning(
                "Executing via local fallback executor. Set SANDBOX_BACKEND=docker for container isolation."
            )
            return await self.local_fallback.execute(
                code=code, workspace=workspace, timeout=timeout, check_security=check_security
            )

        if not await self.is_docker_available():
            err_msg = (
                "Docker daemon is unavailable. Real Docker sandbox cannot execute code. "
                "Ensure Docker Desktop is running, or set SANDBOX_BACKEND=local for local development."
            )
            logger.error(err_msg)
            return ExecutionResult(
                success=False,
                exit_code=1,
                stdout="",
                stderr=err_msg,
                artifacts=[],
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                error=err_msg,
            )

        ws = Path(workspace) if workspace else (self.config.workspace_dir or Path(settings.SANDBOX_WORKSPACE_ROOT))
        ws.mkdir(parents=True, exist_ok=True)
        effective_timeout = timeout or self.config.timeout_seconds or settings.SANDBOX_TIMEOUT

        # AST Safety inspection if requested
        if check_security:
            is_safe, violations = validate_code_safety(code, allowed_modules=self.config.allowed_modules)
            if not is_safe:
                return ExecutionResult(
                    success=False,
                    exit_code=1,
                    stdout="",
                    stderr=f"Security Violation: {'; '.join(violations)}",
                    artifacts=[],
                    execution_time_ms=(time.perf_counter() - start_time) * 1000,
                    error="Code failed sandbox security validation",
                )

        pre_files = set(ws.glob("**/*")) if ws.exists() else set()

        # Prepare executable code including runtime compatibility shims
        executable_code = f"{_RUNTIME_SHIMS}\n\n{code}"

        # Resolve clean paths for Docker volume mounting
        ws_abs = str(ws.resolve()).replace("\\", "/")
        memory_limit = f"{self.config.max_memory_mb}m" if self.config.max_memory_mb else settings.SANDBOX_MEMORY_LIMIT
        cpu_limit = str(settings.SANDBOX_CPU_LIMIT)
        net_mode = "none" if (self.config.block_network or settings.SANDBOX_NETWORK_DISABLED) else "bridge"

        cmd = [
            "docker", "run", "--rm",
            "--network", net_mode,
            "--cpus", cpu_limit,
            "-m", memory_limit,
            "--pids-limit", str(settings.SANDBOX_PIDS_LIMIT),
            "--security-opt", "no-new-privileges",
            "-v", f"{ws_abs}:/workspace:rw",
            "-v", f"{ws_abs}:/shared:rw",
            "-w", "/workspace",
            self.image,
            "python3", "-c", executable_code
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=effective_timeout
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            exit_code = proc.returncode or 0

            # Scan for newly created artifacts in workspace
            post_files = set(ws.glob("**/*")) if ws.exists() else set()
            new_files = [str(f.resolve()) for f in (post_files - pre_files) if f.is_file()]

            return ExecutionResult(
                success=(exit_code == 0),
                exit_code=exit_code,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                artifacts=new_files,
                execution_time_ms=duration_ms,
                error=None if exit_code == 0 else f"Process exited with code {exit_code}"
            )
        except asyncio.TimeoutError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            return ExecutionResult(
                success=False,
                exit_code=124,
                stdout="",
                stderr=f"Execution timed out after {effective_timeout} seconds.",
                artifacts=[],
                execution_time_ms=duration_ms,
                error=f"Execution timed out after {effective_timeout} seconds."
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Docker execution exception: {exc}")
            return ExecutionResult(
                success=False,
                exit_code=1,
                stdout="",
                stderr=f"Docker container execution error: {exc}",
                artifacts=[],
                execution_time_ms=duration_ms,
                error=str(exc)
            )
