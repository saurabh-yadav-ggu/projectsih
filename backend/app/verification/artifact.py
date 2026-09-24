import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List


@dataclass
class Artifact:
    filename: str
    file_type: str
    path: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[int] = None
    thread_id: Optional[str] = None
    size: int = 0
    created_at: float = field(default_factory=time.time)
    verification_status: str = "pending"  # "pending", "passed", "failed"
    verification_checks: List[str] = field(default_factory=list)
    verification_errors: List[str] = field(default_factory=list)

    @classmethod
    def from_path(
        cls,
        path: str,
        user_id: Optional[int] = None,
        thread_id: Optional[str] = None
    ) -> "Artifact":
        p = Path(path)
        ext = p.suffix.lstrip(".").lower()
        size = p.stat().st_size if p.exists() else 0
        return cls(
            id=str(uuid.uuid4()),
            filename=p.name,
            file_type=ext,
            path=str(p.resolve()),
            user_id=user_id,
            thread_id=thread_id,
            size=size,
            created_at=time.time()
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "path": self.path,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "size": self.size,
            "created_at": self.created_at,
            "verification_status": self.verification_status,
            "verification_checks": self.verification_checks,
            "verification_errors": self.verification_errors,
        }
