---

## 1. Principii de design

1. **Information density** — portalul e un tool personal de putere, nu un produs de larg consum. Densitate mai mare de informație e ok.
2. **Dark mode by default** — e un portal de monitorizare, rulează probabil seara sau în birou.
3. **Zero friction pentru acțiunile comune** — adăugarea unei surse, cititul unui rezumat, căutarea în RAG trebuie să fie la maximum 2 click-uri.
4. **Telegram e interfața primară** — portalul e pentru analiză și configurare, Telegram e pentru consum zilnic.

---

## 2. Telegram Bot — UX Flow

### 2.1 Primul contact (onboarding)

```
User: /start

Bot: 👋 Bun venit în Pulse!
     Sistemul tău personal de media intelligence.

     Pentru a începe, adaugă prima sursă:
     /add https://youtube.com/@numecanal

     Sau trimite-mi direct un link YouTube pentru un rezumat instant.
     
     📖 /help pentru toate comenzile
```

### 2.2 Adăugare sursă

```
User: /add https://youtube.com/@lexfridman

Bot: ✅ Canal adăugat: Lex Fridman
     📊 408 videoclipuri | Ultimul: acum 3 zile
     ⏰ Prima verificare în mai puțin de 60 minute.
     
     [🗑 Șterge sursa]  [📋 Vezi toate sursele]
```

### 2.3 Notificare conținut nou

```
Bot: 🎬 Lex Fridman
     
     "Elon Musk: AI, Robots, and the Future"
     
     Elon Musk discută despre riscurile AI-ului general, 
     progresul Neuralink și viziunea sa despre colonizarea Marte. 
     Accentuează necesitatea unui AI "truth-seeking".
     
     ──────────────────
     [👍 Like]  [👎 Dislike]  [📖 Mai mult]  [🔗 Original]
```

### 2.4 La "Mai mult"

```
Bot: 📄 Rezumat complet:

     Lex Fridman — "Elon Musk: AI, Robots, and the Future"
     🕐 3h 24min | 📅 3 mai 2026
     
     Elon Musk revine pe podcastul Lex Fridman pentru o 
     conversație de peste 3 ore despre direcția tehnologică 
     a civilizației umane. [... paragraf complet ...]
     
     **Puncte cheie:**
     • AGI în 2-3 ani conform estimărilor Musk
     • Neuralink: primele 3 implanturi umane funcționale
     • xAI: Grok 3 bate GPT-4 la matematică
     • Tesla Optimus: 1000 roboți produși zilnic în Q2 2026
     • Critica adusă OpenAI: "a pierdut misiunea originală"
     
     ──────────────────
     [👍 Like]  [👎 Dislike]  [🔗 Original]  [💬 Întreabă AI]
```

### 2.5 Butonul "Întreabă AI" — entry point RAG din Telegram

```
Bot: 💬 Ce vrei să știi despre acest video?
     Poți pune orice întrebare legată de conținut.

User: Ce a zis despre Neuralink exact?

Bot: 🧠 Bazat pe conținutul video:
     
     Musk a explicat că Neuralink are în prezent 3 pacienți 
     cu implanturi funcționale. Primul pacient [...] 
     
     📚 Sursă: Lex Fridman #400 (3 mai 2026), min 1:23:45
```

### 2.6 Comenzi complete

| Comandă | Descriere                                          |
| ---------- | ---------------------------------------------------- |
| `/start`         | Onboarding                                         |
| `/add [url]`         | Adaugă canal sau procesează URL one-shot         |
| `/sources`         | Lista surselor urmărite cu status                 |
| `/remove [id]`         | Șterge o sursă                                   |
| `/status`         | Statusul sistemului (uptime, queue, ultima rulare) |
| `/help`         | Lista tuturor comenzilor                           |

---

## 3. Portal Web — Structură și UX

### 3.1 Navigare principală

```
[Pulse logo]  Dashboard | Sources | History | Chat | Learning | Logs | Settings
                                                                    [User: tu ▾]
```

### 3.2 Dashboard

**Layout**: 3 coloane pe desktop, 1 coloană pe mobil.

**Coloana stânga — Stats azi:**

- Items procesate azi / această săptămână
- Breakdown per platformă (YouTube: 5, Twitch: 1)
- Notificări trimise / opened / liked

**Coloana centru — Feed recent:**

- Ultimele 10 items, format card complet
- Fiecare card: thumbnail | titlu | sursă | dată | rating (dacă există) | preview 2 rânduri
- Click pe card → History detail view

**Coloana dreapta — Status sistem:**

- Colectori: ✅ YouTube (last: 12 min ago) | ✅ Twitch (watching)
- Queue: 2 items în procesare
- Next run: YouTube în 48 min
- Ollama: ✅ responding (avg 8s/rezumat)

### 3.3 Sources

**Layout**: tabel cu acțiuni inline.

| Platformă | Nume        | URL                | Status   | Ultima activitate | Items total | Acțiuni              |
| ------------ | ------------- | -------------------- | ---------- | ------------------- | ------------- | ----------------------- |
| 🎬 YouTube | Lex Fridman | youtube.com/@lex   | ✅ Activ | 3 mai, 14:22      | 47          | Edit / Pause / Delete |
| 🎮 Twitch  | Fireship    | twitch.tv/fireship | ✅ Activ | Live acum         | 8           | Edit / Pause / Delete |

**Adăugare sursă**: modal simplu — input URL + buton Adaugă. Sistemul detectează automat platforma.

### 3.4 History

**Filtre** (top bar):

- Platformă: All / YouTube / Twitch / ...
- Sursă: dropdown cu toate sursele
- Rating: All / Liked / Disliked / Unrated
- Perioadă: azi / săptămâna aceasta / luna aceasta / custom range

**Layout**: listă densa de carduri cu preview.

**Detail view** (click pe item):

- Titlu + metadata (durată, dată, sursă)
- Rezumat scurt
- Rezumat complet (expandabil)
- Transcript brut (expandabil, scrollabil)
- Rating curent + posibilitate de a schimba
- Buton "Discută cu AI despre asta" → deschide Chat cu context pre-setat

### 3.5 RAG Chat

**Layout**: interfață chat standard, două coloane pe desktop.

**Stânga (70%)** : conversație chat

- Mesajele utilizatorului și răspunsurile AI
- Sub fiecare răspuns AI: "📚 Bazat pe: [titlu video 1], [titlu video 2]" — linkuri către History

**Dreapta (30%)** : context panel

- "Surse folosite în această conversație"
- Filtre rapide: "Caută doar în YouTube", "Caută doar în ultimele 30 zile"

**Input**: textarea cu buton Send + opțiune "Resetează conversația"

### 3.6 Learning

**Scop**: vizualizarea a ce a "înțeles" sistemul despre preferințele tale.

**Secțiuni**:

*Topicuri liked (word cloud sau bar chart):*

- AI/ML: 23 items liked
- Antreprenoriat: 15 items liked
- Tech deep-dives: 18 items liked

*Topicuri disliked:*

- Politică: 8 items disliked
- Crypto: 5 items disliked

*Creatori preferați (ranked by engagement):*

1. Lex Fridman — 89% like rate
2. Fireship — 94% like rate

*Evoluție în timp*: grafic simplu liked vs. disliked pe ultimele 30 zile.

**TBD**: secțiunea "Skills" — rămasă deschisă până la decizie.

### 3.7 Logs

**Layout**: tabel live cu auto-refresh la 10s.

| Timestamp | Level   | Modul                 | Mesaj                                                    |
| ----------- | --------- | ----------------------- | ---------------------------------------------------------- |
| 14:23:01  | INFO    | youtube\_collector | Verificat canal Lex Fridman: 0 videoclipuri noi          |
| 14:22:47  | INFO    | summarizer            | Rezumat generat în 7.3s qwen                            |
| 14:22:40  | INFO    | transcriber           | Transcript extras: 45,230 caractere                      |
| 14:21:15  | WARNING | youtube\_collector | Rate limit hit, retry în 30s                            |
| 14:20:00  | ERROR   | telegram\_bot      | Failed to send notification user\_id\=2, retry 1/3 |

**Filtre**: Level dropdown | Modul dropdown | Search text | Date range

### 3.8 Settings

**Secțiuni taburi**: General | LLM | Telegram | Sources | Users

*General*:

- Timezone
- Frecvență polling YouTube (30min / 1h / 2h / 6h)
- Limba rezumatelor (pentru viitor)

*LLM*:

- Provider activ:  DeepSeek / Qwen
- Dacă extern: API key (masked), model name, test connection
- Model embeddings

*Telegram*:

- Bot token (masked) + test send
- Chat ID per utilizator

*Users* (admin only):

- Lista utilizatorilor
- Adaugă utilizator nou (telegram\_id + username)
- Revocă acces

---

## 4. Multi-tenant isolation în UI

- Utilizatorul vede **strict** datele lui
- Admin poate vedea toți utilizatorii în Settings \> Users
- Nu există vizibilitate cross-tenant nici în portal, nici în Telegram
- Switch de cont în portal: dropdown top-right (admin only poate switch)

---

*Ultima actualizare: 2026-05-05*