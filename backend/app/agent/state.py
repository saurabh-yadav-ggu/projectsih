from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage


class DeepAgentState(TypedDict):
    messages: List[BaseMessage]
    query: str
    user_id: Optional[int]
    thread_id: Optional[str]
    memory_context: str
    document_context: str
    image_path: Optional[str]
    intent: str
    plan: Optional[Dict[str, Any]]
    current_agent: Optional[str]
    subagent_results: Dict[str, Any]
    artifacts: List[Dict[str, Any]]
    verification_status: Optional[str]
    final_response: str
    error: Optional[str]
