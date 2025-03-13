import asyncio
import contextlib
import threading

import structlog
from anyio import Event

from flare_ai_rag.ai import BaseAIProvider
from flare_ai_rag.api import BaseRouter
from flare_ai_rag.settings import settings
from flare_ai_rag.telegrambot import TelegramBot
from flare_ai_rag.twitterbot import TwitterBot, TwitterConfig

logger = structlog.get_logger(__name__)

# Error messages
ERR_AI_PROVIDER_NOT_INITIALIZED = "AI provider must be initialized"


class BotManager:
    """Manager class for handling multiple social media bots."""

    def __init__(self, router: BaseRouter) -> None:
        """Initialize the BotManager."""
        self.router = router
        self.ai_provider: BaseAIProvider | None = None
        self.telegram_bot: TelegramBot | None = None
        self.twitter_thread: threading.Thread | None = None
        self.active_bots: list[str] = []
        self.running = False
        self._telegram_polling_task: asyncio.Task | None = None

    def start_twitter_bot(self) -> bool:
        """Initialize and start the Twitter bot in a separate thread."""
        if not settings.enable_twitter:
            logger.info("Twitter bot disabled in settings")
            return False

        if not all(
            [
                settings.x_api_key,
                settings.x_api_key_secret,
                settings.x_access_token,
                settings.x_access_token_secret,
            ]
        ):
            logger.error(
                "Twitter bot not started: Missing required credentials. "
                "Please configure Twitter API credentials in settings."
            )
            return False

        try:
            config = TwitterConfig(
                bearer_token=settings.x_bearer_token,
                api_key=settings.x_api_key,
                api_secret=settings.x_api_key_secret,
                access_token=settings.x_access_token,
                access_secret=settings.x_access_token_secret,
                rapidapi_key=settings.rapidapi_key or "",
                rapidapi_host=settings.rapidapi_host,
                accounts_to_monitor=settings.accounts_to_monitor,
                polling_interval=settings.twitter_polling_interval,
            )

            twitter_bot = TwitterBot(
                router=self.router,
                config=config,
            )

            self.twitter_thread = threading.Thread(
                target=twitter_bot.start, daemon=True, name="TwitterBotThread"
            )
            self.twitter_thread.start()
            logger.info("Twitter bot started in background thread")
            self.active_bots.append("Twitter")

        except ValueError:
            logger.exception("Failed to start Twitter bot")
            return False
        except Exception:
            logger.exception("Unexpected error starting Twitter bot")
            return False
        else:
            return True

    async def start_telegram_bot(self) -> bool:
        """Initialize and start the Telegram bot."""
        if not settings.enable_telegram:
            logger.info("Telegram bot disabled in settings")
            return False

        if not settings.telegram_api_token:
            logger.warning("Telegram bot not started: Missing API token")
            return False

        try:
            allowed_users = self._parse_allowed_users()

            self.telegram_bot = TelegramBot(
                router=self.router,
                api_token=settings.telegram_api_token,
                allowed_user_ids=allowed_users,
                polling_interval=settings.telegram_polling_interval,
            )

            await self.telegram_bot.initialize()
            self._telegram_polling_task = asyncio.create_task(
                self.telegram_bot.start_polling()
            )
            self.active_bots.append("Telegram")

        except Exception:
            logger.exception("Failed to start Telegram bot")
            if self.telegram_bot:
                await self.telegram_bot.shutdown()
            return False
        else:
            return True

    def _parse_allowed_users(self) -> list[int]:
        """Parse the allowed users from settings."""
        allowed_users: list[int] = []
        if settings.telegram_allowed_users:
            try:
                allowed_users = [
                    int(user_id.strip())
                    for user_id in settings.telegram_allowed_users.split(",")
                    if user_id.strip().isdigit()
                ]
            except ValueError:
                logger.warning("Error parsing telegram_allowed_users")
        return allowed_users

    async def _check_telegram_status(self) -> None:
        """Check and handle Telegram bot status."""
        if not (
            self.telegram_bot
            and self.telegram_bot.application
            and self.telegram_bot.application.updater
            and self.telegram_bot.application.updater.running
        ):
            logger.error("Telegram bot stopped responding")
            try:
                # Store telegram_bot in a local variable to help type checker
                telegram_bot = self.telegram_bot
                if telegram_bot is not None:  # Add explicit None check
                    await telegram_bot.shutdown()
                if await self.start_telegram_bot():
                    logger.info("Telegram bot restarted successfully")
                else:
                    logger.error("Failed to restart Telegram bot")
                    self.active_bots.remove("Telegram")
            except Exception:
                logger.exception("Error restarting Telegram bot")
                self.active_bots.remove("Telegram")

    def _check_twitter_status(self) -> None:
        """Check and handle Twitter bot status."""
        if self.twitter_thread and not self.twitter_thread.is_alive():
            logger.error("Twitter bot thread terminated unexpectedly")
            self.active_bots.remove("Twitter")
            if self.start_twitter_bot():
                logger.info("Twitter bot restarted successfully")

    async def monitor_bots(self) -> None:
        """Monitor active bots and handle unexpected terminations."""
        self.running = True

        try:
            while self.running and self.active_bots:
                if "Telegram" in self.active_bots and self.telegram_bot:
                    await self._check_telegram_status()

                if "Twitter" in self.active_bots:
                    self._check_twitter_status()

                if not self.active_bots:
                    logger.error("No active bots remaining")
                    break

                await asyncio.sleep(5)

        except Exception:
            logger.exception("Error in bot monitoring loop")
        finally:
            self.running = False

    async def shutdown(self) -> None:
        """Gracefully shutdown all active bots."""
        self.running = False

        if self.telegram_bot:
            try:
                logger.info("Shutting down Telegram bot")
                await self.telegram_bot.shutdown()
            except Exception:
                logger.exception("Error shutting down Telegram bot")

        if "Twitter" in self.active_bots:
            logger.info("Twitter bot daemon thread will terminate with main process")

        logger.info("All bots shutdown completed")


async def async_start(router: BaseRouter) -> None:
    """
    Initialize and start all components of the application asynchronously.

    Args:
        BaseRouter: Router to the RAG pipeline
    """
    bot_manager = BotManager(router)

    try:
        bot_manager.start_twitter_bot()
        await bot_manager.start_telegram_bot()

        if bot_manager.active_bots:
            logger.info("Active bots: %s", ", ".join(bot_manager.active_bots))
            monitor_task = asyncio.create_task(bot_manager.monitor_bots())

            try:
                await Event().wait()
            except asyncio.CancelledError:
                logger.info("Main task cancelled")
            finally:
                monitor_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await monitor_task
                await bot_manager.shutdown()
        else:
            logger.info(
                "No bots active. Configure Twitter and/or Telegram credentials "
                "and enable them in settings to activate social monitoring."
            )
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
        await bot_manager.shutdown()
    except Exception:
        logger.exception("Fatal error in async_start")
        await bot_manager.shutdown()


def start_bot_manager(router: BaseRouter) -> None:
    """
    Initialize and start all components of the application.

    Args:
        BaseRouter: Router to the RAG pipeline
    """
    try:
        asyncio.run(async_start(router))
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception:
        logger.exception("Fatal error in start")
