"""YouTube helpers — channel resolution, new video detection, transcript extraction."""

import asyncio
import logging
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone

import yt_dlp
from googleapiclient.discovery import build

from pulse.config import settings

logger = logging.getLogger(__name__)

_WATCH_URL = "https://www.youtube.com/watch?v="
_PLAYLIST_MAX = 10
_PREFERRED_LANGS = ["ro", "en", "ro-RO", "en-US"]

_CHANNEL_RE = re.compile(
    r"youtube\.com/(?:@([A-Za-z0-9_.\-]+)|c/([A-Za-z0-9_.\-]+)|channel/(UC[A-Za-z0-9_\-]+))"
)
_VIDEO_RE = [
    re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})"),
    re.compile(r"youtube\.com/(?:shorts|live|embed)/([A-Za-z0-9_-]{11})"),
]

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_yt_client = None
_whisper_model = None


def _yt():
    global _yt_client
    if _yt_client is None:
        _yt_client = build("youtube", "v3", developerKey=settings.youtube_api_key, cache_discovery=False)
    return _yt_client


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        logger.info("loading whisper model...")
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
        logger.info("whisper model loaded")
    return _whisper_model


def is_video_url(url: str) -> bool:
    """True if URL points to a single video (not a channel)."""
    return any(sig in url for sig in ("watch?v=", "youtu.be/", "/shorts/", "/live/"))


def extract_video_id(url: str) -> str | None:
    """Extract 11-char YouTube video ID from any supported URL format."""
    for pattern in _VIDEO_RE:
        m = pattern.search(url)
        if m:
            return m.group(1)
    return None


async def resolve_channel(url: str) -> tuple[str, str] | None:
    """Return (yt_channel_id, display_name) for a channel URL. Returns None on failure."""
    m = _CHANNEL_RE.search(url)
    if not m:
        return None
    handle, c_name, channel_id = m.group(1), m.group(2), m.group(3)
    kwargs = (
        {"id": channel_id}
        if channel_id
        else {"forHandle": f"@{(handle or c_name or '').lstrip('@')}"}
    )
    loop = asyncio.get_event_loop()
    try:
        resp = await loop.run_in_executor(
            None, lambda: _yt().channels().list(part="snippet", **kwargs).execute()
        )
        items = resp.get("items", [])
        if not items:
            return None
        return items[0]["id"], items[0]["snippet"]["title"]
    except Exception as exc:
        logger.error("resolve_channel failed url=%s error=%s", url, exc)
        return None


async def fetch_recent_videos(yt_channel_id: str) -> list[dict]:
    """Return metadata of the most recent videos on the channel (newest first). Empty list on failure."""
    if not yt_channel_id.startswith("UC"):
        logger.error("fetch_recent_videos bad channel_id=%s", yt_channel_id)
        return []
    playlist_id = "UU" + yt_channel_id[2:]
    loop = asyncio.get_event_loop()
    try:
        resp = await loop.run_in_executor(
            None,
            lambda: _yt().playlistItems().list(
                part="snippet", playlistId=playlist_id, maxResults=_PLAYLIST_MAX
            ).execute(),
        )
    except Exception as exc:
        logger.error("fetch_recent_videos failed channel=%s error=%s", yt_channel_id, exc)
        return []

    results = []
    for item in resp.get("items", []):
        snip = item["snippet"]
        vid = snip.get("resourceId", {}).get("videoId")
        if not vid:
            continue
        published_raw = snip.get("publishedAt")
        published_at = None
        if published_raw:
            try:
                published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
            except ValueError:
                pass
        results.append({"video_id": vid, "title": snip.get("title"), "published_at": published_at})
    return results


async def get_video_title(video_id: str) -> str | None:
    """Fetch video title via YouTube Data API. Returns None on failure."""
    loop = asyncio.get_event_loop()
    try:
        resp = await loop.run_in_executor(
            None,
            lambda: _yt().videos().list(part="snippet", id=video_id).execute(),
        )
        items = resp.get("items", [])
        if not items:
            return None
        return items[0]["snippet"]["title"]
    except Exception as exc:
        logger.error("get_video_title failed video=%s error=%s", video_id, exc)
        return None


async def get_transcript(video_id: str) -> str | None:
    """Try YouTube captions first, fall back to local Whisper transcription."""
    text = await _transcript_via_api(video_id)
    if text:
        return text
    logger.info("get_transcript no captions, using whisper video=%s", video_id)
    return await _transcript_via_whisper(video_id)


async def _transcript_via_api(video_id: str) -> str | None:
    """Fetch captions via youtube-transcript-api. Returns None if unavailable."""
    import http.cookiejar
    import requests
    from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi

    loop = asyncio.get_event_loop()
    session = requests.Session()
    session.headers.update({"User-Agent": _BROWSER_UA})

    cookies_file = settings.youtube_cookies_file
    if cookies_file and os.path.isfile(cookies_file):
        jar = http.cookiejar.MozillaCookieJar(cookies_file)
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
            session.cookies = jar
        except Exception as exc:
            logger.warning("_transcript_via_api failed loading cookies error=%s", exc)

    try:
        api = YouTubeTranscriptApi(http_client=session)
        transcript = await loop.run_in_executor(
            None, lambda: api.fetch(video_id, languages=_PREFERRED_LANGS)
        )
        snippets = getattr(transcript, "snippets", None) or list(transcript)
        text = " ".join(
            (s.text if hasattr(s, "text") else s["text"]) for s in snippets
        ).strip()
        return text or None
    except (NoTranscriptFound, TranscriptsDisabled):
        logger.info("_transcript_via_api no captions video=%s", video_id)
        return None
    except Exception as exc:
        logger.warning("_transcript_via_api failed video=%s error=%s", video_id, exc)
        return None


async def _download_audio(video_id: str, tmpdir: str) -> str | None:
    """Download best-quality audio stream to tmpdir. Returns file path or None."""
    loop = asyncio.get_event_loop()
    opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{tmpdir}/%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
    }
    cookies_file = settings.youtube_cookies_file
    if cookies_file and os.path.isfile(cookies_file):
        opts["cookiefile"] = cookies_file

    def _do_download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(f"{_WATCH_URL}{video_id}", download=True)
        files = os.listdir(tmpdir)
        return f"{tmpdir}/{files[0]}" if files else None

    try:
        return await loop.run_in_executor(None, _do_download)
    except Exception as exc:
        logger.warning("_download_audio failed video=%s error=%s", video_id, exc)
        return None


async def _transcript_via_whisper(video_id: str) -> str | None:
    """Download audio and transcribe locally with faster-whisper. No external API calls."""
    tmpdir = tempfile.mkdtemp()
    try:
        audio_file = await _download_audio(video_id, tmpdir)
        if not audio_file:
            logger.warning("_transcript_via_whisper no audio downloaded video=%s", video_id)
            return None

        loop = asyncio.get_event_loop()

        def _transcribe():
            model = _get_whisper()
            segments, info = model.transcribe(audio_file, beam_size=5)
            text = " ".join(s.text.strip() for s in segments).strip()
            logger.info("whisper transcribed video=%s lang=%s chars=%d", video_id, info.language, len(text))
            return text or None

        return await loop.run_in_executor(None, _transcribe)
    except Exception as exc:
        logger.warning("_transcript_via_whisper failed video=%s error=%s", video_id, exc)
        return None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
