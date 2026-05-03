# EngageX (Working Title)

**Intelligent Referral, Task & Engagement Engine for Discord Communities**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green.svg)](https://fastapi.tiangolo.com)
[![Discord.py](https://img.shields.io/badge/discord.py-2.7-blue.svg)](https://discordpy.readthedocs.io)
[![n8n](https://img.shields.io/badge/n8n-Automation-FF6D5A.svg)](https://n8n.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Async-336791.svg)](https://postgresql.org)
[![Railway](https://img.shields.io/badge/Railway-Deploy-0B0D0E.svg)](https://railway.app)

EngageX is a behavior-driven growth engine for Discord communities. It tracks user actions, rewards quality engagement, detects fraud silently, and drives retention through gamification loops — all powered by n8n automation and AI scoring.

---

## Architecture

```mermaid
graph LR
    A[Discord Users] -->|Slash Commands + Messages| B[discord.py Bot]
    B -->|Activity Events| C[FastAPI API]
    C -->|Read/Write| D[(PostgreSQL)]
    E[n8n Cron] -->|POST /cron/*| C
    C -->|AI Scoring| F[OpenRouter API]
    E -->|Fraud Check| C
    D -->|Data| E
    C -->|Re-engagement DMs| B
```

```mermaid
graph TB
    subgraph User-Facing
        A[/points] --> G[Check Stats]
        B[/leaderboard] --> H[Rankings]
        C[/profile] --> I[Full Profile]
        D[/tasks] --> J[Quest Board]
        E[/referrals] --> K[Referral Stats]
        F[/submit] --> L[AI Content Score]
    end

    subgraph Passive Tracking
        M[on_message] --> N[Streak Update]
        O[on_member_join] --> P[Auto-Register]
    end

    subgraph Automation Layer
        Q[24h Cron] --> R[Reset Streaks]
        Q --> S[Apply Decay]
        Q --> T[Re-engage DMs]
        U[6h Cron] --> V[Fraud Detection]
    end
```

---

## How It Works

Instead of the traditional `command → response` bot model, EngageX follows:

```
observe → analyze → decide → act → adapt
```

Every user interaction is logged, analyzed, and used to drive personalized engagement. No manual moderation needed.

```mermaid
sequenceDiagram
    participant User
    participant Bot
    participant API
    participant DB
    participant AI
    participant n8n

    User->>Bot: /submit "My content..."
    Bot->>API: Score content
    API->>AI: Evaluate quality
    AI-->>API: Score: 85/100
    API->>DB: Award points + update streak
    API->>DB: Check hidden quests
    API-->>Bot: 25 pts (x1.5 streak bonus)
    Bot-->>User: Content scored! 🎉

    Note over n8n,DB: 6 hours later...
    n8n->>API: POST /check-fraud
    API->>DB: Scan for suspicious patterns
    API-->>n8n: Risk assessment complete
```

---

## Screenshots

### Discord Bot

| `/leaderboard` | `/profile` |
|:---:|:---:|
| ![Leaderboard](assets/discord-leaderboard.png) | ![Profile](assets/discord-profile.png) |

| `/points` | `/submit` Result |
|:---:|:---:|
| ![Points](assets/discord-points.png) | ![Submit Result](assets/discord-submit-result.png) |

| `/referrals` | AI Content Scoring |
|:---:|:---:|
| ![Referrals](assets/discord-referrals.png) | ![Submit Command](assets/discord-submit-cmd.png) |

### n8n Automation Workflows

| Streak & Decay Cron (24h) | Fraud Detection (6h) |
|:---:|:---:|
| ![Streak Decay Cron](assets/n8n-streak-decay-cron.png) | ![Fraud Detection](assets/n8n-fraud-detection.png) |

### Railway Infrastructure

| Infrastructure Topology |
|:---:|
| ![Railway Infrastructure](assets/railway-infrastructure.png) |

---

## Core Modules

| Module | What It Does |
|--------|-------------|
| **Referral Engine** | Validates referrals, scores quality over quantity, rewards only high-quality signups |
| **AI Content Scoring** | Uses OpenAI to evaluate content originality, engagement potential, and effort |
| **Streak System** | Tracks daily activity, rewards consistency with bonus points and multipliers |
| **Fraud Detection** | Silently flags suspicious behavior — referral spam, bot patterns, duplicate content |
| **Hidden Quests** | Surprise rewards triggered by behavior milestones (first referral, 7-day streak, etc.) |
| **Point Decay** | Inactive users lose points over time, keeping the leaderboard competitive |
| **Reputation System** | Weighted scoring — content creation > referrals > participation. Fraud = penalty |
| **Re-engagement Engine** | Automated nudges to inactive users via Discord DMs |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Bot Interface | discord.py |
| API Backend | FastAPI + Uvicorn |
| Automation | n8n (Railway) |
| Database | PostgreSQL (Railway, async via asyncpg) |
| AI Scoring | OpenAI / OpenRouter |
| ORM | SQLAlchemy (async) |
| Package Manager | Poetry |

---

## Data Flow

```mermaid
graph LR
    subgraph Engagement Loop
        A[User Action] --> B[Log Activity]
        B --> C[Update Streak]
        C --> D[Award Points]
        D --> E[Check Quests]
        E --> F[Update Leaderboard]
        F --> A
    end

    subgraph Anti-Abuse Loop
        G[n8n Cron 6h] --> H[Scan Patterns]
        H --> I{Suspicious?}
        I -->|Yes| J[Shadow Ban]
        I -->|No| K[Clear]
        J --> L[Reduce Rewards]
    end

    subgraph Retention Loop
        M[n8n Cron 24h] --> N[Apply Decay]
        N --> O[Find Inactive]
        O --> P[Send Nudge DM]
        P --> Q[User Returns]
        Q --> A
    end
```

---

## Discord Bot Commands

| Command | Description |
|---------|------------|
| `/points` | Check your points, streak, and tier |
| `/leaderboard` | See the top 10 users |
| `/profile` | Full profile with recent activity |
| `/tasks` | Available tasks and completion status |
| `/referrals` | Your referral stats and quality scores |
| `/submit <content>` | Submit content for AI scoring |

The bot also passively tracks activity — every message updates streaks and logs engagement.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/points/{discord_id}` | Get user points and streak |
| `GET` | `/api/profile/{discord_id}` | Full user profile |
| `GET` | `/api/leaderboard` | Top users by points |
| `GET` | `/api/tasks/{discord_id}` | Available and completed tasks |
| `POST` | `/api/user` | Register new user |
| `POST` | `/api/referral` | Process a referral |
| `POST` | `/api/content-score` | Score content with AI |
| `POST` | `/api/cron/streak-reset` | Daily cron: reset inactive streaks |
| `POST` | `/api/cron/decay` | Daily cron: apply point decay |
| `POST` | `/api/cron/reengage` | Cron: send re-engagement nudges |
| `POST` | `/api/check-fraud` | Run fraud detection on a user |

---

## n8n Workflows

| Workflow | Schedule | What It Does |
|----------|----------|-------------|
| Streak & Decay Cron | Every 24h | Resets streaks for inactive users, applies point decay, sends re-engagement DMs |
| Fraud Detection | Every 6h | Scans for suspicious patterns — referral spam, bot behavior, duplicate content |

Import the JSON files from `app/n8n/` into your n8n instance to activate them.

---

## Project Structure

```
EngageX/
├── app/
│   ├── main.py              # Entry point (FastAPI + Discord bot)
│   ├── config.py            # Environment configuration
│   ├── database.py          # SQLAlchemy async engine + sessions
│   ├── models/
│   │   └── models.py        # User, Referral, Task, UserTask, ActivityLog
│   ├── routes/
│   │   └── api.py           # REST endpoints + n8n webhook receivers
│   ├── bot/
│   │   └── discord_bot.py   # Slash commands + message listeners
│   ├── logic/
│   │   ├── referral.py      # Referral validation + quality scoring
│   │   ├── scoring.py       # AI content scoring (OpenAI/OpenRouter)
│   │   ├── streaks.py       # Daily streak tracking + bonuses
│   │   ├── fraud.py         # Silent fraud detection
│   │   ├── decay.py         # Point decay for inactive users
│   │   ├── quests.py        # Hidden surprise quest engine
│   │   ├── reengage.py      # Re-engagement nudge system
│   │   └── reputation.py    # Weighted reputation + tiers
│   └── n8n/
│       ├── streak_decay_cron.json
│       └── fraud_detection.json
├── assets/                   # Screenshots for README
├── tests/
│   └── test_logic.py        # 27 unit tests for core logic
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## Database Schema

```mermaid
erDiagram
    USERS ||--o{ REFERRALS : "makes"
    USERS ||--o{ USER_TASKS : "completes"
    USERS ||--o{ ACTIVITY_LOGS : "generates"
    TASKS ||--o{ USER_TASKS : "assigned to"

    USERS {
        int id PK
        string discord_id
        string username
        int points
        float reputation_score
        int streak
        date last_active
        bool fraud_flag
        bool shadow_banned
        datetime created_at
    }

    REFERRALS {
        int id PK
        string referrer_id FK
        string referred_user
        string status
        float quality_score
        datetime created_at
    }

    TASKS {
        int id PK
        string name
        string description
        int points
        string type
        bool hidden
        string unlock_condition
    }

    USER_TASKS {
        int id PK
        string user_id FK
        int task_id FK
        string status
        datetime completed_at
    }

    ACTIVITY_LOGS {
        int id PK
        string user_id FK
        string action
        jsonb metadata
        datetime created_at
    }
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/KaranMakani/EngageX.git
cd EngageX
poetry install
```

### 2. Configure environment

```bash
cp .env.example .env
# edit .env with your actual keys
```

### 3. Environment Variables

| Variable | Description |
|----------|------------|
| `DISCORD_TOKEN` | Your Discord bot token |
| `DATABASE_URL` | PostgreSQL connection string (asyncpg format) |
| `OPENAI_API_KEY` | OpenAI or OpenRouter API key |
| `OPENAI_BASE_URL` | API base URL (use OpenRouter URL if applicable) |
| `N8N_WEBHOOK_URL` | Your n8n instance URL |
| `APP_URL` | Your API URL (for n8n callbacks) |

### 4. Set up PostgreSQL on Railway

1. Create a new Railway project
2. Add a PostgreSQL service
3. Copy the `DATABASE_PUBLIC_URL` into your `.env`
4. Change the scheme from `postgresql://` to `postgresql+asyncpg://`

### 5. Deploy n8n on Railway

1. Add an n8n service to the same Railway project
2. Set environment variables for authentication
3. Import the workflow JSONs from `app/n8n/`

### 6. Run locally

```bash
# start the API + Discord bot
poetry run uvicorn app.main:app --reload
```

### 7. Deploy API to Railway (optional)

The Dockerfile supports an `API_ONLY=1` mode that runs the FastAPI server without the Discord bot. This is useful for Railway deployments where n8n needs to reach your API.

---

## Anti-Abuse Strategy

EngageX handles fraud silently — no public callouts, no drama:

- **Duplicate detection**: Identifies repeat referrals and content
- **Rate limiting**: Flags suspicious activity volumes
- **Behavior analysis**: Detects bot-like timing patterns
- **Silent penalties**: Shadow-banned users get reduced rewards without knowing
- **Reputation weighting**: Fraud signals tank your reputation score

---

## Gamification Loops

```mermaid
graph TB
    subgraph Streak Rewards
        A[3 Day Streak] -->|Bonus| B[+10% Points]
        C[7 Day Streak] -->|1.5x Multiplier| D[+50% Points]
        E[14 Day Streak] -->|2x Multiplier| F[+100% Points]
        G[30 Day Streak] -->|Legend Status| H[+200% Points]
    end

    subgraph Hidden Quests
        I[First Referral] -->|First Blood| J[+20 pts]
        K[7 Day Streak] -->|Consistency is Key| L[+50 pts]
        M[3 Content Submissions] -->|Voice of Community| N[+30 pts]
    end

    subgraph Point Decay
        O[3 Days Inactive] -->|Grace Period| P[No Decay]
        Q[4+ Days Inactive] -->|2% Daily| R[Compound Decay]
    end
```

---

## Running Tests

```bash
poetry run pytest tests/ -v
```

27 tests covering scoring, streaks, fraud detection, reputation tiers, and hidden quest conditions.

---

## License

MIT
