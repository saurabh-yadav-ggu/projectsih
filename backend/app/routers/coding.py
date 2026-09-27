import json
import logging
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.core.security import get_current_user, get_user_from_token
from app.models.user import User
from app.models.coding import CodingSession
from app.repositories import CodingRepository
from app.schemas.coding import (
    CodingSessionCreate,
    CodingSessionResponse,
    WorkspaceTreeResponse,
    FileNode,
    FileContentRequest,
    FileContentResponse,
    FileRenameRequest,
    FileDeleteRequest,
    TerminalExecRequest,
    TerminalExecResponse,
    ApprovalDecisionRequest,
    WorkspaceSelectRequest,
    WorkspaceSelectResponse,
)
from app.services.coding_workspace import CodingWorkspaceService
from app.services.coding_terminal import CodingTerminalService
from app.services.coding_runner import (
    run_coding_agent_stream,
    resume_coding_agent_approval,
    reset_coding_session,
    get_or_create_coding_session,
)

logger = logging.getLogger("app.routers.coding")

router = APIRouter(prefix="/api/coding", tags=["coding"])


# ---------------------------------------------------------------------------
# Helper: Resolve Workspace Path for User / Session
# ---------------------------------------------------------------------------

def _get_session_workspace(
    user_id: int,
    session_id: Optional[str],
    db: Session
) -> Path:
    if session_id:
        session = CodingRepository.get_session(db, session_id, user_id)
        if session and session.workspace_path:
            p = Path(session.workspace_path)
            if p.exists() and p.is_dir():
                return p
    latest = (
        db.query(CodingSession)
        .filter(CodingSession.user_id == user_id)
        .order_by(CodingSession.updated_at.desc())
        .first()
    )
    if latest and latest.workspace_path:
        p = Path(latest.workspace_path)
        if p.exists() and p.is_dir():
            return p
    return CodingWorkspaceService.get_default_workspace(user_id)


# ---------------------------------------------------------------------------
# 1. Coding Session Endpoints
# ---------------------------------------------------------------------------

@router.post("/sessions", response_model=CodingSessionResponse, status_code=status.HTTP_201_CREATED)
def create_coding_session(
    body: CodingSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new coding session tied to the authenticated user and their workspace."""
    ws = CodingWorkspaceService.resolve_workspace_dir(current_user.id, body.workspace_path)
    session = CodingRepository.create_session(
        db=db,
        user_id=current_user.id,
        workspace_path=str(ws),
        title=body.title or "Coding Session",
        model=body.model,
        conversation_id=body.conversation_id,
    )
    return session


@router.get("/sessions", response_model=List[CodingSessionResponse])
def list_coding_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all active and past coding sessions for the authenticated user."""
    return CodingRepository.list_sessions(db, current_user.id)


@router.get("/sessions/{session_id}", response_model=CodingSessionResponse)
def get_coding_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = CodingRepository.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Coding session not found")
    return session


@router.get("/sessions/{session_id}/messages")
def get_coding_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all conversation messages for this coding session thread."""
    return CodingRepository.get_messages(db, session_id, current_user.id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_coding_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reset_coding_session(session_id)
    success = CodingRepository.delete_session(db, session_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Coding session not found")
    return None


# ---------------------------------------------------------------------------
# 2. Workspace File Endpoints
# ---------------------------------------------------------------------------

@router.get("/workspace/tree", response_model=WorkspaceTreeResponse)
def get_workspace_tree(
    session_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ws = _get_session_workspace(current_user.id, session_id, db)
    tree = CodingWorkspaceService.build_tree(ws, ws)
    return WorkspaceTreeResponse(root=str(ws).replace("\\", "/"), tree=tree)


@router.get("/workspace/file", response_model=FileContentResponse)
def read_workspace_file(
    path: str = Query(..., description="Relative path within workspace"),
    session_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ws = _get_session_workspace(current_user.id, session_id, db)
    data = CodingWorkspaceService.read_file(ws, path)
    return FileContentResponse(**data)


@router.post("/workspace/file", response_model=FileContentResponse)
def write_workspace_file(
    body: FileContentRequest,
    session_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ws = _get_session_workspace(current_user.id, session_id, db)
    data = CodingWorkspaceService.write_file(ws, body.path, body.content)
    return FileContentResponse(**data)


@router.delete("/workspace/file", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace_file(
    path: str = Query(..., description="Relative path to file or directory"),
    session_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ws = _get_session_workspace(current_user.id, session_id, db)
    CodingWorkspaceService.delete_file(ws, path)
    return None


@router.patch("/workspace/file")
def rename_workspace_file(
    body: FileRenameRequest,
    session_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ws = _get_session_workspace(current_user.id, session_id, db)
    success = CodingWorkspaceService.rename_file(ws, body.old_path, body.new_path)
    return {"success": success}


@router.get("/workspace/git")
def get_workspace_git(
    session_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ws = _get_session_workspace(current_user.id, session_id, db)
    return CodingWorkspaceService.git_status(ws)


@router.get("/workspace/active")
def get_active_workspace(
    session_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ws = _get_session_workspace(current_user.id, session_id, db)
    return {
        "workspace": str(ws).replace("\\", "/"),
        "name": ws.name,
        "is_default": ws == CodingWorkspaceService.get_default_workspace(current_user.id),
    }


@router.get("/workspace/list")
def list_workspaces(
    current_user: User = Depends(get_current_user),
):
    """Returns available and suggested workspace directories for user selection."""
    return CodingWorkspaceService.list_suggested_workspaces(current_user.id)


@router.get("/workspace/browse")
def browse_workspace_directories(
    path: Optional[str] = Query(None, description="Directory path to browse"),
    current_user: User = Depends(get_current_user),
):
    """Browses host directories for interactive folder selection in the UI."""
    return CodingWorkspaceService.browse_filesystem(path)


@router.post("/workspace/select", response_model=WorkspaceSelectResponse)
def select_workspace(
    body: WorkspaceSelectRequest,
    session_id: str = Query("default"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Selects and sets the active workspace directory for a coding session."""
    ws = CodingWorkspaceService.resolve_workspace_dir(
        current_user.id,
        custom_path=body.path,
        create_if_missing=body.create_if_missing if body.create_if_missing is not None else True
    )

    clean_ws_str = str(ws).replace("\\", "/")

    # Update or create session with new workspace
    CodingRepository.update_session_workspace(db, session_id, current_user.id, clean_ws_str)

    # Invalidate in-memory cached agent session so the new workspace is loaded
    reset_coding_session(session_id)
    CodingTerminalService.set_cwd(session_id, ws)

    # Build the file tree of the newly selected workspace
    tree = CodingWorkspaceService.build_tree(ws, ws)
    default_ws = CodingWorkspaceService.get_default_workspace(current_user.id)

    return WorkspaceSelectResponse(
        success=True,
        workspace=clean_ws_str,
        name=ws.name,
        is_default=ws == default_ws,
        tree=tree,
    )


# ---------------------------------------------------------------------------
# 3. Terminal Execution Endpoints
# ---------------------------------------------------------------------------

@router.get("/terminal/info")
def get_terminal_info(
    session_id: str = Query("default"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ws = _get_session_workspace(current_user.id, session_id, db)
    cwd = CodingTerminalService.get_cwd(session_id, ws)
    return {
        "cwd": str(cwd).replace("\\", "/"),
        "workspace": str(ws).replace("\\", "/"),
        "name": cwd.name or str(cwd),
    }


@router.post("/terminal/exec", response_model=TerminalExecResponse)
def execute_terminal_command(
    body: TerminalExecRequest,
    session_id: str = Query("default"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ws = _get_session_workspace(current_user.id, session_id, db)
    result = CodingTerminalService.execute_command(
        session_id=session_id,
        workspace_root=ws,
        command_str=body.command,
        custom_cwd=body.cwd,
    )
    return TerminalExecResponse(**result)


# ---------------------------------------------------------------------------
# 4. Approval Decision Endpoint
# ---------------------------------------------------------------------------

@router.post("/approval")
def handle_approval_decision(
    body: ApprovalDecisionRequest,
    session_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    approval = CodingRepository.resolve_approval(db, session_id, body.request_id, body.decision)
    return {"success": bool(approval), "status": body.decision}


# ---------------------------------------------------------------------------
# 5. Real-Time WebSocket Gateway (/ws/coding and /api/coding/ws)
# ---------------------------------------------------------------------------

class CodingConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.running_tasks: Dict[str, asyncio.Task[None]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_event(self, websocket: WebSocket, event: Dict[str, Any]):
        try:
            await websocket.send_text(json.dumps(event))
        except Exception as exc:
            logger.warning("Failed to send WebSocket message: %s", exc)


coding_ws_manager = CodingConnectionManager()


async def _handle_coding_websocket(websocket: WebSocket, token: Optional[str] = None):
    await coding_ws_manager.connect(websocket)

    # Authenticate user from query token
    db: Session = SessionLocal()
    user: Optional[User] = None
    if token:
        user = get_user_from_token(token, db)

    current_session_id = "default"
    current_user_id = user.id if user else 1

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                msg = json.loads(raw_text)
            except json.JSONDecodeError:
                await coding_ws_manager.send_event(websocket, {"type": "error", "message": "Invalid JSON format"})
                continue

            msg_type = msg.get("type")
            session_id = msg.get("session_id", current_session_id)
            current_session_id = session_id

            # Late auth via initial message if query token was omitted
            if not user and msg.get("token"):
                user = get_user_from_token(msg["token"], db)
                if user:
                    current_user_id = user.id

            if msg_type == "prompt":
                prompt_text = msg.get("text", "").strip()
                model_name = msg.get("model")
                workspace_path = msg.get("workspace_path")
                hitl_mode = msg.get("hitl_mode", "safe")

                if not workspace_path:
                    db_session = CodingRepository.get_session(db, session_id, current_user_id)
                    if db_session and db_session.workspace_path:
                        workspace_path = db_session.workspace_path

                if not prompt_text:
                    await coding_ws_manager.send_event(websocket, {"type": "error", "message": "Prompt cannot be empty"})
                    continue

                # Run streaming loop
                async def execute_and_stream():
                    async for event in run_coding_agent_stream(
                        session_id=session_id,
                        user_id=current_user_id,
                        user_prompt=prompt_text,
                        workspace_path=workspace_path,
                        model=model_name,
                        hitl_mode=hitl_mode,
                    ):
                        # Save approval to DB if approval required
                        if event.get("type") == "agent_approval_required":
                            try:
                                CodingRepository.record_approval(
                                    db=db,
                                    session_id=session_id,
                                    request_id=event.get("request_id", ""),
                                    action=event.get("action", "execute"),
                                    command=event.get("command", ""),
                                    risk_level=event.get("risk_level", "medium"),
                                )
                            except Exception as save_err:
                                logger.warning(f"Could not persist approval to DB: {save_err}")

                        await coding_ws_manager.send_event(websocket, event)

                task = asyncio.create_task(execute_and_stream())
                coding_ws_manager.running_tasks[session_id] = task

            elif msg_type == "set_hitl_mode":
                new_hitl_mode = msg.get("mode", "safe")
                session = get_or_create_coding_session(session_id, current_user_id, hitl_mode=new_hitl_mode)
                session.set_hitl_mode(new_hitl_mode)
                await coding_ws_manager.send_event(websocket, {
                    "type": "hitl_mode_updated",
                    "session_id": session_id,
                    "hitl_mode": new_hitl_mode,
                })

            elif msg_type == "approval_response":
                decision = msg.get("decision", "reject")
                req_id = msg.get("request_id")
                if req_id:
                    try:
                        CodingRepository.resolve_approval(db, session_id, req_id, decision)
                    except Exception as res_err:
                        logger.warning(f"Could not update approval status in DB: {res_err}")

                async def resume_stream():
                    async for event in resume_coding_agent_approval(
                        session_id=session_id,
                        user_id=current_user_id,
                        decision=decision,
                        request_id=req_id,
                    ):
                        if event.get("type") == "agent_approval_required":
                            try:
                                CodingRepository.record_approval(
                                    db=db,
                                    session_id=session_id,
                                    request_id=event.get("request_id", ""),
                                    action=event.get("action", "execute"),
                                    command=event.get("command", ""),
                                    risk_level=event.get("risk_level", "medium"),
                                )
                            except Exception:
                                pass
                        await coding_ws_manager.send_event(websocket, event)

                task = asyncio.create_task(resume_stream())
                coding_ws_manager.running_tasks[session_id] = task

            elif msg_type == "stop":
                if session_id in coding_ws_manager.running_tasks:
                    coding_ws_manager.running_tasks[session_id].cancel()
                    await coding_ws_manager.send_event(websocket, {
                        "type": "agent_status",
                        "status": "idle",
                        "session_id": session_id,
                        "message": "Execution stopped by user",
                    })

            elif msg_type in ("clear", "reset"):
                reset_coding_session(session_id)
                await coding_ws_manager.send_event(websocket, {
                    "type": "agent_status",
                    "status": "idle",
                    "session_id": session_id,
                    "message": "Session reset",
                })

            elif msg_type == "select_workspace":
                target_path = msg.get("path")
                ws = CodingWorkspaceService.resolve_workspace_dir(
                    current_user_id,
                    custom_path=target_path,
                    create_if_missing=True
                )
                clean_ws_str = str(ws).replace("\\", "/")
                CodingRepository.update_session_workspace(db, session_id, current_user_id, clean_ws_str)
                reset_coding_session(session_id)
                CodingTerminalService.set_cwd(session_id, ws)
                tree = CodingWorkspaceService.build_tree(ws, ws)
                default_ws = CodingWorkspaceService.get_default_workspace(current_user_id)

                await coding_ws_manager.send_event(websocket, {
                    "type": "workspace_selected",
                    "session_id": session_id,
                    "workspace": clean_ws_str,
                    "name": ws.name,
                    "is_default": ws == default_ws,
                    "tree": [n.model_dump() for n in tree],
                })

            elif msg_type == "ping":
                await coding_ws_manager.send_event(websocket, {"type": "pong"})

    except WebSocketDisconnect:
        coding_ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.exception("Unexpected error in coding websocket")
        coding_ws_manager.disconnect(websocket)
    finally:
        db.close()


@router.websocket("/ws")
async def coding_websocket_api(websocket: WebSocket, token: Optional[str] = Query(None)):
    """WebSocket at /api/coding/ws"""
    await _handle_coding_websocket(websocket, token=token)
