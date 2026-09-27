"""
Production Docker Sandbox Backend for Deep Agents and Shield AI.

Provides isolated container execution for:
- Python execution
- Node.js execution
- Shell commands
- File creation and surgical editing
- Git operations
- Document generation (LibreOffice, Pandoc, ReportLab, docx, openpyxl, pptx, pypdf)
- Running tests
- Coding agent workflows
"""

import atexit
from functools import partial
import logging
import os
import re
import shlex
import shutil
import subprocess
import time
import uuid
import weakref
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from app.config import settings

# Deep Agents protocol & base classes
from deepagents.backends.sandbox import BaseSandbox
from deepagents.backends.protocol import (
    ExecuteResponse,
    FileData,
    FileDownloadResponse,
    FileUploadResponse,
    SandboxBackendProtocol,
    FILE_NOT_FOUND,
    PERMISSION_DENIED,
    IS_DIRECTORY,
    INVALID_PATH,
)
from deepagents.backends.local_shell import LocalShellBackend

logger = logging.getLogger("app.sandbox.docker_backend")

# Active container session registry for container reuse across single agent sessions
_SESSION_SANDBOXES: Dict[str, "DockerSandboxBackend"] = {}


def _sanitize_log_text(text: str) -> str:
    """Scrub sensitive credentials (tokens, passwords, keys) from log messages."""
    if not text:
        return ""
    scrubbed = re.sub(r"(key|token|secret|password|auth)=['\"][^'\"]+['\"]", r"\1='***REDACTED***'", text, flags=re.IGNORECASE)
    scrubbed = re.sub(r"mstrl_[A-Za-z0-9_\-]+", "mstrl_***REDACTED***", scrubbed)
    scrubbed = re.sub(r"sk-[A-Za-z0-9_\-]+", "sk-***REDACTED***", scrubbed)
    return scrubbed


def is_docker_daemon_available(timeout: float = 10.0) -> bool:
    """Verify if the local Docker daemon is installed, running, and reachable."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return False
    try:
        proc = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as exc:
        logger.debug(f"Docker availability check failed: {exc}")
        return False


def is_image_available(image_name: str, timeout: float = 10.0) -> bool:
    """Check if the given Docker image exists locally."""
    try:
        proc = subprocess.run(
            ["docker", "image", "inspect", image_name],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode == 0
    except Exception:
        return False


class DockerSandboxBackend(BaseSandbox):
    """
    Real Docker-isolated sandbox implementation of SandboxBackendProtocol for Deep Agents.
    Executes all commands and filesystem utilities inside an isolated Docker container
    with dedicated session workspace volume mounts, resource quotas, and network constraints.
    """

    def __init__(
        self,
        workspace_dir: Union[Path, str],
        session_id: Optional[str] = None,
        image: Optional[str] = None,
        allow_network: Optional[bool] = None,
        timeout: Optional[int] = None,
        memory: Optional[str] = None,
        cpus: Optional[float] = None,
        pids_limit: Optional[int] = None,
        max_output_bytes: int = 100_000,
    ):
        self.workspace_dir = Path(workspace_dir).resolve()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id or uuid.uuid4().hex[:12]

        self.image = image or settings.SANDBOX_IMAGE
        self.allow_network = allow_network if allow_network is not None else not settings.SANDBOX_NETWORK_DISABLED
        self.default_timeout = timeout or settings.SANDBOX_TIMEOUT
        self.memory = memory or settings.SANDBOX_MEMORY_LIMIT
        self.cpus = cpus or settings.SANDBOX_CPU_LIMIT
        self.pids_limit = pids_limit or settings.SANDBOX_PIDS_LIMIT
        self.max_output_bytes = max_output_bytes

        self.container_id = f"shield-{self.session_id[:16]}"
        self.container_name = f"deepagents-sandbox-{self.container_id}"
        self._closed = False
        self._atexit_hook = None

        super().__init__()

        self._start_container()
        self._atexit_hook = partial(self._atexit_cleanup, weakref.ref(self))
        atexit.register(self._atexit_hook)

    @property
    def id(self) -> str:
        """Unique identifier for this sandbox instance."""
        return self.container_id

    @staticmethod
    def _atexit_cleanup(weak_self):
        obj = weak_self()
        if obj is not None:
            try:
                obj.close()
            except Exception:
                pass

    def _start_container(self) -> None:
        """Start the isolated Docker container with strict security bounds."""
        if not is_docker_daemon_available():
            raise RuntimeError(
                "Docker daemon is not running or unreachable. Ensure Docker Desktop is active."
            )

        if not is_image_available(self.image):
            logger.info(f"Sandbox image '{self.image}' not found locally. Attempting pull or fallback...")
            # If the custom image isn't built yet, raise clear error
            raise RuntimeError(
                f"Docker sandbox image '{self.image}' is missing. Build it with: "
                f"`docker build -t {self.image} -f docker/sandbox/Dockerfile docker/sandbox`"
            )

        # Remove any lingering stale container with this name
        self._remove_container(force=True)

        network_flag = "bridge" if self.allow_network else "none"
        ws_path_str = str(self.workspace_dir.resolve()).replace("\\", "/")

        run_args = [
            "docker", "run", "-d",
            "--init",
            "--name", self.container_name,
            "--network", network_flag,
            "--cpus", str(self.cpus),
            "-m", str(self.memory),
            "--pids-limit", str(self.pids_limit),
            "--security-opt", "no-new-privileges",
            "-v", f"{ws_path_str}:/workspace:rw",
            "-v", f"{ws_path_str}:/shared:rw",
            "-w", "/workspace",
            self.image,
            "sleep", "infinity"
        ]

        logger.info(
            f"Starting Docker sandbox container: {self.container_name} "
            f"[image={self.image}, net={network_flag}, mem={self.memory}, cpus={self.cpus}, ws={ws_path_str}]"
        )
        t0 = time.perf_counter()
        try:
            res = subprocess.run(run_args, capture_output=True, text=True, timeout=30, check=False)
            if res.returncode != 0:
                err_msg = res.stderr.strip() or res.stdout.strip()
                logger.error(f"Failed to start Docker sandbox container: {err_msg}")
                raise RuntimeError(f"Docker container failed to start: {err_msg}")
            elapsed_ms = (time.perf_counter() - t0) * 1000
            logger.info(f"Sandbox container {self.container_name} ready in {elapsed_ms:.1f}ms")

            # Configure git inside container to allow mounted workspace repository
            subprocess.run(
                ["docker", "exec", self.container_name, "git", "config", "--global", "--add", "safe.directory", "*"],
                capture_output=True,
                timeout=5,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self._remove_container(force=True)
            raise RuntimeError("Timed out while starting Docker sandbox container.")
        except Exception as exc:
            self._remove_container(force=True)
            raise RuntimeError(f"Error launching Docker container: {exc}")

    def execute(
        self,
        command: str,
        *,
        timeout: Optional[int] = None,
    ) -> ExecuteResponse:
        """
        Execute command inside the isolated container using `docker exec`
        with timeout protection, output limits, and process-group cleanup.
        """
        if self._closed:
            return ExecuteResponse(output="Error: Docker sandbox is closed.", exit_code=1, truncated=False)

        if not command or not isinstance(command, str):
            return ExecuteResponse(output="Error: Command must be a non-empty string.", exit_code=1, truncated=False)

        effective_timeout = timeout if timeout is not None else self.default_timeout
        if effective_timeout <= 0:
            raise ValueError(f"Timeout must be positive, got {effective_timeout}")

        cmd_preview = _sanitize_log_text(command[:120].replace("\n", " "))
        logger.info(f"[{self.container_name}] Executing (timeout={effective_timeout}s): {cmd_preview}")

        pid_file = f"/tmp/.exec-pid-{uuid.uuid4().hex[:8]}"
        wrapper_script = (
            f"echo $$ > {pid_file} && exec /bin/bash -c " + shlex.quote(command)
        )

        exec_cmd = [
            "docker", "exec",
            self.container_name,
            "/bin/bash", "-c", wrapper_script
        ]

        t0 = time.perf_counter()
        truncated = False
        try:
            proc = subprocess.run(
                exec_cmd,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                check=False,
            )
            duration_ms = (time.perf_counter() - t0) * 1000
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            exit_code = proc.returncode

            # Output length capping
            combined_output = stdout
            if stderr:
                combined_output = f"{stdout}\n[stderr]\n{stderr}" if stdout else stderr

            if len(combined_output) > self.max_output_bytes:
                combined_output = combined_output[:self.max_output_bytes] + f"\n\n[Output truncated at {self.max_output_bytes} bytes]"
                truncated = True

            logger.info(
                f"[{self.container_name}] Command completed in {duration_ms:.1f}ms "
                f"with exit_code={exit_code}"
            )
            return ExecuteResponse(
                output=combined_output or "<no output>",
                exit_code=exit_code,
                truncated=truncated,
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.perf_counter() - t0) * 1000
            logger.warning(f"[{self.container_name}] Command timed out after {effective_timeout}s.")
            # Kill the process group inside the container
            self._kill_process_group(pid_file)
            return ExecuteResponse(
                output=f"Error: Command timed out after {effective_timeout} seconds.",
                exit_code=124,
                truncated=False,
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            logger.error(f"[{self.container_name}] Docker execution failed: {exc}")
            return ExecuteResponse(
                output=f"Error executing command in Docker sandbox: {exc}",
                exit_code=1,
                truncated=False,
            )

    def _kill_process_group(self, pid_file: str) -> None:
        """Terminate the process group inside the container left by a timed-out command."""
        try:
            kill_cmd = [
                "docker", "exec", self.container_name,
                "/bin/bash", "-c",
                f"if [ -f {pid_file} ]; then PID=$(cat {pid_file}); kill -9 -$PID 2>/dev/null || kill -9 $PID 2>/dev/null; rm -f {pid_file}; fi"
            ]
            subprocess.run(kill_cmd, capture_output=True, timeout=5, check=False)
        except Exception:
            pass

    def _resolve_target_path(self, raw_path: Union[str, Path]) -> Optional[Path]:
        """
        Resolves a container path, relative path, or host path into a canonical host path
        strictly confined within self.workspace_dir.
        
        Handles:
        - '/workspace/path/to/file.py' -> self.workspace_dir / 'path/to/file.py'
        - 'workspace/path/to/file.py'  -> self.workspace_dir / 'path/to/file.py'
        - '/shared/path/to/file.py'     -> self.workspace_dir / 'path/to/file.py'
        - 'shared/path/to/file.py'      -> self.workspace_dir / 'path/to/file.py'
        - 'path/to/file.py'             -> self.workspace_dir / 'path/to/file.py'
        - '/path/to/file.py'            -> self.workspace_dir / 'path/to/file.py'
        - Full host path                -> self.workspace_dir / '...' if within workspace_dir
        """
        p_str = str(raw_path).replace("\\", "/").strip()
        ws_str = str(self.workspace_dir.resolve()).replace("\\", "/")

        # Case 1: Absolute host path
        if p_str.lower().startswith(ws_str.lower()):
            rel = p_str[len(ws_str):].lstrip("/")
            target = (self.workspace_dir / rel).resolve()
            return target if str(target).startswith(str(self.workspace_dir)) else None

        # Case 2: Container root aliases (/workspace, /shared)
        for prefix in ("/workspace/", "workspace/", "/shared/", "shared/"):
            if p_str.startswith(prefix):
                p_str = p_str[len(prefix):]
                break

        if p_str in ("/workspace", "workspace", "/shared", "shared", "/", ".", ""):
            return self.workspace_dir.resolve()

        clean_p = p_str.lstrip("/")
        target = (self.workspace_dir / clean_p).resolve()
        if not str(target).startswith(str(self.workspace_dir)):
            return None
        return target

    def upload_files(self, files: Union[List[Tuple[str, Union[bytes, str]]], Sequence[Any]]) -> List[FileUploadResponse]:
        """Write files directly to the host-mounted workspace directory.
        
        Returns a list of FileUploadResponse objects corresponding to the input files.
        """
        if self._closed:
            closed_responses = []
            for item in files:
                p = getattr(item, "path", None) or (item[0] if isinstance(item, (tuple, list)) else str(item))
                closed_responses.append(FileUploadResponse(path=str(p), error="Sandbox closed"))
            return closed_responses

        responses: List[FileUploadResponse] = []
        for item in files:
            if hasattr(item, "path"):
                path_str = str(item.path)
                content = getattr(item, "content", b"")
            elif isinstance(item, (tuple, list)) and len(item) >= 2:
                path_str = str(item[0])
                content = item[1]
            else:
                path_str = str(item)
                content = b""

            target = self._resolve_target_path(path_str)
            if target is None:
                responses.append(FileUploadResponse(path=path_str, error=PERMISSION_DENIED))
                continue

            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, str):
                    target.write_text(content, encoding="utf-8")
                elif isinstance(content, (bytes, bytearray)):
                    target.write_bytes(content)
                else:
                    target.write_bytes(bytes(content))
                responses.append(FileUploadResponse(path=path_str, error=None))
            except Exception as exc:
                responses.append(FileUploadResponse(path=path_str, error=str(exc)))

        return responses

    def download_files(self, paths: Sequence[str]) -> List[FileDownloadResponse]:
        """Read files from the workspace directory.
        
        Returns a list of FileDownloadResponse objects corresponding to the input paths.
        """
        if self._closed:
            return [FileDownloadResponse(path=str(p), content=None, error="Sandbox closed") for p in paths]

        responses: List[FileDownloadResponse] = []
        for p in paths:
            path_str = str(p)
            target = self._resolve_target_path(path_str)
            if target is None:
                responses.append(FileDownloadResponse(path=path_str, content=None, error=PERMISSION_DENIED))
                continue

            if not target.exists():
                responses.append(FileDownloadResponse(path=path_str, content=None, error=FILE_NOT_FOUND))
                continue

            if target.is_dir():
                responses.append(FileDownloadResponse(path=path_str, content=None, error=IS_DIRECTORY))
                continue

            try:
                content = target.read_bytes()
                responses.append(FileDownloadResponse(path=path_str, content=content, error=None))
            except Exception as exc:
                responses.append(FileDownloadResponse(path=path_str, content=None, error=str(exc)))

        return responses

    def close(self) -> None:
        """Gracefully stop and destroy the sandbox container."""
        if self._closed:
            return
        self._closed = True

        if self._atexit_hook is not None:
            try:
                atexit.unregister(self._atexit_hook)
            except Exception:
                pass

        logger.info(f"Destroying Docker sandbox container: {self.container_name}")
        self._remove_container(force=True)

    def _remove_container(self, force: bool = True) -> None:
        """Invoke docker rm to remove the container."""
        try:
            cmd = ["docker", "rm", "-f", self.container_name] if force else ["docker", "rm", self.container_name]
            subprocess.run(cmd, capture_output=True, timeout=10, check=False)
        except Exception:
            pass

    def __enter__(self) -> "DockerSandboxBackend":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


def get_or_create_sandbox_backend(
    workspace_dir: Path,
    session_id: str,
    allow_network: Optional[bool] = None,
) -> SandboxBackendProtocol:
    """
    Factory resolving either DockerSandboxBackend (default production)
    or LocalShellBackend (development mode), reusing container across the session.
    """
    backend_mode = settings.SANDBOX_BACKEND.lower().strip()

    if backend_mode == "local":
        logger.warning(
            "SECURITY NOTICE: Running in 'local' sandbox mode. Commands execute directly on host "
            "without Docker isolation. Use only for trusted local development."
        )
        return LocalShellBackend(root_dir=workspace_dir, inherit_env=True)

    # Production default: Docker Sandbox
    existing = _SESSION_SANDBOXES.get(session_id)
    if existing is not None and not existing._closed:
        # Check if container is still alive in Docker
        proc = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", existing.container_name],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if proc.returncode == 0 and "true" in proc.stdout.lower():
            return existing
        else:
            logger.info(f"Existing sandbox container for session {session_id} died; recreating...")
            existing.close()
            _SESSION_SANDBOXES.pop(session_id, None)

    sandbox = DockerSandboxBackend(
        workspace_dir=workspace_dir,
        session_id=session_id,
        allow_network=allow_network,
    )
    _SESSION_SANDBOXES[session_id] = sandbox
    return sandbox


def cleanup_session_sandbox(session_id: str) -> None:
    """Stop and destroy the container associated with a session."""
    sandbox = _SESSION_SANDBOXES.pop(session_id, None)
    if sandbox:
        try:
            sandbox.close()
        except Exception as exc:
            logger.warning(f"Error during sandbox cleanup for session {session_id}: {exc}")
