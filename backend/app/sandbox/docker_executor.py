import asyncio
import shutil
from pathlib import Path
from typing import Optional

from app.sandbox.models import SandboxConfig, ExecutionResult
from app.sandbox.executor import SandboxExecutor


class DockerSandboxExecutor:
    """
    Docker container sandbox runner with automatic fallback to local SandboxExecutor
    if Docker is not installed or unreachable.
    """

    def __init__(self, config: Optional[SandboxConfig] = None, image: str = "python:3.12-slim"):
        self.config = config or SandboxConfig()
        self.image = image
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
            await asyncio.wait_for(proc.wait(), timeout=3)
            self.docker_available = (proc.returncode == 0)
        except Exception:
            self.docker_available = False

        return self.docker_available

    async def execute(
        self,
        code: str,
        workspace: Optional[Path] = None,
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        if not await self.is_docker_available():
            return await self.local_fallback.execute(code=code, workspace=workspace, timeout=timeout)

        # Execute inside Docker with --network none and workspace volume mount
        ws = Path(workspace) if workspace else (self.config.workspace_dir or Path("./workspace"))
        ws.mkdir(parents=True, exist_ok=True)
        effective_timeout = timeout or self.config.timeout_seconds

        cmd = [
            "docker", "run", "--rm",
            "--network", "none" if self.config.block_network else "bridge",
            "-m", f"{self.config.max_memory_mb}m",
            "-v", f"{ws.resolve()}:/workspace",
            "-w", "/workspace",
            self.image,
            "python", "-c", code
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
            exit_code = proc.returncode or 0
            return ExecutionResult(
                success=(exit_code == 0),
                exit_code=exit_code,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                artifacts=[],
                error=None if exit_code == 0 else f"Docker container exited with code {exit_code}"
            )
        except Exception as e:
            # Fallback to local execution on container failure
            return await self.local_fallback.execute(code=code, workspace=workspace, timeout=timeout)
