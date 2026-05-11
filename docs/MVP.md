# MVP Pulse — Scope și limite

## Ce face MVP-ul (și nimic altceva)

### Funcționalități incluse

1. **Urmărire canale YouTube** — utilizatorul trimite un link de canal, bot-ul îl salvează și verifică periodic (la 10 minute) dacă au apărut videoclipuri noi.

2. **Notificări automate** — când apare un video nou pe un canal urmărit, bot-ul trimite un rezumat în chat (privat sau de grup).

3. **Rezumat instant** — utilizatorul trimite orice link de video YouTube, bot-ul răspunde cu rezumatul (transcript + DeepSeek).

4. **Funcționare în grupuri Telegram** — adaugi bot-ul într-un grup Telegram, folosești exact aceleași comenzi; abonamentele și notificările se leagă de chat-ul grupului.

### Comenzi bot

```
/start              — înregistrează chat-ul (privat sau grup)
/add <url>          — urmărește canal YouTube în acest chat
/sources            — listează canalele urmărite în acest chat
/remove <yt_id>     — șterge abonament
/status             — uptime + statistici simple

[orice link video]  — rezumat instant, fără să stochezi canalul
```

---

## Ce NU este în MVP (și nu se implementează fără decizie explicită)

| Funcționalitate | Motiv excludere |
|---|---|
| Portal web (NiceGUI) | Zero necesitate pentru MVP |
| RAG / embeddings / pgvector | Complexitate fără beneficiu imediat |
| Integrare SiYuan | Documentare manuală e suficientă acum |
| Facebook / Instagram / LinkedIn / Twitch | MVP = YouTube only |
| FastAPI separată | Un singur proces e suficient |
| Feedback (like/dislike) | Neesențial pentru MVP |
| Sistem de „skills" sau „learning" | TBD nedefinit |
| Retry exponențial custom | Over-engineering |
| Embeddings Ollama | RAG dezactivat |

---

## Arhitectura MVP (un singur proces)

```
python -m pulse
    ├── bot.py          — handleri Telegram (comenzi + mesaje cu link)
    └── scheduler.py    — poll la 10 minute → procesează video nou → notifică
```

## Schema DB (minimă)

```
chats           — chat_id (Telegram), chat_type, title
yt_channels     — id, yt_id (UC...), name, last_video_id, checked_at
chat_subs       — chat_id → yt_channel_id  (many-to-many)
videos          — id, yt_id UNIQUE, title, transcript, summary, published_at
notif_sent      — chat_id, video_yt_id  (deduplicare trimiteri)
```

## Proprietăți cheie ale designului

- **`last_video_id`**: după fiecare poll salvăm ultimul video ID văzut. La pollul următor luăm numai ce e mai nou decât acesta. Fără duplicări, fără re-trimiteri după ștergere DB.
- **`videos` partajat**: dacă 10 chat-uri urmăresc același canal, transcriptul și summary-ul se calculează o singură dată.
- **Transcript gol = nicio notificare**: dacă nu putem extrage textul video-ului, logăm eroarea și nu trimitem nimic. Nu există notificări goale.
- **Un singur proces**: bot + scheduler în același `asyncio` event loop. Zero comunicare inter-proces.
