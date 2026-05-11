---

## 1. Colectare conținut

### 1.1 YouTube

| ID    | Cerință                                                           | Status | Note                                             |
| ------- | --------------------------------------------------------------------- | -------- | -------------------------------------------------- |
| YT-01 | Utilizatorul poate adăuga un canal YouTube prin URL sau channel ID | 🔜     | Via portal sau comandă Telegram                 |
| YT-02 | Sistemul verifică canale urmărite la fiecare 1 oră               | 🔜     | APScheduler, polling pe upload playlist          |
| YT-03 | Detectează video-uri noi față de ultima verificare               | 🔜     | Compară cu`last_checked_at`per sursă                            |
| YT-04 | Extrage transcriptul existent (captions auto sau manuale)           | 🔜     | youtube-transcript-api, zero stocare audio       |
| YT-05 | Fallback: descarcă doar audio și transcrie cu faster-whisper      | 🔜     | yt-dlp pipe → whisper, fără fișier temp      |
| YT-06 | Utilizatorul poate trimite un URL YouTube one-shot în Telegram     | 🔜     | Nu necesită canal urmărit                      |
| YT-07 | Extrage metadata: titlu, durată, dată publicare, thumbnail URL    | 🔜     | google-api-python-client                         |
| YT-08 | Nu procesează același video de două ori (deduplicare)            | 🔜     | UNIQUE constraint pe external\_content\_id |

### 1.2 Twitch

| ID    | Cerință                                                       | Status | Note                                                    |
| ------- | ----------------------------------------------------------------- | -------- | --------------------------------------------------------- |
| TW-01 | Sistemul detectează când un streamer urmărit intră live     | 🔜     | TwitchIO EventSub webhook                               |
| TW-02 | Înregistrează audio stream-ului live via streamlink pipe      | 🔜     | Fără stocare video                                    |
| TW-03 | Transcrie audio în timp real sau la finalul stream-ului        | 🔜     | **TBD**: real-time vs. post-stream (vezi secțiunea deschisă) |
| TW-04 | Detectează sfârșitul stream-ului și finalizează procesarea | 🔜     | EventSub stream.offline event                           |
| TW-05 | Stochează timestamp-uri de start/end stream                    | 🔜     |                                                         |
| TW-06 | Portița pentru chat în viitor (arhitectură pregătită)      | 🔜     | Câmp rezervat în schema DB, colector neimplementat    |

### 1.3 URL One-Shot

| ID    | Cerință                                                        | Status | Note |
| ------- | ------------------------------------------------------------------ | -------- | ------ |
| OS-01 | Acceptă URL YouTube arbitrar (canale neurmărite)               | 🔜     |      |
| OS-02 | Procesează și returnează rezumat în Telegram în \< 2 min | 🔜     |      |
| OS-03 | Salvează în istoric cu flag`one_shot=true`                                    | 🔜     |      |

---

## 2. Procesare și AI

### 2.1 Transcriere

| ID    | Cerință                                          | Status | Note                                  |
| ------- | ---------------------------------------------------- | -------- | --------------------------------------- |
| TR-01 | Detectează limba originală a conținutului       | 🔜     | faster-whisper returnează limba auto |
| TR-02 | Stochează transcriptul brut în limba originală  | 🔜     |                                       |
| TR-03 | Transcrierea nu blochează alte procesări (async) | 🔜     |                                       |

### 2.2 Rezumare

| ID    | Cerință                                                                                                      | Status | Note                    |
| ------- | ---------------------------------------------------------------------------------------------------------------- | -------- | ------------------------- |
| SM-01 | Generează rezumat în**română**indiferent de limba originală                                                           | 🔜     | Prompt explicit         |
| SM-02 | Format notificare: titlu + 2-3 rânduri (preview)                                                              | 🔜     |                         |
| SM-03 | Format complet: titlu + paragraf narativ + 5 puncte cheie                                                      | 🔜     | La cerere explicită    |
| SM-04 | Clientul LLM este abstractizat — se poate comuta între Ollama local și API extern fără modificări de cod | 🔜     | Interfață comună`LLMClient`     |
| SM-05 | **LLM implicit pentru POC**: qwen                                                                                                         | 🔜     | **TBD**: decizie finală model |
| SM-06 | Prompt-ul include context despre utilizator și preferințele lui                                              | 🔜     | Din tabelul`user_preferences`             |

### 2.3 Embeddings și RAG

| ID    | Cerință                                                          | Status | Note                            |
| ------- | -------------------------------------------------------------------- | -------- | --------------------------------- |
| EM-01 | Fiecare item procesat generează embeddings via nomic-embed-text   | 🔜     | qwen                            |
| EM-02 | Embeddings stocate în pgvector (același PostgreSQL)              | 🔜     |                                 |
| EM-03 | Fiecare utilizator are spațiu vectorial izolat (tenant isolation) | 🔜     | Filtru pe`user_id`la toate query-urile   |
| EM-04 | Utilizatorul poate conversa cu AI despre conținutul ingerat       | 🔜     | Via portal web, pagina RAG/Chat |
| EM-05 | Conversația include context din ultimele N chunk-uri relevante    | 🔜     | Top-K cosine similarity         |
| EM-06 | Istoricul conversațiilor RAG se salvează per utilizator          | 🔜     |                                 |

---

## 3. Notificări Telegram

| ID    | Cerință                                                             | Status | Note                   |
| ------- | ----------------------------------------------------------------------- | -------- | ------------------------ |
| TG-01 | Bot Telegram nou, pornit de la zero                                   | 🔜     |                        |
| TG-02 | Notificare automată la conținut nou: titlu + 2-3 rânduri           | 🔜     |                        |
| TG-03 | Două butoane inline: 👍 Like / 👎 Dislike                            | 🔜     | Callback query handler |
| TG-04 | Buton "Citește mai mult" — returnează rezumatul complet            | 🔜     |                        |
| TG-05 | Buton "Deschide original" — link sursă                              | 🔜     |                        |
| TG-06 | Fiecare utilizator primește notificări doar pentru sursele lui      | 🔜     | Multi-tenant           |
| TG-07 | Deduplicare notificări — același item nu se notifică de două ori | 🔜     | `notification_log`cu UNIQUE constraint   |
| TG-08 | Comandă`/add [url]`— adaugă sursă sau one-shot URL                            | 🔜     |                        |
| TG-09 | Comandă`/sources`— listează sursele urmărite                                | 🔜     |                        |
| TG-10 | Comandă`/status`— statusul sistemului                                        | 🔜     |                        |

---

## 4. Portal Web (Reflex)

### Meniu principal

```
Dashboard | Sources | History | RAG Chat | Learning | Logs | Settings
```

### 4.1 Dashboard

| ID    | Cerință                                             | Note |
| ------- | ------------------------------------------------------- | ------ |
| PW-01 | Overview: items procesate azi, această săptămână |      |
| PW-02 | Ultimele 10 items cu preview                          |      |
| PW-03 | Status colectori (last run, next run, erori)          |      |

### 4.2 Sources

| ID    | Cerință                                                   | Note |
| ------- | ------------------------------------------------------------- | ------ |
| PW-10 | Adaugă/șterge/dezactivează surse                         |      |
| PW-11 | Per sursă: statistici (items colectate, ultima activitate) |      |
| PW-12 | Forțează re-fetch manual per sursă                       |      |

### 4.3 History

| ID    | Cerință                                                   | Note |
| ------- | ------------------------------------------------------------- | ------ |
| PW-20 | Listă paginată a tuturor itemilor procesați              |      |
| PW-21 | Filtre: platformă, sursă, dată, rating (liked/disliked)  |      |
| PW-22 | Click pe item: rezumat complet + transcript brut + metadata |      |

### 4.4 RAG Chat

| ID    | Cerință                                            | Note |
| ------- | ------------------------------------------------------ | ------ |
| PW-30 | Interfață chat cu AI pe baza conținutului ingerat |      |
| PW-31 | Afișează sursele folosite pentru fiecare răspuns  |      |
| PW-32 | Istoric conversații salvat                          |      |

### 4.5 Learning

| ID    | Cerință                                                    | Note |
| ------- | -------------------------------------------------------------- | ------ |
| PW-40 | Vizualizare preferințe deduse (topicuri liked vs. disliked) |      |
| PW-41 | **TBD**: sistem explicit de "skills" / topicuri de interes          |      |
| PW-42 | Grafic evoluție feedback în timp                           |      |

### 4.6 Logs

| ID    | Cerință                                           | Note |
| ------- | ----------------------------------------------------- | ------ |
| PW-50 | Log în timp real al tuturor acțiunilor sistemului |      |
| PW-51 | Filtre: nivel (INFO/WARNING/ERROR), modul, dată    |      |
| PW-52 | Export logs                                         |      |

### 4.7 Settings

| ID    | Cerință                                         | Note |
| ------- | --------------------------------------------------- | ------ |
| PW-60 | Configurare LLM (model, API key extern opțional) |      |
| PW-61 | Configurare Telegram (token bot)                  |      |
| PW-62 | Configurare frecvență polling per platformă    |      |
| PW-63 | Management utilizatori (admin only)               |      |

---

## 5. Securitate și acces

| ID     | Cerință                                                                | Note |
| -------- | -------------------------------------------------------------------------- | ------ |
| SEC-01 | Portalul web accesibil exclusiv prin Cloudflare Zero Trust               |      |
| SEC-02 | Cloudflare Tunnel expune portalul la un domeniu personal                 |      |
| SEC-03 | Autentificare portal: Cloudflare Access (Google/Email OTP)               |      |
| SEC-04 | API keys și tokens stocate în`.env`, niciodată în cod                      |      |
| SEC-05 | SiYuan token în`.env`, acces exclusiv din rețeaua locală sau prin CF Tunnel |      |

---

## 6. Întrebări deschise (TBD)

| ID     | Întrebare                                                          | Impact                             |
| -------- | --------------------------------------------------------------------- | ------------------------------------ |
| TBD-01 | Model LLM final: Qwen API vs. DeepSeek?                             | Calitate rezumate, cost, latență |
| TBD-02 | Twitch: rezumat real-time (la fiecare 30 min) sau doar post-stream? | Complexitate implementare          |
| TBD-03 | Sistemul de "Skills" în Learning — ce înseamnă exact?           | Feature scope                      |
| TBD-04 | Twitch chat — în ce versiune se implementează?                   | Backlog prioritization             |
| TBD-05 | Retention policy — cât timp păstrăm transcripturile brute?      | Storage planning                   |

---

*Ultima actualizare: 2026-05-05*