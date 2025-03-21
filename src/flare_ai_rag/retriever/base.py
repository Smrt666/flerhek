from abc import ABC, abstractmethod


class BaseRetriever(ABC):
    @abstractmethod
    def semantic_search(
        self, collection_type: str, query: str, top_k: int = 5
    ) -> list[dict]:
        """Perform semantic search using vector embeddings."""
