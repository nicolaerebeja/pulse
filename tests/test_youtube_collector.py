"""Tests for YouTube collector — URL parsing and deduplication logic."""

from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from pulse.collectors.url_ingester import extract_video_id, URLIngester


# --- URL parsing ---

@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s", "dQw4w9WgXcQ"),
    ("https://example.com/video", None),
    ("not-a-url", None),
    ("", None),
])
def test_extract_video_id(url: str, expected: str | None) -> None:
    assert extract_video_id(url) == expected


def test_ingest_raises_on_invalid_url() -> None:
    from pulse.collectors.url_ingester import URLIngester
    import asyncio

    ingester = URLIngester()
    with pytest.raises(ValueError, match="URL nu conține un ID YouTube valid"):
        asyncio.get_event_loop().run_until_complete(
            ingester.ingest("https://example.com/not-youtube", uuid.uuid4())
        )


# --- YouTubeCollector internals ---

def test_uploads_playlist_id_from_channel_id() -> None:
    from pulse.collectors.youtube import YouTubeCollector

    with patch("pulse.collectors.youtube.build") as mock_build:
        mock_build.return_value = MagicMock()
        collector = YouTubeCollector()

    assert collector._uploads_playlist_id("UCxxxxxx12345678") == "UUxxxxxx12345678"


def test_uploads_playlist_id_invalid_raises() -> None:
    from pulse.collectors.youtube import YouTubeCollector

    with patch("pulse.collectors.youtube.build") as mock_build:
        mock_build.return_value = MagicMock()
        collector = YouTubeCollector()

    with pytest.raises(ValueError, match="Cannot derive"):
        collector._uploads_playlist_id("CUSTOM_CHANNEL_NAME")


# --- collect() with mocked YouTube API ---

@pytest.mark.asyncio
async def test_collect_returns_items_for_active_sources() -> None:
    from pulse.collectors.youtube import YouTubeCollector

    source_id = uuid.uuid4()
    user_id = uuid.uuid4()

    fake_source = MagicMock()
    fake_source.id = source_id
    fake_source.external_id = "UCtest1234567890"

    fake_playlist_response = {
        "items": [
            {
                "snippet": {
                    "resourceId": {"videoId": "vid001"},
                    "title": "Test Video",
                    "publishedAt": "2026-05-06T10:00:00Z",
                }
            }
        ]
    }

    with patch("pulse.collectors.youtube.build") as mock_build:
        mock_yt = MagicMock()
        mock_yt.playlistItems().list().execute.return_value = fake_playlist_response
        mock_build.return_value = mock_yt

        collector = YouTubeCollector()

        with patch("pulse.collectors.youtube.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[fake_source])))))
            mock_factory.return_value = mock_session

            with patch.object(collector, "_get_transcript", return_value=("Test transcript", "en")):
                items = await collector.collect(user_id)

    assert len(items) == 1
    assert items[0]["external_content_id"] == "vid001"
    assert items[0]["platform"] == "youtube"
    assert items[0]["source_id"] == source_id
    assert items[0]["is_one_shot"] is False
    assert items[0]["raw_transcript"] == "Test transcript"


# --- Deduplication ---

@pytest.mark.asyncio
async def test_run_once_uses_on_conflict_do_nothing() -> None:
    """Verify that run_once calls pg_insert with on_conflict_do_nothing."""
    from pulse.collectors.youtube import YouTubeCollector

    user_id = uuid.uuid4()

    fake_item = {
        "source_id": uuid.uuid4(),
        "user_id": user_id,
        "platform": "youtube",
        "external_content_id": "vid_dup",
        "title": "Dup Video",
        "original_url": "https://www.youtube.com/watch?v=vid_dup",
        "raw_transcript": "text",
        "language_detected": "en",
        "published_at": None,
        "is_one_shot": False,
    }

    with patch("pulse.collectors.youtube.build") as mock_build:
        mock_build.return_value = MagicMock()
        collector = YouTubeCollector()

        with patch.object(collector, "collect", return_value=[fake_item]):
            with patch("pulse.collectors.youtube.async_session_factory") as mock_factory:
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=False)
                mock_session.execute = AsyncMock()
                mock_session.commit = AsyncMock()
                mock_factory.return_value = mock_session

                with patch("pulse.collectors.youtube.pg_insert") as mock_pg_insert:
                    mock_stmt = MagicMock()
                    mock_pg_insert.return_value.values.return_value.on_conflict_do_nothing.return_value = mock_stmt

                    await collector.run_once(user_id)

                    mock_pg_insert.assert_called_once()
                    mock_pg_insert.return_value.values.return_value.on_conflict_do_nothing.assert_called_once_with(
                        index_elements=["user_id", "platform", "external_content_id"]
                    )
