import os
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from app.core.security import get_current_user
from app.models.user import User
from app.rag import add_file

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a PDF or text file to ingest into ChromaDB for RAG knowledge base.
    """
    allowed_extensions = [".pdf", ".txt", ".md"]
    filename = file.filename or "uploaded_file.txt"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed types: {', '.join(allowed_extensions)}"
        )

    # Save to temp file and load into ChromaDB
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        chunks_added = add_file(temp_file_path)

        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        return {
            "message": f"Successfully indexed '{filename}' into ChromaDB knowledge base.",
            "chunks_added": chunks_added,
            "filename": filename
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}"
        )
