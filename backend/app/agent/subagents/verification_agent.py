import logging
from pathlib import Path
from typing import Dict, Any, List

from app.verification.artifact import Artifact
from app.verification.document import verify_artifact

logger = logging.getLogger("app.agent.subagents.verification")


async def run_verification_agent(
    artifact_paths: List[str],
    user_id: int = None,
    thread_id: str = None,
) -> Dict[str, Any]:
    """
    Verification Agent inspecting generated document artifacts for structural
    integrity, readability, and content non-emptiness.
    """
    if not artifact_paths:
        return {
            "agent": "verification_agent",
            "status": "FAIL",
            "all_passed": False,
            "artifacts": [],
            "errors": ["No generated artifact files found to verify."],
        }

    verified_artifacts: List[Dict[str, Any]] = []
    all_passed = True
    errors: List[str] = []

    for path_str in artifact_paths:
        art = Artifact.from_path(path_str, user_id=user_id, thread_id=thread_id)
        verified = verify_artifact(art)
        verified_artifacts.append(verified.to_dict())

        if verified.verification_status != "passed":
            all_passed = False
            errors.extend(verified.verification_errors)

    return {
        "agent": "verification_agent",
        "status": "PASS" if all_passed else "FAIL",
        "all_passed": all_passed,
        "artifacts": verified_artifacts,
        "errors": errors,
    }
