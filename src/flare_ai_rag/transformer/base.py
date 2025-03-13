from abc import ABC, abstractmethod
from typing import Any


class BaseQueryTransformer(ABC):
    """
    An abstract base class defining the interface for query transforming.
    """

    @abstractmethod
    def transform_query(
        self,
        prompt: str,
        response_mime_type: str | None = None,
        response_schema: Any | None = None,
    ) -> (str, str):
        """
        Transform a query into retriever-redy format.
        """
