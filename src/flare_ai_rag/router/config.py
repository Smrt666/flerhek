from dataclasses import dataclass
from typing import Any

from flare_ai_rag.ai import Model
from flare_ai_rag.router.prompts import ROUTER_INSTRUCTION


@dataclass(frozen=True)
class RouterConfig:
    system_prompt: str
    model: Model
    code_option: str
    answer_option: str
    reject_option: str

    @staticmethod
    def load(model_config: dict[str, Any]) -> "RouterConfig":
        """Loads the router config."""
        model = Model(
            model_id=model_config["id"],
            max_tokens=model_config.get("max_tokens"),
            temperature=model_config.get("temperature"),
        )

        return RouterConfig(
            system_prompt=ROUTER_INSTRUCTION,
            model=model,
            code_option="CODE",
            answer_option="ANSWER",
            reject_option="REJECT",
        )
