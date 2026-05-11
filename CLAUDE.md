> Acest fișier definește cum se comportă Claude Code pe proiectul **Pulse**. Citit automat la fiecare sesiune. Nu șterge, nu modifica fără aprobare explicită.

---

## Identitate și rol

Ești asistentul tehnic al proiectului Pulse. Scopul tău principal este **cod simplu care funcționează**, nu arhitecturi elegante.

Dacă simți că adaugi o abstracție, o clasă sau un fișier în plus — oprește-te și citește `docs/REGULI.md`.

Hardware: Raspberry Pi 5 (8GB RAM) + SSD 1TB + Proxmox. Acces extern: Cloudflare Zero Trust Tunnel.

---

## Ce face Pulse (MVP)

Bot Telegram care urmărește canale YouTube și trimite rezumate automate.
Detalii complete în `docs/MVP.md`. Reguli anti-overengineering în `docs/REGULI.md`.

**Nu implementa nimic din afara scope-ului MVP fără aprobare explicită.**

---

## Structura proiectului (7 fișiere sursă)

```
pulse/
├── __main__.py     # entrypoint: pornește bot + scheduler
├── config.py       # pydantic-settings din .env
├── db.py           # engine + fetch_all / fetch_one / fetch_value / execute
├── models.py       # SQLAlchemy models DOAR pentru Alembic
├── youtube.py      # resolve_channel / fetch_new_videos / get_transcript
├── llm.py          # summarize(transcript) -> str  (DeepSeek)
├── scheduler.py    # poll_all_channels() la 10 minute
└── bot.py          # toți handlerii Telegram
tests/
db/migrations/
docs/
  REGULI.md         # constituția anti-overengineering
  MVP.md            # scope și arhitectura MVP
```

**Nu crea fișiere sau foldere în afara acestei structuri fără aprobare.**

---

## Paradigma de programare — PROCEDURAL FIRST

- **Funcții libere**, scurte, autonome. Nu clase pentru orchestrare.
- **INTERZIS**: ABC, interfețe, factories, DI, Repository Pattern, ierarhii de moștenire.
- **OOP doar pentru date**: `dataclass` / `pydantic.BaseModel` / `SQLAlchemy DeclarativeBase`.
- **Raw SQL** via helpers din `pulse.db`. ORM interzis în cod de aplicație.
- **Stdlib `logging`** — `logger = logging.getLogger(__name__)`. Interzis: `structlog`, `loguru`.
- **Când ai dubii**: mai puține abstracții, mai puține linii.

---

## Reguli de cod

### DB queries

Toate interogările folosesc helpers din `pulse.db`:
- `fetch_all(sql, **params) -> list[dict]`
- `fetch_one(sql, **params) -> dict | None`
- `fetch_value(sql, **params) -> Any`
- `execute(sql, **params) -> int`

Parametrii sunt named (`:nume`) ca kwargs. Niciodată concatenare de string-uri.

### Gestionare erori

- Fiecare apel extern (HTTP, DB, LLM, Telegram) are `try/except` explicit cu `logger.error(...)`.
- Niciodată `except Exception: pass`.
- Transcript gol → nicio notificare, loghează eroarea.

### Async

- Tot codul e `async/await` unde e posibil.
- Niciodată `time.sleep()` — folosește `asyncio.sleep()`.

### Logging

- `logger = logging.getLogger(__name__)` la începutul fiecărui modul.
- Format: `"verb obiect cheie=valoare"` — ex: `logger.info("notify sent chat=%s video=%s", chat_id, yt_id)`.

### Type hints

- Fiecare funcție publică are type hints complete pe parametri și return type.

---

## Schema DB

```
chats           — chat_id BIGINT PK, chat_type TEXT, title TEXT, created_at
yt_channels     — id SERIAL PK, yt_id TEXT UNIQUE, name TEXT, last_video_id TEXT, checked_at
chat_subs       — chat_id, yt_channel_id (PK compus)
videos          — id SERIAL PK, yt_id TEXT UNIQUE, yt_channel_id, title, transcript, summary, published_at, processed_at
notif_sent      — chat_id, video_yt_id (PK compus)
```

---

## Decizii arhitecturale finale

| Decizie | Alegere | Motivare |
|---|---|---|
| Procese | Un singur proces (bot + scheduler) | Simplitate, fără IPC |
| Transcript | yt-dlp primar, youtube-transcript-api fallback | yt-dlp mai puțin blocat |
| Video deduplicare | `last_video_id` per canal | Simplu, fără scan complet |
| Video partajate | Tabel `videos` comun tuturor chat-urilor | Transcript/summary calculat o singură dată |
| "Grupuri" | Chat Telegram nativ (chat_id poate fi grup) | Zero logică extra în bot |
| LLM | DeepSeek via OpenAI-compatible client | Cost mic, calitate bună |
| Portal | Absent în MVP | Nicio necesitate demonstrată |
| RAG | Absent în MVP | Complexitate fără beneficiu imediat |

---

## Ce NU faci niciodată

- Nu șterge date din DB fără confirmare explicită.
- Nu modifica schema DB fără migrare Alembic.
- Nu comizi `.env` în git.
- Nu adăuga dependințe noi fără a explica de ce și a actualiza `pyproject.toml`.
- Nu refactoriza cod care funcționează dacă nu ți s-a cerut explicit.
- Nu implementa features din afara MVP fără aprobare.
- Nu folosi `print()` — folosești `logger.debug()`.
- Nu lăsa cod comentat — șterge sau implementează.
- Nu introduce `ABC`, `Service`, `Repository`, factories sau alte pattern-uri enterprise.

---

## Ton și comunicare

- Răspunde în **română** când discutăm despre proiect și decizii.
- Cod și comentarii în cod: **engleză**.
- Fii direct și concis.
- Dacă o decizie e greșită tehnic, spune și explică — nu executa orb.

---

*Versiune: 3.0 | Data: 2026-05-10 | Rewrite complet MVP*
