> Obiectiv: un sistem funcțional end-to-end în cel mai scurt timp posibil, care să demonstreze fluxul complet: colectare → procesare → notificare Telegram.

---

## Scope POC v0.1

**Inclus:**

- YouTube: urmărire canale + transcript + rezumat în română
- YouTube: one-shot URL via Telegram
- Telegram bot: notificare preview + like/dislike + "citește mai mult"
- Storage: PostgreSQL + schema completă (pregătită pentru pgvector)
- LLM: qwen / DeepSeek
- Multi-tenant: 2 utilizatori

**Exclus din POC (backlog):**

- Twitch (v0.2)
- pgvector / RAG / Chat (v0.3)
- Portal web Reflex (v0.4)
- Instagram, TikTok, LinkedIn (v0.5+)
- Learning / feedback adaptat (v0.4)

---

## Milestone-uri

### M1 — Infrastructură (estimat: 2–3h)

- [ ] `docker-compose.yml` cu PostgreSQL + Ollama
- [ ] Schema DB completă cu Alembic
- [ ] `config.py` cu toate env vars
- [ ] `database.py` async SQLAlchemy
- [ ] `.env.example` documentat
- [ ] SiYuan client basic (`pulse/siyuan/client.py`)
- [ ] Test: conexiune DB, Ollama responds

### M2 — YouTube Collector (estimat: 3–4h)

- [ ] `YouTubeCollector` cu YouTube Data API v3
- [ ] Polling pe upload playlist (eficient, 1 unit/request)
- [ ] `youtube-transcript-api` pentru captions
- [ ] Fallback `yt-dlp` pipe → `faster-whisper`
- [ ] Deduplicare via UNIQUE constraint
- [ ] APScheduler job la fiecare 60 min
- [ ] Test: adaugă canal, rulează manual, verifică DB

### M3 — LLM Pipeline (estimat: 2–3h)

- [ ] `AbstractLLMClient` cu metodele `summarize()` și `embed()`
- [ ] `OllamaClient` implementare
- [ ] Prompt system: instrucțiuni în română, format preview vs. full
- [ ] `Summarizer` service: primește transcript, returnează `summary_short` + `summary_full`
- [ ] Test: transcript real → rezumat în română

### M4 — Telegram Bot (estimat: 3–4h)

- [ ] Bot creat pe @BotFather, token în `.env`
- [ ] Handler `/start` cu înregistrare user în DB
- [ ] Handler `/add [url]` — adaugă canal sau one-shot URL
- [ ] Handler `/sources` — listează sursele utilizatorului
- [ ] Handler `/status` — statusul sistemului
- [ ] Notificare automată: preview cu inline keyboard

  - Buton 👍 Like
  - Buton 👎 Dislike
  - Buton 📖 Citește mai mult
  - Buton 🔗 Deschide original
- [ ] `notification_log` deduplicare
- [ ] Test: video nou → notificare în Telegram în \< 70 min

### M5 — URL One-Shot (estimat: 1–2h)

- [ ] `/add https://youtube.com/watch?v=...` detectează video individual
- [ ] Procesare imediată (nu asteaptă scheduler)
- [ ] Răspuns în Telegram în \< 2 min
- [ ] Test: trimite URL random YouTube, primești rezumat în română

### M6 — Integrare SiYuan (estimat: 1h)

- [ ] `SiYuanClient.create_note(title, content, notebook_id)`
- [ ] `SiYuanClient.append_to_note(note_id, content)`
- [ ] Claude Code documentează automat în SiYuan:

  - Fiecare migrare DB aplicată
  - Fiecare decizie arhitecturală
  - Fiecare bug major rezolvat
- [ ] Test: rulează M1-M5, verifică că există note în SiYuan

---

## Definition of Done pentru POC

- [ ] Adaug un canal YouTube → în mai puțin de 70 min primesc prima notificare Telegram
- [ ] Trimit un URL YouTube random în Telegram → primesc rezumat în română în \< 2 min
- [ ] Dau Like/Dislike dinTelegram → se salvează în DB
- [ ] Cer "Citește mai mult" → primesc rezumatul complet
- [ ] Același video nu generează două notificări
- [ ] Al doilea utilizator (colegul) vede doar sursele lui
- [ ] SiYuan conține minimum 5 note generate automat de Claude Code

---

## Riscuri identificate

| Risc                                     | Probabilitate | Mitigare                                                       |
| ------------------------------------------ | --------------- | ---------------------------------------------------------------- |
| YouTube API quota (10k units/zi)         | Medie         | Folosim`playlistItems.list`(1 unit) nu`search.list`(100 units)                                  |
| qwen                                     | Mare          | Testat înainte, fallback la model mai mic (3b) sau API extern |
| faster-whisper RAM pe RPi                | Medie         | Model`base`(\< 1GB RAM), nu`large`                                       |
| Rate limiting YouTube transcript API     | Mică         | Delay între request-uri, exponential backoff                  |
| TwitchIO EventSub necesită HTTPS public | —            | Cloudflare Tunnel rezolvă asta pentru Twitch în v0.2         |

---

## Ordine de lucru recomandată cu Claude Code

```
1. claude "Implementează M1: docker-compose + schema DB + config"
2. claude "Implementează M2: YouTube collector"
3. claude "Testează M2: rulează manual colectorul pe canalul X"
4. claude "Implementează M3: LLM pipeline cu Ollama"
5. claude "Testează M3: transcript → rezumat pentru ultimul video colectat"
6. claude "Implementează M4: Telegram bot complet"
7. claude "Test end-to-end: M1 → M4"
8. claude "Implementează M5: URL one-shot"
9. claude "Implementează M6: SiYuan integration"
10. claude "Documentează tot ce s-a făcut în SiYuan"
```

---

*Ultima actualizare: 2026-05-05*