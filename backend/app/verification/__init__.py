from app.verification.artifact import Artifact
from app.verification.document import verify_artifact, verify_docx, verify_xlsx, verify_pptx, verify_pdf, verify_html
from app.verification.code import verify_code_syntax

__all__ = [
    "Artifact",
    "verify_artifact",
    "verify_docx",
    "verify_xlsx",
    "verify_pptx",
    "verify_pdf",
    "verify_html",
    "verify_code_syntax",
]
