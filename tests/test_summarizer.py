"""Tests for SummarizerService — DB interaction, LLM calls, edge cases."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pulse.llm.base import AbstractLLMClient
from pulse.processing.summarizer import SummarizerService


def _make_mock_session(item: MagicMock | None) -> AsyncMock:
    """Build an AsyncSession mock that returns `item` on scalar_one_or_none()."""
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=item))
    )
    return session


def _make_mock_llm(short: str = "Short.", full: str = "Full.") -> AbstractLLMClient:
    """Build an AbstractLLMClient mock that returns fixed summaries."""
    llm = AsyncMock(spec=AbstractLLMClient)
    llm.summarize = AsyncMock(side_effect=lambda text, mode: short if mode == "short" else full)
    return llm


# --- happy path ---

@pytest.mark.asyncio
async def test_summarize_content_sets_both_summaries() -> None:
    llm = _make_mock_llm(short="**Titlu**\nRezumat scurt.", full="Rezumat complet.\n- Punct 1")
    service = SummarizerService(llm)

    item = MagicMock()
    item.raw_transcript = "Acesta este transcriptul video-ului."
    item.summary_short = None
    item.summary_full = None
    item.processed_at = None

    session = _make_mock_session(item)
    await service.summarize_content(uuid.uuid4(), session)

    assert item.summary_short == "**Titlu**\nRezumat scurt."
    assert item.summary_full == "Rezumat complet.\n- Punct 1"
    assert item.processed_at is not None
    assert isinstance(item.processed_at, datetime)


@pytest.mark.asyncio
async def test_summarize_content_calls_llm_twice() -> None:
    llm = _make_mock_llm()
    service = SummarizerService(llm)

    item = MagicMock()
    item.raw_transcript = "Text de test."

    session = _make_mock_session(item)
    await service.summarize_content(uuid.uuid4(), session)

    assert llm.summarize.call_count == 2
    modes = {call.kwargs["mode"] for call in llm.summarize.call_args_list}
    assert modes == {"short", "full"}


# --- empty transcript ---

@pytest.mark.asyncio
async def test_summarize_content_skips_empty_transcript() -> None:
    llm = _make_mock_llm()
    service = SummarizerService(llm)

    item = MagicMock()
    item.raw_transcript = None

    session = _make_mock_session(item)
    await service.summarize_content(uuid.uuid4(), session)

    llm.summarize.assert_not_called()


@pytest.mark.asyncio
async def test_summarize_content_skips_whitespace_only_transcript() -> None:
    llm = _make_mock_llm()
    service = SummarizerService(llm)

    item = MagicMock()
    item.raw_transcript = ""

    session = _make_mock_session(item)
    await service.summarize_content(uuid.uuid4(), session)

    llm.summarize.assert_not_called()


# --- item not found ---

@pytest.mark.asyncio
async def test_summarize_content_handles_missing_item() -> None:
    llm = _make_mock_llm()
    service = SummarizerService(llm)

    session = _make_mock_session(None)
    await service.summarize_content(uuid.uuid4(), session)

    llm.summarize.assert_not_called()


# --- LLM error propagation ---

@pytest.mark.asyncio
async def test_summarize_content_propagates_llm_error() -> None:
    llm = AsyncMock(spec=AbstractLLMClient)
    llm.summarize = AsyncMock(side_effect=RuntimeError("DeepSeek unavailable"))
    service = SummarizerService(llm)

    item = MagicMock()
    item.raw_transcript = "Text valid."

    session = _make_mock_session(item)
    with pytest.raises(RuntimeError, match="DeepSeek unavailable"):
        await service.summarize_content(uuid.uuid4(), session)
