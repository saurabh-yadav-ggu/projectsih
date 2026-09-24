from typing import Dict, Any, Optional


class StateBackend:
    """
    Thread-scoped execution state backend.
    Manages active plans, subagent outputs, intermediate reasoning scratchpads,
    and ephemeral execution contexts for conversation threads.
    """

    def __init__(self):
        self._states: Dict[str, Dict[str, Any]] = {}

    def get_thread_state(self, thread_id: str) -> Dict[str, Any]:
        if thread_id not in self._states:
            self._states[thread_id] = {
                "thread_id": thread_id,
                "current_plan": None,
                "current_task": None,
                "subagent_results": {},
                "artifacts": [],
                "scratchpad": {},
            }
        return self._states[thread_id]

    def set_key(self, thread_id: str, key: str, value: Any):
        state = self.get_thread_state(thread_id)
        state[key] = value

    def get_key(self, thread_id: str, key: str, default: Any = None) -> Any:
        state = self.get_thread_state(thread_id)
        return state.get(key, default)

    def record_subagent_result(self, thread_id: str, agent_name: str, result: Any):
        state = self.get_thread_state(thread_id)
        state["subagent_results"][agent_name] = result

    def clear_thread_state(self, thread_id: str):
        if thread_id in self._states:
            del self._states[thread_id]
