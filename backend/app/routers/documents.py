from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.security import get_current_user, SECRET_KEY, ALGORITHM
from app.database import get_db
from app.models.user import User
import jwt

router = APIRouter(prefix="/api/documents", tags=["documents"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
MCP_OUT_DIR = Path(__file__).resolve().parents[1] / "mcp" / "out"

DOWNLOADABLE_EXTENSIONS = {
    ".docx", ".xlsx", ".pptx", ".pdf", ".md", ".txt", ".html", ".csv",
}

MEDIA_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".pdf": "application/pdf",
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
}


def get_optional_user(
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    auth_token = None
    if authorization and authorization.startswith("Bearer "):
        auth_token = authorization.split("Bearer ", 1)[1].strip()
    elif token:
        auth_token = token.strip()

    if auth_token:
        try:
            payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if email:
                return db.query(User).filter(User.email == email).first()
        except Exception:
            pass
    return None


import time
from app.backends.composite import get_composite_backend

def format_size(bytes_size: int) -> str:
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    else:
        return f"{bytes_size / (1024 * 1024):.1f} MB"


@router.get("/generated")
async def list_generated_documents(
    current_user: User = Depends(get_current_user),
):
    """List all generated documents in the user's workspace and output directory."""
    composite = get_composite_backend()
    user_gen_dir = composite.fs.get_user_generated_dir(current_user.id)

    seen_names = set()
    documents = []

    # 1. Search user's isolated workspace generated directory
    if user_gen_dir.exists():
        for file_path in sorted(user_gen_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
            if file_path.is_file() and file_path.suffix.lower() in DOWNLOADABLE_EXTENSIONS:
                stat = file_path.stat()
                ext = file_path.suffix.lower().lstrip(".")
                documents.append({
                    "id": file_path.name,
                    "filename": file_path.name,
                    "path": file_path.as_posix(),
                    "format": ext,
                    "size": stat.st_size,
                    "size_formatted": format_size(stat.st_size),
                    "created_at": stat.st_mtime,
                    "created_at_formatted": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
                    "is_user_workspace": True,
                })
                seen_names.add(file_path.name)

    # 2. Also check MCP_OUT_DIR (shared / fallback output dir)
    if MCP_OUT_DIR.exists():
        for file_path in sorted(MCP_OUT_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
            if file_path.is_file() and file_path.suffix.lower() in DOWNLOADABLE_EXTENSIONS:
                if file_path.name not in seen_names:
                    stat = file_path.stat()
                    ext = file_path.suffix.lower().lstrip(".")
                    documents.append({
                        "id": file_path.name,
                        "filename": file_path.name,
                        "path": file_path.as_posix(),
                        "format": ext,
                        "size": stat.st_size,
                        "size_formatted": format_size(stat.st_size),
                        "created_at": stat.st_mtime,
                        "created_at_formatted": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
                        "is_user_workspace": False,
                    })
                    seen_names.add(file_path.name)

    return {"documents": documents, "count": len(documents)}


@router.delete("/generated/{filename}")
async def delete_generated_document(
    filename: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a generated document from the user's workspace."""
    composite = get_composite_backend()
    user_gen_dir = composite.fs.get_user_generated_dir(current_user.id)

    clean_name = Path(filename).name  # Sanitize against path traversal
    target_in_user = user_gen_dir / clean_name
    target_in_mcp = MCP_OUT_DIR / clean_name

    deleted = False
    if target_in_user.is_file():
        target_in_user.unlink()
        deleted = True
    elif target_in_mcp.is_file():
        target_in_mcp.unlink()
        deleted = True

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{clean_name}' not found or already deleted.",
        )

    return {"success": True, "message": f"Document '{clean_name}' deleted successfully."}


@router.get("/download")
async def download_document(
    path: str = Query(..., min_length=1),
    token: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Download a generated document from the application workspace."""
    cleaned_path = path.strip().strip('"\'`')
    requested_path = Path(cleaned_path).expanduser()

    BACKEND_DIR = Path(__file__).resolve().parents[2]
    WORKSPACE_DIR = BACKEND_DIR / "workspace"

    # Determine candidate file locations
    candidates = []
    if requested_path.is_absolute():
        candidates.append(requested_path.resolve())

    candidates.append((DOCUMENTS_DIR / requested_path.name).resolve())
    candidates.append((MCP_OUT_DIR / requested_path.name).resolve())
    candidates.append((DATA_DIR / requested_path.name).resolve())
    candidates.append((BACKEND_DIR / requested_path).resolve())
    candidates.append((PROJECT_ROOT / requested_path).resolve())

    # Search user workspaces
    if current_user:
        candidates.append((WORKSPACE_DIR / "users" / str(current_user.id) / "generated" / requested_path.name).resolve())

    if (WORKSPACE_DIR / "users").exists():
        for gen_dir in (WORKSPACE_DIR / "users").glob("*/generated"):
            candidates.append((gen_dir / requested_path.name).resolve())

    target_file: Path | None = None
    for candidate in candidates:
        if candidate.is_file():
            target_file = candidate
            break

    if not target_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Security check: must reside inside project root
    try:
        target_file.relative_to(PROJECT_ROOT)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document path is outside the application workspace",
        ) from error

    ext = target_file.suffix.lower()
    if ext not in DOWNLOADABLE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type is not downloadable",
        )

    media_type = MEDIA_TYPES.get(ext, "application/octet-stream")
    return FileResponse(
        target_file,
        filename=target_file.name,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{target_file.name}"'}
    )