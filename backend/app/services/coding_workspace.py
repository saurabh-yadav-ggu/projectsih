import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from fastapi import HTTPException

from app.backends.filesystem import WORKSPACE_ROOT
from app.schemas.coding import FileNode

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".idea",
    ".vscode",
    ".agents",
    ".shield",
    ".skills",
}


class CodingWorkspaceService:
    @staticmethod
    def get_default_workspace(user_id: int) -> Path:
        """Returns and ensures the default code workspace for a given user."""
        ws = WORKSPACE_ROOT / "users" / str(user_id) / "code"
        ws.mkdir(parents=True, exist_ok=True)
        return ws

    @staticmethod
    def resolve_workspace_dir(
        user_id: int,
        custom_path: Optional[str] = None,
        create_if_missing: bool = True
    ) -> Path:
        """
        Resolves the active workspace directory for a user.
        Supports:
        - None / empty: default user sandbox workspace (`users/{user_id}/code`)
        - Relative path: resolved inside `users/{user_id}/projects/{custom_path}`
        - Absolute path: validates/creates the target directory anywhere on the machine
        """
        user_root = (WORKSPACE_ROOT / "users" / str(user_id)).resolve()
        user_root.mkdir(parents=True, exist_ok=True)

        if not custom_path or not str(custom_path).strip():
            return CodingWorkspaceService.get_default_workspace(user_id)

        clean = str(custom_path).strip()
        p = Path(clean).expanduser()

        if not p.is_absolute():
            # Relative path: treat as a named project folder inside user's projects/
            projects_dir = user_root / "projects"
            projects_dir.mkdir(parents=True, exist_ok=True)
            target = (projects_dir / clean).resolve()
        else:
            target = p.resolve()

        if create_if_missing and not target.exists():
            try:
                target.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        if target.exists() and target.is_dir():
            return target

        return CodingWorkspaceService.get_default_workspace(user_id)

    @staticmethod
    def list_suggested_workspaces(user_id: int) -> List[Dict[str, Any]]:
        """Returns standard and available project workspaces for quick selection."""
        user_root = (WORKSPACE_ROOT / "users" / str(user_id)).resolve()
        default_code = CodingWorkspaceService.get_default_workspace(user_id)
        projects_dir = user_root / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)

        suggestions = [
            {
                "name": "Default Sandbox (code)",
                "path": str(default_code).replace("\\", "/"),
                "type": "default",
                "description": "Per-user isolated sandbox directory",
            }
        ]

        # Subdirectories in user's default sandbox workspace
        if default_code.exists():
            for p in sorted(default_code.iterdir()):
                if p.is_dir() and not p.name.startswith(".") and p.name not in IGNORE_DIRS:
                    suggestions.append({
                        "name": f"Sandbox: {p.name}",
                        "path": str(p).replace("\\", "/"),
                        "type": "sandbox_folder",
                        "description": f"Project folder in sandbox: {p.name}",
                    })

        # Host project root (d:/sih/project)
        host_root = Path(__file__).resolve().parent.parent.parent.parent
        if host_root.exists() and host_root.is_dir():
            suggestions.append({
                "name": f"Current Project Repo ({host_root.name})",
                "path": str(host_root).replace("\\", "/"),
                "type": "project_root",
                "description": "The main repository codebase",
            })

        # Subdirectories in user's projects folder
        if projects_dir.exists():
            for p in sorted(projects_dir.iterdir()):
                if p.is_dir() and not p.name.startswith(".") and p.name not in IGNORE_DIRS:
                    suggestions.append({
                        "name": p.name,
                        "path": str(p).replace("\\", "/"),
                        "type": "user_project",
                        "description": f"User project folder in {p.name}",
                    })

        return suggestions

    @staticmethod
    def browse_filesystem(target_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Browses directories on the local host filesystem for interactive folder selection.
        Returns:
        - current_path: resolved string path
        - parent_path: parent directory string path (or None if at drive root)
        - drives: list of available drive letters / roots (e.g. ['C:/', 'D:/'])
        - directories: list of subdirectories in current_path with name and path
        """
        import string

        # Available system drives (Windows) or root (Unix)
        drives = []
        if os.name == "nt":
            for d in string.ascii_uppercase:
                dp = Path(f"{d}:/")
                if dp.exists():
                    drives.append(f"{d}:/")
        else:
            drives = ["/"]

        if not target_path or not str(target_path).strip():
            # Default to host root repository or primary drive
            host_root = Path(__file__).resolve().parent.parent.parent.parent
            current = host_root if host_root.exists() else Path(drives[0] if drives else "/")
        else:
            p = Path(str(target_path).strip()).expanduser()
            if not p.is_absolute():
                host_root = Path(__file__).resolve().parent.parent.parent.parent
                current = (host_root / p).resolve()
            else:
                current = p.resolve()

        if not current.exists() or not current.is_dir():
            current = Path(drives[0] if drives else "/")

        parent = current.parent if current.parent != current else None

        subdirs = []
        try:
            for entry in sorted(current.iterdir(), key=lambda e: e.name.lower()):
                if entry.is_dir() and not entry.name.startswith((".", "$", "System Volume")):
                    if entry.name not in IGNORE_DIRS:
                        subdirs.append({
                            "name": entry.name,
                            "path": str(entry).replace("\\", "/"),
                        })
        except (PermissionError, OSError):
            pass

        return {
            "current_path": str(current).replace("\\", "/"),
            "parent_path": str(parent).replace("\\", "/") if parent else None,
            "drives": drives,
            "directories": subdirs,
        }

    @staticmethod
    def resolve_safe_file_path(workspace_root: Path, rel_path: str) -> Path:
        """Ensures the file path cannot escape the workspace root."""
        clean = rel_path.lstrip("/\\")
        resolved = (workspace_root / clean).resolve()
        try:
            resolved.relative_to(workspace_root)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: path is outside workspace root")
        return resolved

    @staticmethod
    def build_tree(current_dir: Path, root: Path, max_depth: int = 5, current_depth: int = 0) -> List[FileNode]:
        """Recursively builds file tree up to max_depth, ignoring noise directories."""
        if current_depth > max_depth or not current_dir.exists() or not current_dir.is_dir():
            return []

        nodes: List[FileNode] = []
        try:
            entries = sorted(list(current_dir.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
        except (PermissionError, OSError):
            return []

        for entry in entries:
            # Skip hidden and system directories (e.g. .agents, .shield, .skills)
            if entry.name in IGNORE_DIRS:
                continue
            if entry.is_dir() and entry.name.startswith("."):
                continue

            rel_path = str(entry.relative_to(root)).replace("\\", "/")
            if entry.is_dir():
                children = CodingWorkspaceService.build_tree(entry, root, max_depth, current_depth + 1)
                nodes.append(
                    FileNode(
                        name=entry.name,
                        path=rel_path,
                        type="directory",
                        children=children,
                    )
                )
            else:
                size = entry.stat().st_size if entry.exists() else 0
                nodes.append(
                    FileNode(
                        name=entry.name,
                        path=rel_path,
                        type="file",
                        size=size,
                    )
                )

        return nodes

    @staticmethod
    def read_file(workspace_root: Path, rel_path: str) -> Dict[str, Any]:
        """Reads file content from workspace."""
        path = CodingWorkspaceService.resolve_safe_file_path(workspace_root, rel_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"File '{rel_path}' not found")
        if path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path '{rel_path}' is a directory, not a file")

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return {
                "path": rel_path.replace("\\", "/"),
                "content": content,
                "size": path.stat().st_size,
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to read file: {exc}")

    @staticmethod
    def write_file(workspace_root: Path, rel_path: str, content: str) -> Dict[str, Any]:
        """Writes/creates a file inside workspace."""
        path = CodingWorkspaceService.resolve_safe_file_path(workspace_root, rel_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {
                "path": rel_path.replace("\\", "/"),
                "content": content,
                "size": path.stat().st_size,
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to write file: {exc}")

    @staticmethod
    def delete_file(workspace_root: Path, rel_path: str) -> bool:
        """Deletes a file or directory safely."""
        path = CodingWorkspaceService.resolve_safe_file_path(workspace_root, rel_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Target '{rel_path}' not found")
        if path == workspace_root:
            raise HTTPException(status_code=403, detail="Cannot delete workspace root")

        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            return True
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to delete '{rel_path}': {exc}")

    @staticmethod
    def rename_file(workspace_root: Path, old_rel_path: str, new_rel_path: str) -> bool:
        """Renames or moves a file within workspace."""
        src = CodingWorkspaceService.resolve_safe_file_path(workspace_root, old_rel_path)
        dst = CodingWorkspaceService.resolve_safe_file_path(workspace_root, new_rel_path)

        if not src.exists():
            raise HTTPException(status_code=404, detail=f"Source '{old_rel_path}' not found")
        if dst.exists():
            raise HTTPException(status_code=409, detail=f"Destination '{new_rel_path}' already exists")

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            return True
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to rename: {exc}")

    @staticmethod
    def git_status(workspace_root: Path) -> Dict[str, Any]:
        """Returns git branch, status porcelain, and diff if workspace is a git repo."""
        if not (workspace_root / ".git").exists():
            return {
                "is_git": False,
                "branch": "",
                "status": "",
                "diff": "",
            }

        try:
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(workspace_root),
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            status = subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=str(workspace_root),
                text=True,
                stderr=subprocess.DEVNULL,
            )

            diff = subprocess.check_output(
                ["git", "diff"],
                cwd=str(workspace_root),
                text=True,
                stderr=subprocess.DEVNULL,
            )

            return {
                "is_git": True,
                "branch": branch,
                "status": status,
                "diff": diff,
            }
        except Exception:
            return {
                "is_git": True,
                "branch": "main",
                "status": "",
                "diff": "",
            }
