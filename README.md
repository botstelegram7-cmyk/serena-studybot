<div align="center">

<!-- ANIMATED HEADER -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:6C63FF,100:FF6584&height=200&section=header&text=SerenaStudyBot&fontSize=60&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=🎓%20AI-Powered%20Telegram%20Study%20Bot&descAlignY=58&descSize=20" width="100%"/>

<!-- ANIMATED TYPING -->
<a href="https://git.io/typing-svg">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=22&pause=1000&color=6C63FF&center=true&vCenter=true&multiline=true&width=700&height=80&lines=SSC+%7C+UPSC+%7C+JEE+%7C+RAILWAY;2025-26+PYQ+%7C+AI+Doubt+Solver+%7C+Testbook-style+Analysis" alt="Typing SVG" />
</a>

<br/>

<!-- BADGES ROW 1 -->
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/serena_studybot)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-2.0-blue?style=for-the-badge&logo=telegram&logoColor=white)](https://pyrogram.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com/atlas)

<!-- BADGES ROW 2 -->
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Render](https://img.shields.io/badge/Render-Deployed-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Live%20🟢-success?style=for-the-badge)](https://t.me/serena_studybot)

<!-- BADGES ROW 3 -->
[![AI](https://img.shields.io/badge/AI-Groq%20%7C%20Gemini%20%7C%20SambaNova-FF6B6B?style=for-the-badge&logo=openai&logoColor=white)]()
[![Exams](https://img.shields.io/badge/Exams-SSC%20%7C%20UPSC%20%7C%20JEE%20%7C%20Railway-purple?style=for-the-badge)]()
[![Updated](https://img.shields.io/badge/Updated-2025--26-orange?style=for-the-badge)]()

<br/>

<!-- ANIMATED STATS -->
<img src="https://komarev.com/ghpvc/?username=serena-studybot&label=Bot+Views&color=6C63FF&style=for-the-badge" alt="views"/>

</div>

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [🤖 AI Providers](#-ai-providers)
- [📁 Project Structure](#-project-structure)
- [🚀 Deploy on Render](#-deploy-on-render)
- [🐳 Local Development](#-local-development)
- [⚙️ Environment Variables](#️-environment-variables)
- [📸 Image Setup](#-image-setup)
- [💬 Bot Commands](#-bot-commands)
- [📊 How It Works](#-how-it-works)
- [👑 Credits](#-credits)

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎯 Mock Tests
- ✅ **Poll-based** inline button tests
- 📅 **Real PYQ** with exam name + year tag
- 💀 **Extreme Mode** — top 1% level
- 🗂 **Topic-wise** targeted practice
- 📊 **Testbook-style** analysis report
- 🏆 Rank estimate vs actual cutoffs

</td>
<td width="50%">

### 🤖 AI Doubt Solver
- ✏️ **Rough copy style** for Maths
- 📖 Theory answers with memory tricks
- ⚡ SSC-style short methods
- 🌐 English · हिंदी · বাংলা
- 🧠 Smart Math vs Theory detection
- 💡 2025-26 exam-specific tips

</td>
</tr>
<tr>
<td width="50%">

### 📚 Study Features
- 📤 Owner can upload PYQ PDFs/Images
- 🔍 OCR-based question extraction
- 💰 Free AI APIs (zero cost)
- 📅 Daily quiz at 8 AM IST
- 🌅 Morning motivation messages
- 🌙 Night relief messages

</td>
<td width="50%">

### ⚙️ Technical
- 🐳 Docker compatible
- 🔄 Multi-provider AI fallback
- 📈 Progress tracking & leaderboard
- 🌐 Multilingual support
- 🔒 Owner-only admin commands
- ♻️ Auto session management

</td>
</tr>
</table>

---

## 🎓 Supported Exams

| Exam | Coverage |
|------|----------|
| 📋 **SSC** | CGL · CHSL · MTS · GD · CPO · JE · Stenographer |
| 🏛 **UPSC** | CSE Prelims · NDA · CDS · CAPF · IFS |
| ⚗️ **JEE** | Mains (Jan/Apr) · Advanced · 2025-26 Pattern |
| 🚂 **RAILWAY** | NTPC · Group D · ALP · JE · 2025-26 |

---

## 🤖 AI Providers

> **100% Free** — No paid APIs required!

| Provider | Use | Free Limit | Get Key |
|----------|-----|-----------|---------|
| 🟢 **Groq** | Primary AI | 14,400 req/day | [console.groq.com](https://console.groq.com) |
| 🟡 **Gemini Flash** | Fallback | 1,500 req/day | [aistudio.google.com](https://aistudio.google.com) |
| 🔵 **SambaNova** | Emergency | Generous | [cloud.sambanova.ai](https://cloud.sambanova.ai) |
| 🌐 **OpenTDB** | Quiz API | Unlimited | No key needed |
| 🌐 **TriviaAPI** | Quiz API | Unlimited | No key needed |

**Fallback Chain:** `Groq → Gemini → SambaNova` (auto-switches if one fails)

---

## 📁 Project Structure

```
serena-studybot/
│
├── 📄 main.py                  # Entry point — Bot + Web server
├── 📄 bot.py                   # All handlers & commands
├── 📄 config.py                # Settings & environment variables
├── 📄 database.py              # MongoDB operations
│
├── 📂 modules/
│   ├── 🤖 ai_helper.py         # Groq → Gemini → SambaNova fallback
│   ├── 📝 mock_test.py         # Test engine + analysis
│   ├── 💡 question_gen.py      # PYQ AI question generator (2025-26)
│   ├── 🌐 quiz_apis.py         # External free quiz APIs
│   ├── 🧠 doubt_solver.py      # AI doubt solver (rough copy style)
│   ├── 📤 parser.py            # PDF/Image/TXT question extractor
│   ├── 📊 tracker.py           # Progress + leaderboard
│   └── ⏰ scheduler.py         # Daily quiz + AI greetings
│
├── 🐳 Dockerfile
├── 🐳 docker-compose.yml
├── 📋 requirements.txt
├── 🔑 .env.example
└── 📖 README.md
```

---

## 🚀 Deploy on Render

### Step 1 — Prerequisites

Get these free accounts first:

| Service | URL | What You Get |
|---------|-----|-------------|
| Telegram API | [my.telegram.org](https://my.telegram.org) | `API_ID` & `API_HASH` |
| BotFather | [@BotFather](https://t.me/BotFather) | `BOT_TOKEN` |
| MongoDB Atlas | [mongodb.com/atlas](https://mongodb.com/atlas) | `MONGO_URI` |
| Groq | [console.groq.com](https://console.groq.com) | `GROQ_API_KEY` |
| Gemini | [aistudio.google.com](https://aistudio.google.com) | `GEMINI_API_KEY` |
| SambaNova | [cloud.sambanova.ai](https://cloud.sambanova.ai) | `SAMBANOVA_API_KEY` |
| GitHub | [github.com](https://github.com) | For repo hosting |
| Render | [render.com](https://render.com) | For deployment |

---

### Step 2 — MongoDB Atlas Setup

1. Go to [mongodb.com/atlas](https://mongodb.com/atlas) → **Sign up free**
2. Create **Free Cluster** (M0 — 512MB free)
3. **Database Access** → Add user → Username & Password
4. **Network Access** → Add IP → `0.0.0.0/0` (allow all)
5. **Connect** → Drivers → Copy connection string

```
mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/
```

> ⚠️ If password has special chars (`@#!$`), encode them:
> `@` → `%40` | `#` → `%23` | `!` → `%21`

---

### Step 3 — Create Telegram Bot

1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`
3. Choose a name: `Serena Study Bot`
4. Choose username: `your_studybot`
5. Copy the **token** — this is your `BOT_TOKEN`
6. Send `/setcommands` and paste:
```
start - Welcome & exam selection
test - Start mock test
quick - Quick practice test
practice - Subject practice
topic - Topic-wise practice
extreme - Extreme difficulty test
ask - AI doubt solver
myprogress - My performance report
leaderboard - Top scorers
setexam - Set your target exam
language - Change language
stoptest - Stop current test
help - All commands
```

---

### Step 4 — GitHub Setup

1. Go to [github.com](https://github.com) → **New repository**
2. Name: `serena-studybot`
3. Set to **Private** ⚠️ (bot token protection!)
4. Create `.gitignore`:
```
.env
*.session
__pycache__/
*.pyc
sessions/
```
5. Upload all project files
6. **Never upload `.env` file!**

---

### Step 5 — Deploy on Render

1. Go to [render.com](https://render.com) → Sign up with GitHub
2. Click **New** → **Web Service**
3. Connect your GitHub repo
4. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `serena-studybot` |
| **Runtime** | `Docker` |
| **Branch** | `main` |
| **Instance Type** | `Free` |

5. Add **Environment Variables** (see section below)
6. Click **Create Web Service**
7. Wait for deployment (~3-5 minutes)

---

### Step 6 — UptimeRobot (Keep Bot Alive)

Render free tier sleeps after 15 min inactivity. Fix this:

1. Go to [uptimerobot.com](https://uptimerobot.com) → Free account
2. **Add New Monitor**
3. Settings:
   - Type: `HTTP(s)`
   - URL: `https://your-app.onrender.com/health`
   - Interval: `5 minutes`
4. Save → Bot stays alive 24/7! ✅

---

## 🐳 Local Development

```bash
# Clone repo
git clone https://github.com/yourusername/serena-studybot.git
cd serena-studybot

# Copy env file
cp .env.example .env
# Fill in your credentials in .env

# Run with Docker Compose (includes MongoDB)
docker-compose up --build

# OR run directly with Python
pip install -r requirements.txt
python main.py
```

---

## ⚙️ Environment Variables

Create `.env` file with these values:

```env
# ── TELEGRAM ────────────────────────────────────
# Get from: https://my.telegram.org
API_ID=12345678
API_HASH=abcdef1234567890abcdef

# Get from: @BotFather on Telegram
BOT_TOKEN=1234567890:ABCDEFghijklmnop

# ── DATABASE ────────────────────────────────────
# Get from: https://mongodb.com/atlas → Free cluster
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
DB_NAME=serena_studybot

# ── AI PROVIDERS (All Free!) ────────────────────
# https://console.groq.com → API Keys
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# https://aistudio.google.com → Get API Key
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxx

# https://cloud.sambanova.ai → API Keys
SAMBANOVA_API_KEY=xxxxxxxxxxxxxxxxxxxx

# ── OPTIONAL QUIZ APIs ──────────────────────────
# https://quizapi.io → Register → API Key (100/day free)
QUIZ_API_KEY=

# Free APIs (no key needed, just enable)
OPENTDB_ENABLED=true
TRIVIA_API_ENABLED=true

# ── SERVER ──────────────────────────────────────
PORT=8080

# ── BOT SETTINGS ────────────────────────────────
MAX_DAILY_DOUBTS=30
POLL_TIMER=60
```

---

## 📸 Image Setup

Set custom images for start screen and exam screens:

```
# Method 1 — URL
/setimage START https://your-image-url.jpg
/setimage SSC   https://your-ssc-image.jpg
/setimage UPSC  https://your-upsc-image.jpg
/setimage JEE   https://your-jee-image.jpg
/setimage RAILWAY https://your-railway-image.jpg

# Method 2 — Send a photo to bot, then reply to it:
/setimage SSC

# View all images
/images

# Remove an image
/delimage SSC
```

**Recommended image size:** `800×400px` (landscape)

---

## 💬 Bot Commands

### 👤 User Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome screen + exam selection |
| `/test SSC` | Full mock test (100Q) |
| `/quick SSC 10` | Quick 10-question test |
| `/practice SSC Quant` | Subject practice |
| `/topic SSC Quant Percentage` | Topic-wise practice |
| `/extreme SSC` | 💀 Extreme difficulty (top 1% level) |
| `/ask <question>` | AI doubt solver |
| `/myprogress` | Full performance report |
| `/leaderboard SSC` | Top 10 scorers |
| `/setexam SSC UPSC` | Set your target exams |
| `/language` | Change language (EN/HI/BN) |
| `/stoptest` | Force stop current test |
| `/help` | All commands list |

### 👑 Owner Commands

| Command | Description |
|---------|-------------|
| `/upload SSC Quant 2024 SSC CGL 2024` | Upload PYQ sheet |
| `/setimage START <url>` | Set start screen image |
| `/images` | View all set images |
| `/delimage SSC` | Remove an image |
| `/dbstats` | Question bank statistics |
| `/broadcast <message>` | Message all users |

---

## 📊 How It Works

```
User /test SSC
      │
      ▼
   bot.py  ──────────────────────────────────────────►  mock_test.py
                                                              │
                                          ┌───────────────────┼────────────────────┐
                                          ▼                   ▼                    ▼
                                    database.py        question_gen.py         quiz_apis.py
                                    (PYQ from DB)      (AI-generated PYQ)      (OpenTDB/Trivia)
                                          │                   │                    │
                                          └───────────────────┴────────────────────┘
                                                              │
                                                              ▼
                                                    Inline Button Question
                                                    📅 SSC CGL 2024 (2024)
                                                    Q5/25 | Quant 🟡
                                                              │
                                                    User selects answer
                                                              │
                                                              ▼
                                                    Answer feedback +
                                                    Progress bar +
                                                    Short method trick
                                                              │
                                               (After all questions)
                                                              │
                                                              ▼
                                                    Testbook-style Analysis
                                                    ✅ Score | 🎯 Accuracy
                                                    📊 Subject breakdown
                                                    🏆 Rank estimate
                                                    ❌ Mistakes review
```

---

## ⏰ Auto Schedule

| Time (IST) | Action |
|-----------|--------|
| **6:00 AM** | 🌅 AI-generated personalized morning motivation |
| **8:00 AM** | 📅 3 Daily PYQ questions |
| **9:30 PM** | 🌙 AI-generated night relief message |

---

## 📈 Analysis Report Sample

```
╔══════════════════════════╗
║  🏁 TEST COMPLETE!       ║
╚══════════════════════════╝

👤 Serena | 📋 SSC
████████░░░░ 72%  B+👍 Good

✅ 18  +36pts  | ❌ 5  -2.5pts  | ⏭ 2
📈 33.5/50  | 🎯 78%  | ⏱ 12m34s

┌ 🎯 RANK ESTIMATE
└ 🥉 Top 15% — Safe Zone ✅

📚 SUBJECT ANALYSIS
✅ Quant:   8/10  ▓▓▓▓▓▓▓░  80%
⚠️ English: 5/8   ▓▓▓▓░░░░  62%
✅ Reason:  4/5   ▓▓▓▓▓▓░░  80%
❌ GK:      1/2   ▓▓░░░░░░  50%
```

---

## 👑 Credits

<div align="center">

### 🌟 Developed By

<table>
<tr>
<td align="center" width="50%">
  <a href="https://t.me/TechnicalSerena">
    <img src="https://img.shields.io/badge/Telegram-@TechnicalSerena-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="TechnicalSerena"/>
  </a>
  <br/>
  <b>🎓 Serena</b>
  <br/>
  <sub>Lead Developer · Bot Architecture · AI Integration</sub>
  <br/>
  <sub>Telegram ID: <code>6518065496</code></sub>
</td>
<td align="center" width="50%">
  <a href="https://t.me/Xioqui_Xan">
    <img src="https://img.shields.io/badge/Telegram-@Xioqui__Xan-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Xioqui_Xan"/>
  </a>
  <br/>
  <b>🛠 Xioqui Xan</b>
  <br/>
  <sub>Co-Owner · Testing · Feature Suggestions</sub>
  <br/>
  <sub>Telegram ID: <code>1598576202</code></sub>
</td>
</tr>
</table>

### 🛠 Built With

[![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://pyrogram.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://mongodb.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Groq](https://img.shields.io/badge/Groq-FF6B6B?style=flat-square)](https://groq.com)
[![Gemini](https://img.shields.io/badge/Gemini-4285F4?style=flat-square&logo=google&logoColor=white)](https://aistudio.google.com)

### 💖 Special Thanks

> **Groq** — For blazing fast free AI inference  
> **Google** — For Gemini Flash free tier  
> **MongoDB Atlas** — For free database hosting  
> **Render** — For free deployment platform  
> **OpenTDB & TriviaAPI** — For free quiz questions

</div>

---

<div align="center">

### ⭐ If this helped you, give it a star!

```
╔═══════════════════════════════════════╗
║  ➵⋆🪐ᴛᴇᴄʜɴɪᴄᴀʟ_sᴇʀᴇɴᴀ𓂃              ║
║  Made with 💜 for competitive exam    ║
║  aspirants across India 🇮🇳           ║
╚═══════════════════════════════════════╝
```

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:6C63FF,100:FF6584&height=100&section=footer" width="100%"/>

</div>
