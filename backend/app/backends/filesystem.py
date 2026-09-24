import os
import shutil
from pathlib import Path
from typing import Optional, List


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent / "workspace"


class FilesystemBackend:
    """
    FilesystemBackend managing user-isolated file workspaces.
    Enforces user directory isolation, path traversal defense, and safe file operations.
    """

    def __init__(self, root_dir: Optional[Path] = None):
        self.root = root_dir or WORKSPACE_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def get_user_workspace(self, user_id: int) -> Path:
        """Returns the sandboxed root path for a specific user."""
        user_ws = self.root / "users" / str(user_id)
        for subdir in ["uploads", "projects", "generated", "code", "temporary", "artifacts"]:
            (user_ws / subdir).mkdir(parents=True, exist_ok=True)
        return user_ws

    def get_user_generated_dir(self, user_id: int) -> Path:
        ws = self.get_user_workspace(user_id)
        return ws / "generated"

    def resolve_safe_path(self, user_id: int, relative_path: str) -> Path:
        """
        Resolves a user-supplied relative path against the user's workspace.
        Raises PermissionError if the resolved path escapes the user directory.
        """
        user_ws = self.get_user_workspace(user_id).resolve()
        target = (user_ws / relative_path).resolve()

        if not str(target).startswith(str(user_ws)):
            raise PermissionError(f"Access denied: path '{relative_path}' escapes user workspace boundary.")

        return target

    def list_user_files(self, user_id: int, subdir: str = "") -> List[Path]:
        """Lists files within a user's workspace."""
        base = self.resolve_safe_path(user_id, subdir)
        if not base.exists():
            return []
        return [p for p in base.glob("**/*") if p.is_file()]

    def safe_delete_file(self, user_id: int, relative_path: str) -> bool:
        """
        Safely deletes a file within the user's workspace.
        Never allows deleting the workspace root or parent directories.
        """
        target = self.resolve_safe_path(user_id, relative_path)
        user_ws = self.get_user_workspace(user_id).resolve()

        if target == user_ws or not target.is_relative_to(user_ws):
            raise PermissionError("Cannot delete user workspace root.")

        if target.is_file():
            target.unlink()
            return True
        elif target.is_dir():
            # Only allow deleting leaf directories or subdirectories inside user workspace
            if target == user_ws / "uploads" or target == user_ws / "generated":
                # Clear contents instead of deleting standard directories
                for item in target.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                return True
            shutil.rmtree(target)
            return True
        return False
