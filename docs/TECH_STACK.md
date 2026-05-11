---

## 1. Principii tehnice fundamentale

1. **Python only** — backend, bot, portal, scripts. Zero Node.js, zero Go, zero Rust.
2. **Un singur proces principal** pentru POC — FastAPI cu APScheduler embedded. Se separă pe măsură ce crește.
3. **Un singur serviciu de date** — PostgreSQL cu extensia pgvector. Nu Chroma, nu Pinecone, nu Redis separat.
4. **Cod curat și explicit** — fără magic, fără meta-programming excesiv. Un junior trebuie să înțeleagă orice fișier în \< 5 minute.
5. **Configurare prin environment** — toate secretele în `.env` via `pydantic-settings`. Zero hardcoding.
6. **Containerizat de la start** — Docker Compose pe RPi 5 și Proxmox.

---

## 2. Stack complet

### 2.1 Infrastructure

| Componentă         | Tehnologie                     | Versiune | Justificare                         |
| --------------------- | -------------------------------- | ---------- | ------------------------------------- |
| Hardware            | Raspberry Pi 5                 | 8GB RAM  | Dev + producție inițială         |
| Hardware alternativ | Proxmox (servere proprii)      | —       | Scale-up fără cost cloud          |
| OS                  | Raspberry Pi OS (Debian 12)    | Bookworm | Stabil, suport oficial              |
| Containerizare      | Docker + Docker Compose        | Latest   | Izolare servicii, reproducibilitate |
| Reverse proxy local | Caddy sau Nginx                | —       | HTTPS local, routing                |
| Acces extern        | Cloudflare Zero Trust + Tunnel | —       | Securitate, fără port forwarding  |

### 2.2 Backend

| Componentă     | Tehnologie        | Versiune | Justificare                           |
| ----------------- | ------------------- | ---------- | --------------------------------------- |
| Framework API   | FastAPI           | 0.115+   | Async nativ, auto-docs, tip safety    |
| ASGI server     | Uvicorn           | Latest   | Standard pentru FastAPI               |
| Scheduler       | APScheduler       | 4.x      | Embedded în FastAPI, simplu          |
| ORM             | SQLAlchemy        | 2.x      | Async, type-safe, migrări            |
| Migrări DB     | Alembic           | Latest   | Standard cu SQLAlchemy                |
| Validare config | pydantic-settings | 2.x      | `.env`→ obiect Python typed                |
| HTTP client     | httpx             | Latest   | Async, modern, înlocuiește requests |
| Logging         | structlog         | Latest   | JSON structurat, ușor de filtrat     |

### 2.3 Baza de date

| Componentă      | Tehnologie    | Justificare                                |
| ------------------ | --------------- | -------------------------------------------- |
| RDBMS            | PostgreSQL 16 | Stabil, extensibil, familiar               |
| Vector extension | pgvector      | RAG în același DB, zero serviciu extra   |
| Driver async     | asyncpg       | Performanță, compatibil SQLAlchemy async |

### 2.4 AI & ML

| Componentă               | Tehnologie             | Rulare           | Justificare                                          |
| --------------------------- | ------------------------ | ------------------ | ------------------------------------------------------ |
| LLM runtime local         | Ollama                 | RPi / Proxmox    | Simplu, API compatibil OpenAI                        |
| Model rezumare (POC)      | qwen                   |                  | Lightweight, multilingual, gratuit                   |
| Model embeddings          | nomic-embed-text       | Local via Ollama | Rapid, dimensiune mică (768d)                       |
| Transcriere audio         | faster-whisper         | Local            | Mai rapid decât Whisper original                    |
| Client LLM (abstractizat) | Custom`LLMClient`                 | —               | Swap facil între Ollama ↔ DeepSeek API ↔ Qwen API |
| **TBD**                          | DeepSeek V3 / Qwen API | Cloud            | Calitate mai bună când e nevoie                    |

### 2.5 Colectori

| Platformă           | Librărie principală    | Fallback / auxiliar            |
| ---------------------- | -------------------------- | -------------------------------- |
| YouTube (canale)     | google-api-python-client | yt-dlp (audio fallback)        |
| YouTube (transcript) | youtube-transcript-api   | faster-whisper via yt-dlp pipe |
| Twitch (events)      | TwitchIO                 | —                             |
| Twitch (audio)       | streamlink               | faster-whisper                 |
| Instagram (v2)       | Instaloader              | —                             |
| Facebook Pages (v2)  | facebook-scraper         | RSS via feedparser             |
| TikTok (v2)          | TikTokApi                | Playwright + Camoufox          |
| LinkedIn (v3)        | linkedin-api             | —                             |

### 2.6 Telegram Bot

| Componentă   | Tehnologie                               |
| --------------- | ------------------------------------------ |
| Framework bot | python-telegram-bot v21 (async)          |
| Pattern       | Conversation handlers + Inline keyboards |

### 2.7 Portal Web

| Componentă   | Tehnologie                 | Justificare                                  |
| --------------- | ---------------------------- | ---------------------------------------------- |
| Framework     | Reflex                     | Python pur, compilează în React, fără JS |
| Stilizare     | Reflex built-in (Radix UI) | Consistent, nu necesită CSS custom          |
| Autentificare | Cloudflare Access (extern) | Nu implementăm auth propriu                 |

### 2.8 Documentație automată

| Componentă    | Tehnologie                                                                                    | Detalii                  |
| ---------------- | ----------------------------------------------------------------------------------------------- | -------------------------- |
| Knowledge base | SiYuan (self-hosted)                                                                          | note.rebdev.online       |
| Integrare      | HTTP API (port default, HTTPS via CF Tunnel)                                                  | Authorization: token din`.env` |
| Pattern        | Claude Code apelează API la fiecare decizie arhitecturală, modificare majoră, bug rezolvat |                          |

---

## 3. Schema bazei de date

```sql
-- Multi-tenant: toți utilizatorii în același DB, izolați prin user_id

CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE,
    username    VARCHAR(100),
    is_admin    BOOLEAN DEFAULT false,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE monitored_sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    platform        VARCHAR(20) NOT NULL,  -- 'youtube' | 'twitch' | 'instagram' | ...
    external_id     VARCHAR(255) NOT NULL, -- channel_id, username, etc.
    display_name    VARCHAR(255),
    source_url      TEXT,
    is_active       BOOLEAN DEFAULT true,
    last_checked_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, platform, external_id)
);

CREATE TABLE content_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id           UUID REFERENCES monitored_sources(id) ON DELETE SET NULL,
    user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
    platform            VARCHAR(20) NOT NULL,
    external_content_id VARCHAR(255) NOT NULL,
    title               TEXT,
    original_url        TEXT,
    raw_transcript      TEXT,       -- textul brut, limba originală
    summary_short       TEXT,       -- titlu + 2-3 rânduri (pentru notificare)
    summary_full        TEXT,       -- rezumat complet în română
    language_detected   VARCHAR(10),
    is_one_shot         BOOLEAN DEFAULT false,
    published_at        TIMESTAMPTZ,
    processed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, platform, external_content_id)
);

CREATE TABLE embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_item_id UUID REFERENCES content_items(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    chunk_index     INTEGER,
    chunk_text      TEXT,
    embedding       vector(768),    -- nomic-embed-text dimensiune
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE user_feedback (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    content_item_id UUID REFERENCES content_items(id) ON DELETE CASCADE,
    rating          SMALLINT,       -- 1 = like, -1 = dislike, 0 = neutral
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, content_item_id)
);

CREATE TABLE notification_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_item_id UUID REFERENCES content_items(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    channel         VARCHAR(20) NOT NULL,   -- 'telegram' | 'web'
    status          VARCHAR(20) DEFAULT 'pending',
    sent_at         TIMESTAMPTZ,
    UNIQUE(content_item_id, user_id, channel)
);

CREATE TABLE rag_conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE rag_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES rag_conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20),    -- 'user' | 'assistant'
    content         TEXT,
    sources         JSONB,          -- [{content_item_id, chunk_index, score}]
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## 4. Structura proiect

```
pulse/
├── pulse/
│   ├── __init__.py
│   ├── config.py                   # pydantic-settings, toate env vars
│   ├── database.py                 # SQLAlchemy async engine + session
│   │
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── base.py                 # AbstractCollector
│   │   ├── youtube.py
│   │   ├── twitch.py
│   │   └── url_ingester.py
│   │
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── transcriber.py          # faster-whisper wrapper
│   │   ├── summarizer.py           # LLMClient calls
│   │   └── embedder.py             # Ollama nomic-embed-text
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py                 # AbstractLLMClient (interfață comună)
│   │   ├── ollama_client.py
│   │   └── openai_compat_client.py # DeepSeek / Qwen / orice OpenAI-compat
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   └── retriever.py            # pgvector similarity search + context builder
│   │
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── telegram.py             # handlers, inline keyboards
│   │   └── commands.py
│   │
│   ├── portal/                     # Reflex app
│   │   ├── __init__.py
│   │   ├── state.py                # Reflex state management
│   │   └── pages/
│   │       ├── dashboard.py
│   │       ├── sources.py
│   │       ├── history.py
│   │       ├── rag_chat.py
│   │       ├── learning.py
│   │       ├── logs.py
│   │       └── settings.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app, scheduler init
│   │   └── routers/
│   │       ├── sources.py
│   │       ├── content.py
│   │       └── users.py
│   │
│   └── siyuan/
│       ├── __init__.py
│       └── client.py               # SiYuan HTTP API wrapper
│
├── db/
│   └── migrations/                 # Alembic
│
├── docker-compose.yml
├── docker-compose.dev.yml
├── Dockerfile
├── .env.example
├── pyproject.toml
├── CLAUDE.md
└── README.md
```

---

## 5. Docker Compose (structură)

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: pulse
      POSTGRES_USER: pulse
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

  ollama:
    image: ollama/ollama
    volumes:
      - ollama_data:/root/.ollama
    # pe RPi: fără GPU, CPU inference

  pulse-api:
    build: .
    depends_on: [postgres, ollama]
    env_file: .env
    ports:
      - "8000:8000"    # FastAPI
      - "3000:3000"    # Reflex portal

volumes:
  postgres_data:
  ollama_data:
```

---

*Ultima actualizare: 2026-05-05*