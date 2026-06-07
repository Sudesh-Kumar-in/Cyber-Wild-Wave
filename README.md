# 🔥 CYBER WILD WAVE

> **Production-ready Premium OSINT Telegram Bot** with subscription system, admin panel, 7 search types, payment verification, and full auto-cleanup chat experience.

---

## Features

| Feature | Description |
|---|---|
| 📱 Number Lookup | Mobile number intelligence |
| 📞 Telegram Lookup | Telegram user data |
| 🪪 Aadhaar Lookup | Aadhaar linked data |
| 👨‍👩‍👧‍👦 Family Lookup | Family member data |
| 📍 Pincode Lookup | Area & post office info |
| 🏦 IFSC Lookup | Bank branch details |
| 🚗 Vehicle Lookup | Vehicle registration info |
| 💎 Premium System | Plans, key activation, payment verification |
| 👑 Admin Panel | Full management (ban, broadcast, stats, logs) |
| 🧹 Auto Cleanup | Only user query + result remain in chat |
| 📊 Analytics | Live stats, search logs, export |
| ⏸ Freeze System | Pause/resume premium timers |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your values
```

### 3. Run

```bash
python main.py
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Telegram Bot token from @BotFather |
| `API_KEY` | ✅ | OSINT API key |
| `ADMIN_IDS` | ✅ | Comma-separated Telegram user IDs for admins |
| `SESSION_SECRET` | ✅ | Secret string for session security |
| `CHANNEL_INVITE_LINK` | ❌ | Force-join channel link (leave blank to disable) |
| `DATABASE_PATH` | ❌ | SQLite DB path (default: `bot.db`) |
| `FREE_DAILY_SEARCHES` | ❌ | Free searches per day (default: `5`) |

---

## Project Structure

```
bot/
├── main.py                  # Entry point & handler routing
├── config.py                # All configuration & plan definitions
├── database.py              # Async SQLite database layer
├── requirements.txt         # Python dependencies
│
├── handlers/
│   ├── start.py             # /start, welcome, main menu buttons
│   ├── search.py            # Search keyboard flow + cleanup
│   ├── premium.py           # Premium plans, key redemption
│   ├── admin.py             # Admin panel (all admin actions)
│   ├── account.py           # My Account view
│   └── payment.py           # Screenshot upload & approval
│
├── keyboards/
│   ├── main_kb.py           # User / Admin / Search keyboards
│   ├── admin_kb.py          # Admin inline keyboards
│   ├── premium_kb.py        # Premium inline keyboards
│   └── search_kb.py         # Search back-button keyboard
│
├── services/
│   └── api_service.py       # OSINT API calls (aiohttp)
│
├── utils/
│   ├── formatters.py        # Result text formatters
│   ├── helpers.py           # Shared utilities
│   ├── logger.py            # Structured logging setup
│   ├── msg_tracker.py       # Bot message cleanup tracker
│   └── rate_limiter.py      # Per-user rate limiting
│
├── payment_qr/
│   └── qr.jpg               # Place your payment QR code here
│
└── assets/screenshots/      # Payment screenshots (auto-created)
```

---

## Deployment

### Railway

```bash
# Push to GitHub, then:
# New Project → Deploy from GitHub repo
# Add env vars in Railway dashboard → Deploy
```

### Render

```bash
# New Web Service → connect GitHub repo
# Build: pip install -r requirements.txt
# Start: python main.py
# Add env vars → Deploy
```

### VPS

```bash
screen -S cww-bot
cd bot && python main.py
# Ctrl+A, D to detach
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

---

## Admin Commands

| Command / Button | Action |
|---|---|
| `/start` | Open bot with correct keyboard |
| `/admin` | Open admin panel (admin only) |
| 👑 Admin Panel | Switch to admin submenu keyboard |
| 🔙 Back | Return to main keyboard |
| 💎 Grant Premium | Grant premium to a user |
| 🚫 Revoke Premium | Revoke premium |
| 📢 Broadcast | Send message to all users |
| 🔐 Ban User | Ban a user by ID |
| ✅ Unban User | Unban a user |
| 📊 Live Statistics | View live bot stats |
| 📝 Logs | View recent search logs |
| ⚡ Server Status | CPU, RAM, disk usage |
| 📂 Export Users | Download user list as TXT |
| 🔄 Lifetime Update | View premium time report |
| ⏸ Freeze (Bot Control) | Pause all premium timers |

---

## Premium Plans

| Plan | Price |
|---|---|
| 1 Day | ₹49 |
| 3 Days | ₹99 |
| 7 Days | ₹149 |
| 15 Days | ₹199 |
| 1 Month | ₹299 |
| 2 Months | ₹449 |
| 3 Months | ₹599 |
| 6 Months | ₹799 |
| 1 Year | ₹1199 |

---

## License

Private. All rights reserved. © CYBER WILD WAVE
