from typing import Protocol, runtime_checkable


@runtime_checkable
class KnowledgeSearchPort(Protocol):
    """Abstract port for semantic knowledge retrieval.

    The workflow engine depends on this protocol — not on the concrete
    repository or embedding provider. The infrastructure adapter wires them.
    """

    async def search(self, query: str, limit: int = 10) -> list[str]: ...
