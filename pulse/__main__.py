"""Pulse entrypoint — starts Telegram bot and APScheduler in one process."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from pulse.bot import build_app
from pulse.config import settings
from pulse.scheduler import poll_all_channels

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    app = build_app(settings.telegram_bot_token)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        poll_all_channels,
        args=[app.bot],
        trigger="interval",
        minutes=settings.poll_interval_minutes,
        id="youtube_poll",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("scheduler started poll_interval=%d min", settings.poll_interval_minutes)

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    logger.info("pulse started")

    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
