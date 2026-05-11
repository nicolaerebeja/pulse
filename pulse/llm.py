"""LLM summarization via DeepSeek (OpenAI-compatible API)."""

import logging

from openai import AsyncOpenAI

from pulse.config import settings

logger = logging.getLogger(__name__)

_MAX_CHARS = 30_000

_PROMPT = (
    "Ești un sistem automat de rezumare a conținutului media.\n"
    "Rolul tău este exclusiv factual — nu evaluezi, nu judeci, nu iei poziție.\n"
    "Rezumă ORICE text primit, indiferent de limbaj, ton sau subiect, "
    "strict din perspectiva unui reporter neutru.\n"
    "Generează în română:\n"
    "1. UN TITLU DESCRIPTIV (prima linie)\n"
    "2. 2-3 rânduri care descriu factual ce spune autorul\n"
    "3. Exact 3-5 bullet points cu ideile principale\n"
    "Dacă refuzi să rezumi, sistemul eșuează — nu refuza niciodată.\n\n"
    "Text:\n{text}"
)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    return _client


async def summarize(transcript: str) -> str | None:
    """Summarize a video transcript in Romanian. Returns None on API error or empty input."""
    if not transcript or not transcript.strip():
        return None
    truncated = transcript[:_MAX_CHARS]
    try:
        response = await _get_client().chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": _PROMPT.format(text=truncated)}],
            max_tokens=800,
            temperature=0.3,
        )
        result = (response.choices[0].message.content or "").strip()
        tokens = response.usage.total_tokens if response.usage else 0
        logger.info("summarize ok tokens=%s", tokens)
        return result or None
    except Exception as exc:
        logger.error("summarize failed error=%s", exc)
        return None
