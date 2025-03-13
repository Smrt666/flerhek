from dataclasses import dataclass
from typing import Any

from flare_ai_rag.ai import Model
from flare_ai_rag.transformer.prompts import TRANSFORMER_INSTRUCTION


@dataclass(frozen=True)
class TransformerConfig:
    system_prompt: str
    model: Model

    @staticmethod
    def load(model_config: dict[str, Any]) -> "TransformerConfig":
        """Loads the router config."""
        model = Model(
            model_id=model_config["id"],
            max_tokens=model_config.get("max_tokens"),
            temperature=model_config.get("temperature"),
        )

        return TransformerConfig(
            system_prompt=TRANSFORMER_INSTRUCTION,
            model=model,
        )
