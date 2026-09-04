import os
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from app.core.security import get_current_user
from app.models.user import User
from app.rag import add_file

router = APIRouter(prefix="/api/upload", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a document (.pdf, .txt, .md) or image (.png, .jpg, .jpeg, .webp)
    to ingest into ChromaDB for RAG knowledge base & vision analysis.
    """
    allowed_extensions = [".pdf", ".txt", ".md", ".png", ".jpg", ".jpeg", ".webp"]
    filename = file.filename or "uploaded_file.txt"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed types: {', '.join(allowed_extensions)}"
        )

    saved_file_path = UPLOAD_DIR / filename

    try:
        content = await file.read()
        with open(saved_file_path, "wb") as f:
            f.write(content)

        chunks_added = add_file(str(saved_file_path))
        is_image = ext in [".png", ".jpg", ".jpeg", ".webp"]

        msg = (
            f"Successfully uploaded and analyzed image '{filename}'."
            if is_image
            else f"Successfully indexed '{filename}' into ChromaDB knowledge base."
        )

        return {
            "message": msg,
            "chunks_added": chunks_added,
            "filename": filename,
            "file_path": str(saved_file_path),
            "is_image": is_image
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}"
        )
