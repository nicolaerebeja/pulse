"""Telegram bot — all command and message handlers in one file."""

import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from pulse.config import settings
from pulse.db import execute, fetch_all, fetch_one, fetch_value
from pulse.llm import summarize
from pulse.youtube import extract_video_id, get_transcript, is_video_url, resolve_channel

logger = logging.getLogger(__name__)

_startup_time: datetime = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_chat(update: Update) -> None:
    """Insert chat into DB if not already there."""
    chat = update.effective_chat
    await execute(
        """
        INSERT INTO chats (chat_id, chat_type, title)
        VALUES (:cid, :ctype, :title)
        ON CONFLICT (chat_id) DO NOTHING
        """,
        cid=chat.id,
        ctype=chat.type,
        title=chat.title or chat.full_name,
    )


async def _find_channel_by_input(text: str) -> dict | None:
    """Return yt_channels row if already in DB, by yt_id or name prefix."""
    return await fetch_one(
        "SELECT id, yt_id, name FROM yt_channels WHERE yt_id = :t OR lower(name) = lower(:t)",
        t=text,
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _register_chat(update)
    await update.message.reply_text(
        "👋 Bun venit în Pulse!\n\n"
        "Trimite-mi un link de canal YouTube pentru a-l urmări:\n"
        "  /add https://youtube.com/@numecanal\n\n"
        "Sau trimite direct un link de video și primești rezumatul instant.\n\n"
        "/help — toate comenzile"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 Comenzi:\n\n"
        "/add <url_canal> — urmărește un canal YouTube\n"
        "/sources — lista canalelor urmărite în acest chat\n"
        "/remove <yt_id> — șterge un abonament\n"
        "/status — statistici\n\n"
        "Trimite orice link video YouTube → rezumat instant."
    )


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _register_chat(update)
    args = context.args or []
    if not args:
        await update.message.reply_text("Utilizare: /add <url_canal_youtube>")
        return

    url = args[0]
    chat_id = update.effective_chat.id

    if is_video_url(url):
        await update.message.reply_text("Acesta e un link de video, nu de canal. Trimite-l direct în chat pentru rezumat instant.")
        return

    await update.message.reply_text("🔍 Rezolv canalul...")
    info = await resolve_channel(url)
    if info is None:
        await update.message.reply_text("❌ Nu am putut identifica un canal YouTube valid din acest link.")
        return

    yt_id, name = info

    existing_sub = await fetch_one(
        """
        SELECT 1 FROM chat_subs cs
          JOIN yt_channels yc ON yc.id = cs.yt_channel_id
         WHERE cs.chat_id = :cid AND yc.yt_id = :yt_id
        """,
        cid=chat_id, yt_id=yt_id,
    )
    if existing_sub:
        await update.message.reply_text(f"ℹ️ Canalul «{name}» este deja urmărit în acest chat.")
        return

    channel = await fetch_one("SELECT id FROM yt_channels WHERE yt_id = :yt_id", yt_id=yt_id)
    if channel is None:
        await execute(
            "INSERT INTO yt_channels (yt_id, name) VALUES (:yt_id, :name) ON CONFLICT (yt_id) DO NOTHING",
            yt_id=yt_id, name=name,
        )
        channel = await fetch_one("SELECT id FROM yt_channels WHERE yt_id = :yt_id", yt_id=yt_id)

    await execute(
        "INSERT INTO chat_subs (chat_id, yt_channel_id) VALUES (:cid, :ch_id) ON CONFLICT DO NOTHING",
        cid=chat_id, ch_id=channel["id"],
    )
    logger.info("add channel chat=%s yt_id=%s", chat_id, yt_id)
    await update.message.reply_text(
        f"✅ Canal adăugat: *{name}*\n\nPrima verificare în maxim {settings.poll_interval_minutes} minute.",
        parse_mode="Markdown",
    )


async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _register_chat(update)
    chat_id = update.effective_chat.id
    rows = await fetch_all(
        """
        SELECT yc.yt_id, yc.name, yc.checked_at
          FROM yt_channels yc
          JOIN chat_subs cs ON cs.yt_channel_id = yc.id
         WHERE cs.chat_id = :cid
         ORDER BY yc.name
        """,
        cid=chat_id,
    )
    if not rows:
        await update.message.reply_text("Nu urmărești niciun canal. Folosește /add <url> pentru a adăuga unul.")
        return

    lines = ["📋 Canale urmărite în acest chat:\n"]
    for row in rows:
        last = row["checked_at"].strftime("%d %b %H:%M") if row["checked_at"] else "—"
        lines.append(f"🎬 {row['name'] or row['yt_id']}\n   ID: `{row['yt_id']}` | Verificat: {last}")
    await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown")


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _register_chat(update)
    args = context.args or []
    if not args:
        await update.message.reply_text("Utilizare: /remove <yt_id>\nVezi ID-urile cu /sources.")
        return

    yt_id = args[0]
    chat_id = update.effective_chat.id

    channel = await fetch_one("SELECT id, name FROM yt_channels WHERE yt_id = :yt_id", yt_id=yt_id)
    if not channel:
        await update.message.reply_text("❌ Canal negăsit. Verifică ID-ul cu /sources.")
        return

    deleted = await execute(
        "DELETE FROM chat_subs WHERE chat_id = :cid AND yt_channel_id = :ch_id",
        cid=chat_id, ch_id=channel["id"],
    )
    if deleted == 0:
        await update.message.reply_text("❌ Nu ești abonat la acest canal în acest chat.")
        return

    logger.info("remove channel chat=%s yt_id=%s", chat_id, yt_id)
    await update.message.reply_text(f"✅ Canal eliminat: {channel['name'] or yt_id}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uptime = str(datetime.now(timezone.utc) - _startup_time).split(".")[0]
    total_videos = await fetch_value("SELECT COUNT(*) FROM videos WHERE summary IS NOT NULL")
    total_channels = await fetch_value("SELECT COUNT(*) FROM yt_channels")
    total_chats = await fetch_value("SELECT COUNT(*) FROM chats")
    await update.message.reply_text(
        f"📊 Status Pulse\n\n"
        f"⏱ Uptime: {uptime}\n"
        f"💬 Chat-uri active: {total_chats or 0}\n"
        f"📺 Canale urmărite: {total_channels or 0}\n"
        f"🎬 Videoclipuri procesate: {total_videos or 0}\n"
        f"🔄 Interval poll: {settings.poll_interval_minutes} minute"
    )


# ---------------------------------------------------------------------------
# Message handler — video link → instant summary
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any text message. If it contains a YouTube video URL, summarize it."""
    await _register_chat(update)
    text = update.message.text or ""
    video_id = extract_video_id(text)
    if not video_id:
        return

    await update.message.reply_text("⏳ Extrag transcriptul și generez rezumatul...")

    existing = await fetch_one(
        "SELECT title, summary FROM videos WHERE yt_id = :vid",
        vid=video_id,
    )
    if existing and existing["summary"]:
        title_line = f"*{existing['title']}*\n\n" if existing.get("title") else ""
        await update.message.reply_text(
            f"🎬 {title_line}{existing['summary']}\n\n🔗 https://youtube.com/watch?v={video_id}",
            parse_mode="Markdown",
        )
        logger.info("handle_message cache hit video=%s", video_id)
        return

    transcript = await get_transcript(video_id)
    if not transcript:
        await update.message.reply_text(
            "❌ Nu am putut extrage transcriptul acestui video.\n"
            "Posibil: subtitrări dezactivate sau video privat."
        )
        logger.warning("handle_message no transcript video=%s", video_id)
        return

    summary = await summarize(transcript)
    if not summary:
        await update.message.reply_text("❌ Nu am putut genera rezumatul. Încearcă din nou.")
        logger.warning("handle_message no summary video=%s", video_id)
        return

    from pulse.youtube import get_video_title
    title = await get_video_title(video_id)
    title_line = f"*{title}*\n\n" if title else ""

    await update.message.reply_text(
        f"🎬 {title_line}{summary}\n\n🔗 https://youtube.com/watch?v={video_id}",
        parse_mode="Markdown",
    )

    await execute(
        """
        INSERT INTO videos (yt_id, title, transcript, summary, processed_at)
        VALUES (:vid, :title, :transcript, :summary, now())
        ON CONFLICT (yt_id) DO UPDATE
            SET transcript   = EXCLUDED.transcript,
                summary      = EXCLUDED.summary,
                title        = EXCLUDED.title,
                processed_at = EXCLUDED.processed_at
        """,
        vid=video_id, title=title, transcript=transcript, summary=summary,
    )
    logger.info("handle_message summary sent video=%s", video_id)


# ---------------------------------------------------------------------------
# App builder
# ---------------------------------------------------------------------------

def build_app(bot_token: str):
    """Build and return the configured Telegram Application."""
    app = ApplicationBuilder().token(bot_token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("sources", cmd_sources))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app
