"""Telegram bot — all command and message handlers in one file."""

import logging
from datetime import datetime, timedelta, timezone
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from pulse.config import settings
from pulse.db import execute, fetch_all, fetch_one, fetch_value
from pulse.llm import split_summary, summarize
from pulse.youtube import extract_video_id, get_transcript, is_video_url, resolve_channel

logger = logging.getLogger(__name__)

_startup_time: datetime = datetime.now(timezone.utc)


def _rel_time(dt: datetime | None) -> str:
    """Return human-readable relative time: 'acum 3 min', 'acum 2h 15min', or absolute date."""
    if not dt:
        return "—"
    diff = datetime.now(timezone.utc) - dt
    total_minutes = int(diff.total_seconds() // 60)
    if total_minutes < 1:
        return "acum"
    if total_minutes < 60:
        return f"acum {total_minutes} min"
    hours = total_minutes // 60
    mins = total_minutes % 60
    if hours < 24:
        return f"acum {hours}h {mins}min" if mins else f"acum {hours}h"
    return dt.strftime("%d %b %H:%M UTC")


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
        "👋 <b>Bun venit în Pulse!</b>\n\n"
        "Ce fac:\n"
        "• Monitorizez canale YouTube și îți trimit automat rezumat pentru fiecare video nou\n"
        "• La link direct de video, generez rezumatul în câteva secunde\n\n"
        "Cum începi:\n"
        f"<code>/add https://youtube.com/@numecanal</code>\n\n"
        f"Verificare automată la fiecare {settings.poll_interval_minutes} minute.\n"
        "/help — toate comenzile",
        parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 <b>Comenzi Pulse</b>\n\n"
        "/add <code>&lt;url_canal&gt;</code> — abonează-te la un canal YouTube\n"
        "    Ex: <code>/add https://youtube.com/@Reuters</code>\n\n"
        "/sources — canalele urmărite în acest chat, cu statistici\n\n"
        "/remove <code>&lt;nume_sau_id&gt;</code> — șterge un abonament\n"
        "    Ex: <code>/remove Reuters</code>\n\n"
        "/status — starea botului, scheduler, activitate per canal\n\n"
        "🔗 <b>Link video YouTube</b> direct în chat → rezumat instant (teaser + buton detalii)",
        parse_mode="HTML",
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
        f"✅ Canal adăugat: <b>{escape(name)}</b>\n\nPrima verificare în maxim {settings.poll_interval_minutes} minute.",
        parse_mode="HTML",
    )


async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _register_chat(update)
    chat_id = update.effective_chat.id
    rows = await fetch_all(
        """
        SELECT yc.yt_id, yc.name, yc.checked_at,
               COUNT(v.id)        AS video_count,
               MAX(v.processed_at) AS last_video_at
          FROM yt_channels yc
          JOIN chat_subs cs ON cs.yt_channel_id = yc.id
          LEFT JOIN videos v ON v.yt_channel_id = yc.id
         WHERE cs.chat_id = :cid
         GROUP BY yc.id, yc.yt_id, yc.name, yc.checked_at
         ORDER BY yc.name
        """,
        cid=chat_id,
    )
    if not rows:
        await update.message.reply_text(
            "Nu urmărești niciun canal.\n"
            "Adaugă unul cu: <code>/add https://youtube.com/@numecanal</code>",
            parse_mode="HTML",
        )
        return

    lines = [f"📋 <b>Canale urmărite</b> ({len(rows)} total)\n"]
    for row in rows:
        name = escape(row["name"] or row["yt_id"])
        yt_id = escape(row["yt_id"])
        checked = _rel_time(row["checked_at"])
        last_vid = _rel_time(row["last_video_at"]) if row["last_video_at"] else "—"
        count = row["video_count"] or 0
        lines.append(
            f"🎬 <b>{name}</b>\n"
            f"   ID: <code>{yt_id}</code>\n"
            f"   Verificat: {checked} | Ultimul video: {last_vid} | {count} procesate"
        )
    await update.message.reply_text("\n\n".join(lines), parse_mode="HTML")


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _register_chat(update)
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Utilizare: <code>/remove &lt;nume_sau_id&gt;</code>\n"
            "Ex: <code>/remove Reuters</code>\nVezi canalele cu /sources.",
            parse_mode="HTML",
        )
        return

    query = " ".join(args)
    chat_id = update.effective_chat.id

    channel = await fetch_one(
        "SELECT id, name, yt_id FROM yt_channels WHERE yt_id = :q OR lower(name) = lower(:q)",
        q=query,
    )
    if not channel:
        await update.message.reply_text("❌ Canal negăsit. Verifică cu /sources.")
        return

    deleted = await execute(
        "DELETE FROM chat_subs WHERE chat_id = :cid AND yt_channel_id = :ch_id",
        cid=chat_id, ch_id=channel["id"],
    )
    if deleted == 0:
        await update.message.reply_text("❌ Nu ești abonat la acest canal în acest chat.")
        return

    logger.info("remove channel chat=%s yt_id=%s", chat_id, channel["yt_id"])
    await update.message.reply_text(
        f"✅ <b>{escape(channel['name'] or channel['yt_id'])}</b> eliminat.",
        parse_mode="HTML",
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now(timezone.utc)

    # Uptime
    diff = now - _startup_time
    up_h = int(diff.total_seconds() // 3600)
    up_m = int((diff.total_seconds() % 3600) // 60)
    uptime_str = f"{up_h}h {up_m}min" if up_h else f"{up_m}min"

    # Next poll — APScheduler ticks at fixed offsets from startup time
    interval_s = settings.poll_interval_minutes * 60
    elapsed_s = diff.total_seconds()
    remaining_s = interval_s - (elapsed_s % interval_s)
    next_poll_str = f"~{int(remaining_s // 60)}min" if remaining_s > 60 else "imediat"

    # Global counts
    total_videos = await fetch_value("SELECT COUNT(*) FROM videos WHERE summary IS NOT NULL")
    total_chats = await fetch_value("SELECT COUNT(*) FROM chats")

    # Last poll across all channels
    last_poll = await fetch_value("SELECT MAX(checked_at) FROM yt_channels")

    # Per-channel breakdown
    channels = await fetch_all(
        """
        SELECT yc.name, yc.yt_id, yc.checked_at,
               COUNT(v.id)         AS video_count,
               MAX(v.processed_at) AS last_video_at
          FROM yt_channels yc
          LEFT JOIN videos v ON v.yt_channel_id = yc.id
         GROUP BY yc.id, yc.name, yc.yt_id, yc.checked_at
         ORDER BY yc.name
        """
    )

    lines = [
        "📊 <b>Pulse — Status</b>",
        "",
        f"⏱ Uptime: {uptime_str}",
        f"🔄 Poll interval: {settings.poll_interval_minutes} min",
        f"🕐 Ultima verificare: {_rel_time(last_poll)}",
        f"⏭ Urmăroarea verificare: {next_poll_str}",
        "",
        f"💬 Chat-uri active: {total_chats or 0}",
        f"📺 Canale monitorizate: {len(channels)}",
        f"🎬 Videoclipuri procesate total: {total_videos or 0}",
    ]

    if channels:
        lines.append("")
        lines.append("📋 <b>Activitate per canal:</b>")
        for ch in channels:
            name = escape(ch["name"] or ch["yt_id"])
            checked = _rel_time(ch["checked_at"])
            last_vid = _rel_time(ch["last_video_at"]) if ch["last_video_at"] else "niciunul încă"
            count = ch["video_count"] or 0
            lines.append(
                f"\n• <b>{name}</b>\n"
                f"  Verificat: {checked}\n"
                f"  Ultimul video procesat: {last_vid}\n"
                f"  Total procesate: {count}"
            )

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


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
        teaser, _full = split_summary(existing["summary"])
        title_line = f"<b>{escape(existing['title'])}</b>\n\n" if existing.get("title") else ""
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📖 Rezumat complet", callback_data=f"full:{video_id}")
        ]])
        await update.message.reply_text(
            f"🎬 {title_line}{escape(teaser)}\n\n🔗 https://youtube.com/watch?v={video_id}",
            parse_mode="HTML",
            reply_markup=keyboard,
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
    teaser, _full = split_summary(summary)
    title_line = f"<b>{escape(title)}</b>\n\n" if title else ""
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📖 Rezumat complet", callback_data=f"full:{video_id}")
    ]])
    await update.message.reply_text(
        f"🎬 {title_line}{escape(teaser)}\n\n🔗 https://youtube.com/watch?v={video_id}",
        parse_mode="HTML",
        reply_markup=keyboard,
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

async def show_full_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback: expand notification to full summary when user taps the button."""
    query = update.callback_query
    await query.answer()

    video_id = query.data.split(":", 1)[1]
    video = await fetch_one("SELECT title, summary FROM videos WHERE yt_id = :vid", vid=video_id)
    if not video or not video["summary"]:
        await query.answer("Rezumatul nu mai este disponibil.", show_alert=True)
        return

    _teaser, full = split_summary(video["summary"])
    title_line = f"<b>{escape(video['title'])}</b>\n\n" if video.get("title") else ""
    await query.edit_message_text(
        f"🎬 {title_line}{escape(full)}\n\n🔗 https://youtube.com/watch?v={video_id}",
        parse_mode="HTML",
    )
    logger.info("show_full_summary video=%s", video_id)


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("handler exception update=%s error=%s", update, context.error, exc_info=context.error)


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
    app.add_handler(CallbackQueryHandler(show_full_summary, pattern=r"^full:"))
    app.add_error_handler(_error_handler)
    return app
