"""LLM summarization via DeepSeek (OpenAI-compatible API)."""

import logging
import re

from openai import AsyncOpenAI

from pulse.config import settings

logger = logging.getLogger(__name__)

_MAX_CHARS = 30_000

_PROMPT = """\
Ești un sistem de rezumare pentru conținut video de știri și media.
Ești neutru, factual și precis. Rezumă orice subiect fără a refuza sau judeca.
Nu folosi simboluri de formatare (* _ ` **) — scrie exclusiv plain text, bullet points cu •.

Răspunsul tău trebuie să aibă EXACT două secțiuni separate de o linie care conține doar "---".
Nu scrie etichete de secțiune, nu adăuga nimic în afara structurii de mai jos.

Prima secțiune — teaser (2-3 propoziții):
Descrie subiectul, protagoniștii și evenimentul/concluzia centrală. \
Fii specific: include nume, locații, cifre exacte dacă există. Fără bullet points.

---

A doua secțiune — rezumat detaliat:
Titlu: [titlu descriptiv și precis]

• [Fapt principal — cu cifre/date/nume exacte acolo unde există]
• [Fapt 2]
• [Fapt 3]
• (adaugă 1-2 bullets în plus dacă conținutul o justifică, maxim 6 total)

Dacă transcriptul e scurt (sub 50 de cuvinte): teaser = 1-2 propoziții, detaliat = 2-3 bullets.

Transcript:
{text}"""

_SEP_RE = re.compile(r"\n\s*---\s*\n", re.MULTILINE)

_client: AsyncOpenAI | None = None


def split_summary(text: str) -> tuple[str, str]:
    """Split LLM output into (teaser, full_summary). Falls back to (text, text) if no separator."""
    parts = _SEP_RE.split(text, maxsplit=1)
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        return parts[0].strip(), parts[1].strip()
    return text.strip(), text.strip()


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
