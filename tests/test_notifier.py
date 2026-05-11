"""Tests for NotifierService — deduplication, missing telegram_id, send_message mock."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pulse.bot.notifier import NotifierService


def _make_user(telegram_id: int | None = 123456789) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.telegram_id = telegram_id
    return u


def _make_content_item(user_id: uuid.UUID, summary_short: str = "Rezumat scurt.") -> MagicMock:
    item = MagicMock()
    item.id = uuid.uuid4()
    item.user_id = user_id
    item.summary_short = summary_short
    item.summary_full = "Rezumat complet."
    item.title = "Test Video"
    item.original_url = "https://www.youtube.com/watch?v=testid"
    item.source_id = None
    return item


def _make_db(user=None, item=None, existing_log=None) -> AsyncMock:
    """Build a mock AsyncSession for NotifierService tests."""
    session = AsyncMock()

    query_results = [user, item]
    scalar_results = [existing_log]

    call_count = {"execute": 0, "scalar": 0}

    async def mock_execute(stmt):
        idx = call_count["execute"]
        call_count["execute"] += 1
        val = query_results[idx] if idx < len(query_results) else None
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=val)
        return result

    async def mock_scalar(stmt):
        idx = call_count["scalar"]
        call_count["scalar"] += 1
        return scalar_results[idx] if idx < len(scalar_results) else None

    session.execute = mock_execute
    session.scalar = mock_scalar
    session.add = MagicMock()
    return session


# --- deduplication ---

@pytest.mark.asyncio
async def test_notify_returns_false_when_already_sent() -> None:
    user = _make_user()
    item = _make_content_item(user.id)
    existing_log = MagicMock()  # simulates an existing notification_log entry

    db = _make_db(user=user, item=item, existing_log=existing_log)

    mock_app = MagicMock()
    mock_app.bot.send_message = AsyncMock()

    with patch("pulse.bot.notifier.get_bot", return_value=mock_app.bot):
        service = NotifierService()
        result = await service.notify_user(user.id, item.id, db)

    assert result is False
    mock_app.bot.send_message.assert_not_called()


# --- user without telegram_id ---

@pytest.mark.asyncio
async def test_notify_returns_false_when_no_telegram_id() -> None:
    user = _make_user(telegram_id=None)
    item = _make_content_item(user.id)
    db = _make_db(user=user, item=item)

    mock_app = MagicMock()
    mock_app.bot.send_message = AsyncMock()

    with patch("pulse.bot.notifier.get_bot", return_value=mock_app.bot):
        service = NotifierService()
        result = await service.notify_user(user.id, item.id, db)

    assert result is False
    mock_app.bot.send_message.assert_not_called()


# --- bot not running ---

@pytest.mark.asyncio
async def test_notify_returns_false_when_bot_not_running() -> None:
    user = _make_user()
    item = _make_content_item(user.id)
    db = _make_db(user=user, item=item)

    with patch("pulse.bot.notifier.get_bot", return_value=None):
        service = NotifierService()
        result = await service.notify_user(user.id, item.id, db)

    assert result is False


# --- happy path ---

@pytest.mark.asyncio
async def test_notify_sends_message_and_logs_notification() -> None:
    user = _make_user()
    item = _make_content_item(user.id)
    db = _make_db(user=user, item=item, existing_log=None)

    mock_app = MagicMock()
    mock_app.bot.send_message = AsyncMock()

    with patch("pulse.bot.notifier.get_bot", return_value=mock_app.bot):
        service = NotifierService()
        result = await service.notify_user(user.id, item.id, db)

    assert result is True
    mock_app.bot.send_message.assert_called_once()
    call_kwargs = mock_app.bot.send_message.call_args.kwargs
    assert call_kwargs["chat_id"] == user.telegram_id
    assert "Rezumat scurt." in call_kwargs["text"]
    db.add.assert_called_once()
