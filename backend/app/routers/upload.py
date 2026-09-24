import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.repositories import ThreadRepository, MessageRepository
from app.rag import add_file

router = APIRouter(prefix="/api/upload", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    thread_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a document (.pdf, .txt, .md) or image (.png, .jpg, .jpeg, .webp)
    associated with a thread_id for RAG knowledge base & vision analysis.
    """
    allowed_extensions = [".pdf", ".txt", ".md", ".docx", ".csv", ".png", ".jpg", ".jpeg", ".webp"]
    filename = file.filename or "uploaded_file.txt"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed types: {', '.join(allowed_extensions)}"
        )

    # Obtain or create thread for document context
    if thread_id and thread_id.strip():
        thread = ThreadRepository.get_thread(db, thread_id=thread_id.strip(), user_id=current_user.id)
        if not thread:
            thread = ThreadRepository.create_thread(db, user_id=current_user.id, title=f"Doc: {filename[:30]}")
    else:
        thread = ThreadRepository.create_thread(db, user_id=current_user.id, title=f"Doc: {filename[:30]}")

    saved_file_path = UPLOAD_DIR / filename

    try:
        content = await file.read()
        with open(saved_file_path, "wb") as f:
            f.write(content)

        chunks_added = add_file(
            file_path=str(saved_file_path),
            thread_id=thread.id,
            user_id=current_user.id
        )
        is_image = ext in [".png", ".jpg", ".jpeg", ".webp"]

        msg = (
            f"Successfully uploaded image '{filename}' into thread."
            if is_image
            else f"Successfully indexed '{filename}' ({chunks_added} chunks) into thread context."
        )

        # Record upload in thread database
        sys_msg_content = f"Uploaded {'image' if is_image else 'document'} '{filename}' into thread context."
        MessageRepository.add_message(
            db=db,
            thread_id=thread.id,
            role="system",
            content=sys_msg_content
        )
        ThreadRepository.touch_thread(db, thread_id=thread.id, user_id=current_user.id)

        return {
            "message": msg,
            "chunks_added": chunks_added,
            "filename": filename,
            "file_path": str(saved_file_path),
            "is_image": is_image,
            "thread_id": thread.id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}"
        )
