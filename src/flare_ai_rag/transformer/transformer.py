from typing import Any, override

import structlog

from flare_ai_rag.ai import GeminiProvider, OpenRouterClient
from flare_ai_rag.transformer import BaseQueryTransformer
from flare_ai_rag.transformer.config import TransformerConfig
from flare_ai_rag.utils import (
    parse_chat_response_as_json,
    parse_gemini_response_as_json,
)

logger = structlog.get_logger(__name__)


class GeminiTransformer(BaseQueryTransformer):
    """
    Transform the query into a retriever-ready format with keywords.
    """

    def __init__(
        self, client: GeminiProvider, transformer_config: TransformerConfig
    ) -> None:
        """
        Initialize the transformer with a GeminiProvider instance.
        """
        self.transformer_config = transformer_config
        self.client = client

    @override
    def transform_query(
        self,
        prompt: str,
        response_mime_type: str | None = None,
        response_schema: Any | None = None,
    ) -> (str, str):
        logger.debug("Sending prompt...", prompt=prompt)
        # Use the generate method of GeminiProvider to obtain a response.
        response = self.client.generate(
            prompt=prompt,
            response_mime_type=response_mime_type,
            response_schema=response_schema,
        )
        logger.debug("Generated response from query router...", response=response)
        # Parse the response to extract result.
        result = parse_gemini_response_as_json(response.raw_response)
        transformed = result.get("transformed", "")
        keywords = result.get("keywords", [])
        # Validate the result.
        print(result)

        return transformed, keywords


class QueryTransformer(BaseQueryTransformer):
    """
    Transform the query into a retriever-ready format with keywords.
    """

    def __init__(self, client: OpenRouterClient, config: TransformerConfig) -> None:
        """
        Initialize the transformer with an API key and model name.
        :param api_key: Your OpenRouter API key.
        :param model: The model to use.
        """
        self.transformer_config = config
        self.client = client
        self.query = ""

    @override
    def transform_query(
        self,
        prompt: str,
        response_mime_type: str | None = None,
        response_schema: Any | None = None,
    ) -> (str, str):
        payload: dict[str, Any] = {
            "model": self.transformer_config.model.model_id,
            "messages": [
                {"role": "system", "content": self.transformer_config.system_prompt},
                {"role": "user", "content": prompt},
            ],
        }

        if self.transformer_config.model.max_tokens is not None:
            payload["max_tokens"] = self.transformer_config.model.max_tokens
        if self.transformer_config.model.temperature is not None:
            payload["temperature"] = self.transformer_config.model.temperature

        # Get response
        response = self.client.send_chat_completion(payload)
        classification = (
            parse_chat_response_as_json(response).get("classification", "").upper()
        )

        # Parse the response to extract result.
        result = parse_chat_response_as_json(response)
        transformed = result.get("transformed", "")
        keywords = result.get("keywords", [])

        return transformed, keywords
