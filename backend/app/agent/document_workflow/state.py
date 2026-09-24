from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
import logging

from app.backends.state import StateBackend

logger = logging.getLogger("app.agent.document_workflow.state")


class TaskLifecycle(str, Enum):
    CREATED = "CREATED"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    SKILL_SELECTION = "SKILL_SELECTION"
    DECOMPOSING = "DECOMPOSING"
    GENERATING = "GENERATING"
    INTEGRATING = "INTEGRATING"
    VALIDATING = "VALIDATING"
    REPAIRING = "REPAIRING"
    SANDBOX_RUNNING = "SANDBOX_RUNNING"
    FILE_VALIDATING = "FILE_VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class InformationAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    REQUIRES_SOURCE = "REQUIRES_SOURCE"
    REQUIRES_USER_INPUT = "REQUIRES_USER_INPUT"
    FAILED = "FAILED"


@dataclass
class SectionTask:
    task_id: str
    section_id: str
    title: str
    objective: str
    requirements: List[str] = field(default_factory=list)
    scope_constraints: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    required_skills: List[str] = field(default_factory=list)
    source_material: Optional[str] = None
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    content: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 2
    failure_reason: Optional[str] = None
    validation_notes: List[str] = field(default_factory=list)


@dataclass
class DocumentGenerationState:
    task_id: str
    user_id: Optional[int] = None
    original_query: str = ""
    query_analysis: Dict[str, Any] = field(default_factory=dict)
    scope_lock: Dict[str, Any] = field(default_factory=lambda: {
        "must_include": [],
        "may_include": [],
        "must_not_include": []
    })
    selected_skills: List[str] = field(default_factory=list)
    document_type: str = "docx"
    document_plan: Dict[str, Any] = field(default_factory=dict)
    tasks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    task_status: Dict[str, str] = field(default_factory=dict)
    subagent_status: Dict[str, str] = field(default_factory=dict)
    generated_sections: List[Dict[str, Any]] = field(default_factory=list)
    integration_status: str = "PENDING"
    validation_results: Dict[str, Any] = field(default_factory=dict)
    repair_tasks: List[Dict[str, Any]] = field(default_factory=list)
    sandbox_status: str = "PENDING"
    file_validation_status: str = "PENDING"
    artifact_metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    overall_status: TaskLifecycle = TaskLifecycle.CREATED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    state_history: List[Dict[str, Any]] = field(default_factory=list)

    def transition_to(self, new_state: TaskLifecycle, details: Optional[str] = None):
        """Persists explicit lifecycle transitions."""
        old_state = self.overall_status
        self.overall_status = new_state
        self.updated_at = datetime.now(timezone.utc).isoformat()
        entry = {
            "from_state": old_state.value if isinstance(old_state, TaskLifecycle) else str(old_state),
            "to_state": new_state.value if isinstance(new_state, TaskLifecycle) else str(new_state),
            "timestamp": self.updated_at,
            "details": details,
        }
        self.state_history.append(entry)
        logger.info(f"Task {self.task_id} transitioned: {entry['from_state']} -> {entry['to_state']} ({details or 'ok'})")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["overall_status"] = self.overall_status.value if isinstance(self.overall_status, TaskLifecycle) else str(self.overall_status)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentGenerationState":
        copied = dict(data)
        if "overall_status" in copied and isinstance(copied["overall_status"], str):
            try:
                copied["overall_status"] = TaskLifecycle(copied["overall_status"])
            except ValueError:
                copied["overall_status"] = TaskLifecycle.CREATED
        return cls(**copied)

    def persist(self, state_backend: StateBackend):
        """Checkpoints workflow state into StateBackend."""
        thread_key = f"doc_task_{self.task_id}"
        state_backend.set_key(thread_key, "workflow_state", self.to_dict())

    @classmethod
    def load(cls, task_id: str, state_backend: StateBackend) -> Optional["DocumentGenerationState"]:
        """Loads workflow state from StateBackend for resumption."""
        thread_key = f"doc_task_{task_id}"
        data = state_backend.get_key(thread_key, "workflow_state")
        if data:
            return cls.from_dict(data)
        return None
