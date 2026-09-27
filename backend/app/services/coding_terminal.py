import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# Active cwd per session_id
_terminal_cwds: Dict[str, Path] = {}


class CodingTerminalService:
    @staticmethod
    def get_cwd(session_id: str, default_ws: Path) -> Path:
        cwd = _terminal_cwds.get(session_id)
        if cwd is None or not cwd.exists():
            cwd = default_ws
            _terminal_cwds[session_id] = cwd
        return cwd

    @staticmethod
    def set_cwd(session_id: str, new_cwd: Path):
        _terminal_cwds[session_id] = new_cwd

    @staticmethod
    def execute_command(
        session_id: str,
        workspace_root: Path,
        command_str: str,
        custom_cwd: Optional[str] = None,
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        cwd = Path(custom_cwd).resolve() if custom_cwd else CodingTerminalService.get_cwd(session_id, workspace_root)
        if not cwd.exists() or not cwd.is_dir():
            cwd = workspace_root

        cmd = command_str.strip()
        if not cmd:
            return {
                "stdout": "",
                "stderr": "",
                "exit_code": 0,
                "cwd": str(cwd).replace("\\", "/"),
            }

        # Handle 'clear' / 'cls'
        if cmd.lower() in ("clear", "cls"):
            return {
                "stdout": "\x1b[2J\x1b[H",
                "stderr": "",
                "exit_code": 0,
                "cwd": str(cwd).replace("\\", "/"),
            }

        # Handle 'cd' commands
        if cmd == "cd" or cmd == "cd ~":
            CodingTerminalService.set_cwd(session_id, workspace_root)
            return {
                "stdout": "",
                "stderr": "",
                "exit_code": 0,
                "cwd": str(workspace_root).replace("\\", "/"),
            }

        if cmd.startswith("cd "):
            target_rel = cmd[3:].strip().strip("\"'")
            if target_rel == "..":
                new_dir = cwd.parent
            else:
                new_dir = (cwd / target_rel).resolve()

            # Ensure new_dir is within workspace_root or allowed paths
            try:
                new_dir.relative_to(workspace_root)
                if new_dir.exists() and new_dir.is_dir():
                    CodingTerminalService.set_cwd(session_id, new_dir)
                    return {
                        "stdout": "",
                        "stderr": "",
                        "exit_code": 0,
                        "cwd": str(new_dir).replace("\\", "/"),
                    }
                else:
                    return {
                        "stdout": "",
                        "stderr": f"cd: no such file or directory: {target_rel}\n",
                        "exit_code": 1,
                        "cwd": str(cwd).replace("\\", "/"),
                    }
            except ValueError:
                return {
                    "stdout": "",
                    "stderr": "cd: access denied: cannot navigate outside workspace root\n",
                    "exit_code": 1,
                    "cwd": str(cwd).replace("\\", "/"),
                }

        # Run process via shell
        try:
            is_win = os.name == "nt"
            res = subprocess.run(
                cmd,
                shell=True,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=os.environ.copy(),
            )
            return {
                "stdout": res.stdout,
                "stderr": res.stderr,
                "exit_code": res.returncode,
                "cwd": str(cwd).replace("\\", "/"),
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout_seconds} seconds\n",
                "exit_code": 124,
                "cwd": str(cwd).replace("\\", "/"),
            }
        except Exception as exc:
            return {
                "stdout": "",
                "stderr": f"Execution error: {exc}\n",
                "exit_code": 1,
                "cwd": str(cwd).replace("\\", "/"),
            }
