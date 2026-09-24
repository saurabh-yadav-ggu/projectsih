import pytest
from pathlib import Path
from app.backends.state import StateBackend
from app.backends.filesystem import FilesystemBackend


def test_state_backend_thread_isolation():
    state = StateBackend()
    state.set_key("thread-1", "plan", {"intent": "chat"})
    state.set_key("thread-2", "plan", {"intent": "document"})

    assert state.get_key("thread-1", "plan")["intent"] == "chat"
    assert state.get_key("thread-2", "plan")["intent"] == "document"


def test_filesystem_backend_user_isolation(tmp_path: Path):
    fs = FilesystemBackend(root_dir=tmp_path)
    ws_1 = fs.get_user_workspace(101)
    ws_2 = fs.get_user_workspace(102)

    assert str(ws_1) != str(ws_2)
    assert ws_1.exists()
    assert (ws_1 / "generated").exists()
    assert (ws_2 / "uploads").exists()


def test_filesystem_backend_path_traversal_prevention(tmp_path: Path):
    fs = FilesystemBackend(root_dir=tmp_path)
    with pytest.raises(PermissionError):
        fs.resolve_safe_path(user_id=101, relative_path="../../etc/passwd")


def test_filesystem_backend_safe_delete(tmp_path: Path):
    fs = FilesystemBackend(root_dir=tmp_path)
    ws = fs.get_user_workspace(101)
    test_file = ws / "generated" / "temp.txt"
    test_file.write_text("sample content")
    assert test_file.exists()

    deleted = fs.safe_delete_file(101, "generated/temp.txt")
    assert deleted is True
    assert not test_file.exists()

    # Deleting workspace root raises PermissionError
    with pytest.raises(PermissionError):
        fs.safe_delete_file(101, ".")
