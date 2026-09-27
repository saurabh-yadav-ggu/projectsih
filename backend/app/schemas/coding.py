from datetime import datetime
from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field


class CodingSessionCreate(BaseModel):
    workspace_path: Optional[str] = None
    title: Optional[str] = "Coding Session"
    model: Optional[str] = None
    conversation_id: Optional[str] = None


class CodingApprovalResponse(BaseModel):
    id: str
    session_id: str
    request_id: str
    action: str
    command: str
    risk_level: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CodingSessionResponse(BaseModel):
    id: str
    user_id: int
    conversation_id: Optional[str] = None
    title: str
    workspace_path: str
    model: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    approvals: Optional[List[CodingApprovalResponse]] = []

    class Config:
        from_attributes = True


class FileNode(BaseModel):
    name: str
    path: str
    type: Literal["file", "directory"]
    size: Optional[int] = None
    children: Optional[List["FileNode"]] = None


FileNode.model_rebuild()


class WorkspaceTreeResponse(BaseModel):
    root: str
    tree: List[FileNode]


class FileContentRequest(BaseModel):
    path: str
    content: str


class FileContentResponse(BaseModel):
    path: str
    content: str
    size: int


class FileRenameRequest(BaseModel):
    old_path: str
    new_path: str


class FileDeleteRequest(BaseModel):
    path: str


class TerminalExecRequest(BaseModel):
    command: str
    cwd: Optional[str] = None


class TerminalExecResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    cwd: str


class ApprovalDecisionRequest(BaseModel):
    request_id: str
    decision: Literal["approve", "reject"]


class WorkspaceSelectRequest(BaseModel):
    path: str
    create_if_missing: Optional[bool] = True


class WorkspaceSelectResponse(BaseModel):
    success: bool
    workspace: str
    name: str
    is_default: bool
    tree: List[FileNode]
