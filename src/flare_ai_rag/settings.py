from pathlib import Path

import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger(__name__)


def create_path(folder_name: str) -> Path:
    """Creates and returns a path for storing data or logs."""
    path = Path(__file__).parent.resolve().parent / f"{folder_name}"
    path.mkdir(exist_ok=True)
    return path


class Settings(BaseSettings):
    """
    Application settings model that provides configuration for all components.
    Combines both infrastructure and consensus settings.
    """

    # Flag to enable/disable attestation simulation
    simulate_attestation: bool = False

    # Gemini Settings
    gemini_api_key: str = ""

    # OpenRouter Settings
    open_router_base_url: str = "https://openrouter.ai/api/v1"
    open_router_api_key: str = ""

    # Restrict backend listener to specific IPs
    cors_origins: list[str] = ["*"]

    tuned_model_name: str = ""

    # Twitter/X bot settings
    enable_twitter: bool = False
    x_bearer_token: str = ""
    x_api_key: str = ""
    x_api_key_secret: str = ""
    x_access_token: str = ""
    x_access_token_secret: str = ""
    rapidapi_key: str = "" # get an api key from https://rapidapi.com/davethebeast/api/twitter241
    rapidapi_host: str = "twitter241.p.rapidapi.com"
    twitter_accounts_to_monitor: str = "@FlareNetworks"
    twitter_polling_interval: int = 60

    # Telegram bot settings
    enable_telegram: bool = False
    telegram_api_token: str = ""
    telegram_allowed_users: str = (
        ""  # Comma-separated list of allowed user IDs (optional)
    )
    telegram_polling_interval: int = 5

    # Path Settings
    data_path: Path = create_path("data")
    input_path: Path = create_path("flare_ai_rag")
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def accounts_to_monitor(self) -> list[str]:
        """Parse the comma-separated list of Twitter accounts to monitor."""
        if not self.twitter_accounts_to_monitor:
            return ["@privychatxyz"]
        return [
            account.strip() for account in self.twitter_accounts_to_monitor.split(",")
        ]

    @property
    def telegram_allowed_user_ids(self) -> list[int]:
        """Parse the comma-separated list of allowed Telegram user IDs."""
        if not self.telegram_allowed_users:
            return []
        try:
            return [
                int(user_id.strip())
                for user_id in self.telegram_allowed_users.split(",")
                if user_id.strip()
            ]
        except ValueError:
            logger.exception(
                "Invalid Telegram user IDs in configuration. User IDs must be integers."
            )
            return []


# Create a global settings instance
settings = Settings()
logger.debug("Settings have been initialized.", settings=settings.model_dump())
