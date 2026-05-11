---

## 1. Model de securitate

Pulse rulează complet self-hosted. Nu există date în cloud. Singurul punct de expunere externă este prin **Cloudflare Zero Trust**, care acționează ca un Identity-Aware Proxy în fața tuturor serviciilor.

```
Internet → Cloudflare Access (autentificare) → Cloudflare Tunnel → RPi 5 / Proxmox
```

---

## 2. Cloudflare Zero Trust Setup

### 2.1 Cloudflare Tunnel

```bash
# Instalare cloudflared pe RPi
curl -L --output cloudflared.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
sudo dpkg -i cloudflared.deb

# Autentificare și creare tunnel
cloudflared tunnel login
cloudflared tunnel create pulse

# Configurare (~/.cloudflared/config.yml)
tunnel: <TUNNEL_ID>
credentials-file: /home/pi/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: pulse.rebdev.online
    service: http://localhost:3000    # Reflex portal
  - hostname: pulse-api.rebdev.online
    service: http://localhost:8000    # FastAPI (dacă e nevoie)
  - hostname: note.rebdev.online
    service: http://localhost:6806    # SiYuan (deja configurat)
  - service: http_status:404
```

### 2.2 Cloudflare Access Policy

- **Application**: `pulse.rebdev.online`
- **Policy**: Allow → Email → [emailurile tale și ale colegului]
- **Session duration**: 24h
- **Purpose**: Zero port-forwarding, zero VPN, autentificare prin email OTP sau Google

---

## 3. Secrete și variabile de mediu

### 3.1 Fișier `.env` (niciodată în git)

```bash
# Database
POSTGRES_PASSWORD=<strong-random-password>
DATABASE_URL=postgresql+asyncpg://pulse:<password>@localhost:5432/pulse

# YouTube
YOUTUBE_API_KEY=<google-api-key>

# Twitch (v0.2)
TWITCH_CLIENT_ID=
TWITCH_CLIENT_SECRET=
TWITCH_WEBHOOK_SECRET=

# Telegram
TELEGRAM_BOT_TOKEN=<token-from-botfather>

# LLM - Ollama (local, default)
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_EMBED_MODEL=nomic-embed-text

# LLM - External API (opțional, swap)
LLM_PROVIDER=ollama                  #  'deepseek' | 'qwen'
EXTERNAL_LLM_API_KEY=
EXTERNAL_LLM_BASE_URL=
EXTERNAL_LLM_MODEL=

# SiYuan
SIYUAN_API_URL=https://note.rebdev.online
SIYUAN_TOKEN=ttmyid1336sxelpc
SIYUAN_NOTEBOOK_ID=<notebook-id-for-pulse>

# App
APP_SECRET_KEY=<random-32-chars>
APP_ENV=production                   # 'development' | 'production'
LOG_LEVEL=INFO
```

### 3.2 `.gitignore` obligatoriu

```
.env
.env.local
*.pyc
__pycache__/
.venv/
docker-compose.override.yml
```

---

## 4. Backup strategie

### 4.1 PostgreSQL

```bash
# Backup zilnic automat (cron pe RPi)
0 3 * * * docker exec pulse-postgres pg_dump -U pulse pulse | \
  gzip > /mnt/ssd/backups/pulse_$(date +%Y%m%d).sql.gz

# Retenție: ultimele 30 zile
find /mnt/ssd/backups/ -name "pulse_*.sql.gz" -mtime +30 -delete
```

### 4.2 SSD extern (/mnt/ssd)

- Partiție dedicată pentru date Pulse (PostgreSQL data + backups + Ollama models)
- Minim 100GB alocat

### 4.3 Sincronizare opțională pe Proxmox

- rsync nocturn RPi → Proxmox pentru backup secundar

---

## 5. Monitoring

| Ce monitorizăm    | Cum                      | Alertă                                 |
| -------------------- | -------------------------- | ----------------------------------------- |
| Servicii Docker up | Docker health checks     | Telegram bot trimite alertă la restart |
| Spațiu disk       | Script bash în cron     | Alertă la \> 80% utilizare          |
| Erori colectori    | structlog → tabel`logs`în DB | Vizibil în portalul Logs               |
| YouTube API quota  | Contor zilnic în DB     | Alertă la \> 8000 units/zi          |
| Ollama latență   | Timer în summarizer     | Log WARNING la \> 30s per rezumat    |

---

## 6. Rate limiting și comportament etic

### YouTube

- Folosim `playlistItems.list` nu `search.list` (1 unit vs 100 units per request)
- Delay minim 1s între request-uri consecutive
- Exponential backoff la HTTP 429

### Twitch

- EventSub webhooks — platforma notifică noi, nu facem polling
- Un singur streamer urmărit per cont de aplicație

### General

- User-Agent realist în toate request-urile
- Respectăm `Retry-After` headers
- Nu procesăm conținut privat sau cu acces restricționat

---

## 7. Deployment pe RPi 5

```bash
# Setup inițial
git clone https://github.com/<user>/pulse.git
cd pulse
cp .env.example .env
# editează .env cu valorile reale

# Pull modele Ollama
docker compose up ollama -d
docker exec pulse-ollama ollama pull qwen2.5:7b
docker exec pulse-ollama ollama pull nomic-embed-text

# Migrări DB
docker compose up postgres -d
docker compose run --rm pulse-api alembic upgrade head

# Start complet
docker compose up -d

# Verificare
docker compose ps
docker compose logs -f pulse-api
```

---

## 8. Upgrade strategy

```bash
git pull
docker compose build pulse-api
docker compose run --rm pulse-api alembic upgrade head
docker compose up -d pulse-api
```

---

*Ultima actualizare: 2026-05-05*