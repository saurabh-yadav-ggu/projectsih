"""
Docker Sandbox Health Check for Shield AI and Deep Agents.

Verifies:
1. Docker daemon available and reachable.
2. Sandbox Docker image available locally.
3. Temporary container can start with configured security options.
4. Workspace volume mount is writable by container.
5. Command execution returns real output and exit code inside container.
"""

import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Any

from app.config import settings

logger = logging.getLogger("app.sandbox.health")


def check_sandbox_health() -> Dict[str, Any]:
    """
    Perform an end-to-end health verification of the Docker sandbox execution environment.
    """
    health: Dict[str, Any] = {
        "status": "healthy",
        "sandbox_backend": settings.SANDBOX_BACKEND,
        "checks": {
            "docker_available": False,
            "image_available": False,
            "container_startable": False,
            "workspace_writable": False,
            "command_execution": False,
        },
        "details": {},
        "timestamp": time.time(),
    }

    if settings.SANDBOX_BACKEND == "local":
        health["status"] = "degraded"
        health["details"]["notice"] = (
            "Running in local fallback mode (SANDBOX_BACKEND=local). "
            "Isolated Docker container execution is disabled."
        )
        return health

    # 1. Docker daemon check
    docker_bin = shutil.which("docker")
    if not docker_bin:
        health["status"] = "unhealthy"
        health["details"]["docker_error"] = "Docker executable not found on PATH."
        return health

    try:
        proc = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0:
            health["status"] = "unhealthy"
            health["details"]["docker_error"] = f"Docker daemon unreachable: {proc.stderr.strip()}"
            return health
        health["checks"]["docker_available"] = True
        health["details"]["docker_version"] = proc.stdout.strip()
    except Exception as exc:
        health["status"] = "unhealthy"
        health["details"]["docker_error"] = f"Docker check exception: {exc}"
        return health

    # 2. Image available check
    image = settings.SANDBOX_IMAGE
    try:
        proc = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0:
            health["status"] = "degraded"
            health["details"]["image_error"] = f"Docker image '{image}' not found locally. Build it using docker/sandbox/Dockerfile."
            return health
        health["checks"]["image_available"] = True
    except Exception as exc:
        health["status"] = "degraded"
        health["details"]["image_error"] = f"Image inspection error: {exc}"
        return health

    # 3, 4, 5. Container start, workspace write, command execution test
    test_container_name = f"shield-health-check-{int(time.time() * 1000)}"
    with tempfile.TemporaryDirectory(prefix="shield-health-") as temp_ws:
        temp_ws_path = Path(temp_ws).resolve()
        clean_ws = str(temp_ws_path).replace("\\", "/")

        run_cmd = [
            "docker", "run", "-d",
            "--name", test_container_name,
            "--network", "none",
            "--cpus", "1.0",
            "-m", "512m",
            "--pids-limit", "64",
            "--security-opt", "no-new-privileges",
            "-v", f"{clean_ws}:/workspace:rw",
            "-w", "/workspace",
            image,
            "sleep", "60"
        ]

        try:
            start_proc = subprocess.run(run_cmd, capture_output=True, text=True, timeout=15, check=False)
            if start_proc.returncode != 0:
                health["status"] = "unhealthy"
                health["details"]["container_error"] = f"Failed to start test container: {start_proc.stderr.strip()}"
                return health
            health["checks"]["container_startable"] = True

            # Test command execution and workspace writing inside container
            exec_cmd = [
                "docker", "exec", test_container_name,
                "python3", "-c",
                "import os; f = open('/workspace/health_test.txt', 'w'); f.write('OK'); f.close(); print(2 + 2)"
            ]
            exec_proc = subprocess.run(exec_cmd, capture_output=True, text=True, timeout=10, check=False)
            if exec_proc.returncode == 0 and "4" in exec_proc.stdout:
                health["checks"]["command_execution"] = True
            else:
                health["status"] = "unhealthy"
                health["details"]["exec_error"] = f"Test execution failed (code={exec_proc.returncode}): {exec_proc.stderr.strip()}"

            # Verify file was written to host workspace mount
            test_file = temp_ws_path / "health_test.txt"
            if test_file.exists() and test_file.read_text().strip() == "OK":
                health["checks"]["workspace_writable"] = True
            else:
                health["status"] = "unhealthy"
                health["details"]["workspace_error"] = "Workspace mount verification file missing on host."

        except Exception as exc:
            health["status"] = "unhealthy"
            health["details"]["test_error"] = str(exc)
        finally:
            # Clean up test container
            subprocess.run(["docker", "rm", "-f", test_container_name], capture_output=True, timeout=10, check=False)

    return health
