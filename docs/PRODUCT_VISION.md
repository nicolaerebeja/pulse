> *Simți pulsul a ceea ce contează pentru tine.*

---

## 1. Problema

Consumul de conținut online în 2026 este fragmentat și zgomotos. Un profesionist sau antreprenor care urmărește 10–20 creatori de conținut pe YouTube, Twitch, Instagram, TikTok și LinkedIn pierde zilnic ore întregi fie consumând conținut irelevant, fie ratând complet ce e important pentru că nu a avut timp să verifice fiecare platformă.

Soluțiile existente (RSS, newsletters, agregatori generici) nu înțeleg **preferințele individuale** și nu oferă **context conversațional** — nu poți întreba un RSS feed "ce a zis X despre subiectul Y în ultimele 3 săptămâni?".

---

## 2. Viziunea

**Pulse** este un sistem personal de media intelligence care:

- Urmărește autonom creatorii de conținut selectați manual
- Extrage, transcrie și traduce conținutul în română
- Generează rezumate concise livrate prin Telegram
- Stochează totul într-un vector DB pentru conversații RAG
- Învață preferințele utilizatorului prin feedback explicit (like/dislike) și comportament implicit (ce deschide, ce ignoră)
- Rulează complet **self-hosted** pe hardware propriu, fără dependențe cloud obligatorii

Pulse nu este un produs public. Este o unealtă personală de amplificare a capacității de analiză și sinteză informațională, construită ca proiect de învățare și experiență practică în scraping, AI pipelines și RAG.

---

## 3. Utilizatori țintă

| Utilizator | Descriere                                                                                                   |
| ------------ | ------------------------------------------------------------------------------------------------------------- |
| Owner (tu) | Dezvoltator full-stack, antreprenor, urmărește conținut tehnic și de business în română și engleză |
| Coleg      | Al doilea tenant — surse proprii, preferințe proprii, izolat complet de primul utilizator                 |

Sistemul este **multi-tenant by design**, chiar dacă nu va fi niciodată public. Fiecare utilizator are: surse proprii, istoric propriu, preferințe proprii, spațiu RAG propriu.

---

## 4. Platforme suportate (roadmap)

| Platformă        | Status    | Metodă                                         | Prioritate |
| ------------------- | ----------- | ------------------------------------------------- | ------------ |
| YouTube           | ✅ POC v1 | API oficial + youtube-transcript-api            | P0         |
| Twitch            | ✅ POC v1 | TwitchIO EventSub + streamlink + faster-whisper | P0         |
| Instagram         | 🔜 v2     | Instaloader (profiluri publice)                 | P1         |
| Facebook Pages    | 🔜 v2     | facebook-scraper / RSS                          | P1         |
| TikTok            | 🔜 v2     | TikTokApi + Playwright stealth                  | P1         |
| LinkedIn          | 🔜 v3     | linkedin-api (cont dedicat)                     | P2         |
| Telegram channels | 🔜 v3     | Telethon                                        | P2         |
| RSS/Web generic   | 🔜 v3     | feedparser + readability                        | P2         |

---

## 5. Principii de design

1. **Privacy first** — toate datele rămân pe hardware propriu. Niciun conținut nu pleacă în cloud fără consimțământ explicit.
2. **Python only** — întreg stack-ul (backend, bot, portal) este Python pur. Zero Node.js, zero framework-uri complexe. Cod lizibil de un junior fără AI.
3. **Progressive complexity** — POC simplu, extensibil incremental. Nu over-engineerăm de la start.
4. **Graceful degradation** — dacă un collector eșuează, restul sistemului continuă. Fiecare modul e izolat.
5. **Observable** — fiecare acțiune se loghează. Portalul are o pagină de Logs completă.
6. **Documentat automat** — Claude Code documentează fiecare decizie și modificare în SiYuan via API.

---

## 6. Ce NU este Pulse

- Nu este un produs SaaS public
- Nu este un instrument de surveillance sau monitorizare a persoanelor private
- Nu înlocuiește consumul direct de conținut — oferă un filtru și un punct de intrare
- Nu este un tool de automatizare a postărilor (nu publică nimic în numele utilizatorului)

---

## 7. Succes metrics (personal)

- Timp economisit per zi în consumul de conținut: **target \> 1 oră**
- Rată de relevanță a notificărilor Telegram după 30 zile de feedback: **target \> 80%**
- Latență medie de la publicare conținut la notificare Telegram: **target \< 60 min pentru YouTube, \< 10 min pentru Twitch live**
- Uptime sistem pe RPi 5: **target \> 99% lunar**

---

*Document viu — actualizat pe măsură ce proiectul evoluează.Ultima actualizare: 2026-05-05*