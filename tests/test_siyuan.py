"""Tests for SiYuan API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from pulse.siyuan.client import SiYuanClient


def test_client_initialization() -> None:
    client = SiYuanClient()
    assert client._base_url == "https://note.rebdev.online"
    assert "Authorization" in client._headers
    assert "Content-Type" in client._headers


@pytest.mark.asyncio
async def test_create_note_returns_block_id(siyuan_success_response: dict) -> None:
    client = SiYuanClient()

    mock_response = MagicMock()
    mock_response.json.return_value = siyuan_success_response
    mock_response.raise_for_status = MagicMock()

    with patch("pulse.siyuan.client.httpx.AsyncClient") as MockClient:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("pulse.siyuan.client.settings") as mock_settings:
            mock_settings.siyuan_token = "test-token"
            mock_settings.siyuan_api_url = "https://note.rebdev.online"
            result = await client.create_note("Test Title", "Test Content", "parent-123")

    assert result == "test-block-id-abc123"


@pytest.mark.asyncio
async def test_create_note_raises_on_http_error() -> None:
    client = SiYuanClient()

    with patch("pulse.siyuan.client.httpx.AsyncClient") as MockClient:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(side_effect=httpx.HTTPError("Connection refused"))
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("pulse.siyuan.client.settings") as mock_settings:
            mock_settings.siyuan_token = "test-token"
            mock_settings.siyuan_api_url = "https://note.rebdev.online"
            with pytest.raises(httpx.HTTPError):
                await client.create_note("Title", "Content", "parent-id")


@pytest.mark.asyncio
async def test_create_note_skips_when_no_token() -> None:
    client = SiYuanClient()

    with patch("pulse.siyuan.client.settings") as mock_settings:
        mock_settings.siyuan_token = ""
        result = await client.create_note("Title", "Content", "parent-id")

    assert result == ""


@pytest.mark.asyncio
async def test_append_to_note_skips_when_no_token() -> None:
    client = SiYuanClient()

    with patch("pulse.siyuan.client.settings") as mock_settings:
        mock_settings.siyuan_token = ""
        await client.append_to_note("parent-id", "content")