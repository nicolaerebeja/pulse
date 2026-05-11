"""Scheduler — polls all active YouTube channels and notifies subscribed chats on new videos."""

import logging
from datetime import datetime, timezone

from telegram import Bot

from pulse.config import settings
from pulse.db import execute, fetch_all, fetch_one, fetch_value
from pulse.llm import summarize
from pulse.youtube import fetch_recent_videos, get_transcript

logger = logging.getLogger(__name__)


async def poll_all_channels(bot: Bot) -> None:
    """Check every active channel for new videos. Called by APScheduler every N minutes."""
    channels = await fetch_all(
        """
        SELECT DISTINCT yc.id, yc.yt_id, yc.name, yc.last_video_id
          FROM yt_channels yc
          JOIN chat_subs cs ON cs.yt_channel_id = yc.id
        """
    )
    logger.info("poll_all_channels channels=%d", len(channels))

    for ch in channels:
        try:
            await _poll_channel(bot, ch)
        except Exception as exc:
            logger.error("poll_channel failed channel=%s error=%s", ch["yt_id"], exc)


async def _poll_channel(bot: Bot, channel: dict) -> None:
    """Check one channel for new videos and process each one found."""
    recent = await fetch_recent_videos(channel["yt_id"])
    if not recent:
        logger.warning("poll_channel no videos returned channel=%s", channel["yt_id"])
        return

    await execute(
        "UPDATE yt_channels SET checked_at = :now WHERE id = :id",
        now=datetime.now(timezone.utc),
        id=channel["id"],
    )

    last_vid = channel["last_video_id"]

    # First check: just record the newest video ID, don't notify.
    if last_vid is None:
        await execute(
            "UPDATE yt_channels SET last_video_id = :vid WHERE id = :id",
            vid=recent[0]["video_id"],
            id=channel["id"],
        )
        logger.info("poll_channel first check, recording last_video_id channel=%s", channel["yt_id"])
        return

    # Find all videos newer than last_vid (playlist is newest-first).
    ids = [v["video_id"] for v in recent]
    if last_vid in ids:
        new_videos = recent[: ids.index(last_vid)]  # everything before last_vid
    else:
        # last_vid not in the last _PLAYLIST_MAX results — all fetched videos are new
        new_videos = recent

    if not new_videos:
        logger.debug("poll_channel no new videos channel=%s", channel["yt_id"])
        return

    logger.info("poll_channel found %d new video(s) channel=%s", len(new_videos), channel["yt_id"])

    # Process oldest-to-newest so notifications arrive in chronological order.
    for video_meta in reversed(new_videos):
        video_id = video_meta["video_id"]
        logger.info("poll_channel processing video=%s channel=%s", video_id, channel["yt_id"])

        video = await _ensure_video_processed(
            video_id=video_id,
            yt_channel_id=channel["id"],
            title=video_meta["title"],
            published_at=video_meta["published_at"],
        )
        if not video:
            continue
        await _notify_subscribers(bot, channel_id=channel["id"], video=video)

    # Update last_video_id to the most recent video (first in the newest-first list).
    await execute(
        "UPDATE yt_channels SET last_video_id = :vid WHERE id = :id",
        vid=new_videos[0]["video_id"],
        id=channel["id"],
    )


async def _ensure_video_processed(
    video_id: str,
    yt_channel_id: int,
    title: str | None,
    published_at: datetime | None,
) -> dict | None:
    """Return video dict with summary. Fetch transcript + summarize if not done yet."""
    existing = await fetch_one("SELECT id, yt_id, title, summary FROM videos WHERE yt_id = :vid", vid=video_id)
    if existing and existing["summary"]:
        return existing

    transcript = await get_transcript(video_id)
    if not transcript:
        logger.warning("ensure_video_processed no transcript video=%s", video_id)
        return None

    summary = await summarize(transcript)
    if not summary:
        logger.warning("ensure_video_processed no summary video=%s", video_id)
        return None

    now = datetime.now(timezone.utc)

    if existing:
        await execute(
            """
            UPDATE videos
               SET transcript = :transcript, summary = :summary, processed_at = :now
             WHERE yt_id = :vid
            """,
            transcript=transcript, summary=summary, now=now, vid=video_id,
        )
        return {**existing, "summary": summary, "title": title}

    await execute(
        """
        INSERT INTO videos (yt_id, yt_channel_id, title, transcript, summary, published_at, processed_at)
        VALUES (:vid, :ch_id, :title, :transcript, :summary, :published_at, :now)
        ON CONFLICT (yt_id) DO UPDATE
            SET transcript = EXCLUDED.transcript,
                summary = EXCLUDED.summary,
                processed_at = EXCLUDED.processed_at
        """,
        vid=video_id, ch_id=yt_channel_id, title=title,
        transcript=transcript, summary=summary,
        published_at=published_at, now=now,
    )
    return {"yt_id": video_id, "title": title, "summary": summary}


async def _notify_subscribers(bot: Bot, channel_id: int, video: dict) -> None:
    """Send notification to all chats subscribed to this channel, skip already notified."""
    chats = await fetch_all(
        "SELECT chat_id FROM chat_subs WHERE yt_channel_id = :ch_id",
        ch_id=channel_id,
    )

    title_line = f"*{video['title']}*\n\n" if video.get("title") else ""
    text = f"🎬 {title_line}{video['summary']}\n\n🔗 https://youtube.com/watch?v={video['yt_id']}"

    for row in chats:
        chat_id = row["chat_id"]
        already = await fetch_value(
            "SELECT 1 FROM notif_sent WHERE chat_id = :cid AND video_yt_id = :vid",
            cid=chat_id, vid=video["yt_id"],
        )
        if already:
            continue
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
            await execute(
                "INSERT INTO notif_sent (chat_id, video_yt_id) VALUES (:cid, :vid) ON CONFLICT DO NOTHING",
                cid=chat_id, vid=video["yt_id"],
            )
            logger.info("notify sent chat=%s video=%s", chat_id, video["yt_id"])
        except Exception as exc:
            logger.error("notify failed chat=%s video=%s error=%s", chat_id, video["yt_id"], exc)
