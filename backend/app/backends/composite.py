from pathlib import Path
from typing import Optional

from app.backends.state import StateBackend
from app.backends.store import StoreBackend
from app.backends.filesystem import FilesystemBackend


class CompositeBackend:
    """
    CompositeBackend unifying State, Store, and Filesystem layers.
    Maintains thread-scoped execution state, persistent user memories,
    and sandboxed user workspace storage.
    """

    def __init__(
        self,
        state_backend: Optional[StateBackend] = None,
        store_backend: Optional[StoreBackend] = None,
        filesystem_backend: Optional[FilesystemBackend] = None,
    ):
        self.state = state_backend or StateBackend()
        self.store = store_backend or StoreBackend()
        self.fs = filesystem_backend or FilesystemBackend()


_default_composite: Optional[CompositeBackend] = None


def get_composite_backend() -> CompositeBackend:
    global _default_composite
    if _default_composite is None:
        _default_composite = CompositeBackend()
    return _default_composite
