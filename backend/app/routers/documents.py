from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/documents", tags=["documents"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
MCP_OUT_DIR = Path(__file__).resolve().parents[1] / "mcp" / "out"

DOWNLOADABLE_EXTENSIONS = {
    ".docx", ".xlsx", ".pptx", ".pdf", ".md", ".txt", ".html",
}

MEDIA_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".pdf": "application/pdf",
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".html": "text/html; charset=utf-8",
}


@router.get("/download")
async def download_document(
    path: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
):
    """Download a generated document from the application workspace."""
    del current_user
    cleaned_path = path.strip().strip('"\'`')
    requested_path = Path(cleaned_path).expanduser()

    # Determine candidate file locations
    candidates = []
    if requested_path.is_absolute():
        candidates.append(requested_path.resolve())
    else:
        candidates.append((DOCUMENTS_DIR / requested_path.name).resolve())
        candidates.append((MCP_OUT_DIR / requested_path.name).resolve())
        candidates.append((DATA_DIR / requested_path).resolve())
        candidates.append((PROJECT_ROOT / requested_path).resolve())

    # Fallback: check DOCUMENTS_DIR and MCP_OUT_DIR for the filename if absolute path doesn't exist
    candidates.append((DOCUMENTS_DIR / requested_path.name).resolve())
    candidates.append((MCP_OUT_DIR / requested_path.name).resolve())

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