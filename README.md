# SmartCart AI

An adaptive e-commerce platform built around a Deep Reinforcement Learning agent
that learns each visitor's preferences in real time. A live A/B dashboard compares
the DRL agent against a classical collaborative-filtering baseline.

🌐 **Live demo:** https://smartcart-ai.vercel.app
📊 **Dashboard:** https://smartcart-ai.vercel.app/dashboard (login required)

---

## What this is

Most "AI recommendation" demos serve a model trained once and never updated.
SmartCart closes the loop: every add-to-cart becomes a reward signal that
retrains the agent, and the dashboard measures whether it's working.

The agent observes user behaviour (views, clicks, cart events), produces
ranked recommendations via a Deep Q-Network, and updates its policy from
real reward signals — all in a working e-commerce frontend a non-technical
visitor can use without knowing any of this is happening.

## Architecture

| Layer | Stack |
|-------|-------|
| Frontend | React + Vite + TypeScript + Tailwind + TanStack Query + Zustand |
| Backend | FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 |
| Database | PostgreSQL (Neon serverless in production) |
| ML | PyTorch DQN with online + target networks, gradient clipping, ε-greedy |
| Auth | JWT access tokens + refresh-token rotation + JTI revocation |
| Deployment | Render (backend) + Vercel (frontend) + GitHub Actions CI/CD |

## What's interesting under the hood

- **PostgreSQL-backed experience replay buffer** — durable across restarts, queryable for offline analysis, no separate Redis/memcached dependency at MVP scale
- **Reward attribution baked into the schema** — `cart_events.recommendation_context` JSONB tracks which policy and model produced each conversion, enabling honest A/B reporting
- **Auto-promotion with guard rails** — new model checkpoints are gated on a 10% loss-improvement margin and a minimum step count, preventing thrashing on noise
- **Dual training triggers** — reactive (every N cart events) and cadence-based (every 60s), serialised through a single mutex to prevent overlap
- **Stratified minibatch sampling** — guarantees non-zero-reward episodes appear in every batch so view/click noise doesn't drown the gradient signal
- **Sub-bundle lazy loading** — storefront cold-paint stays under 60KB; the dashboard's recharts dependency only downloads on `/dashboard` navigation

## Local development

### Prerequisites

- Python 3.11+
- Node 18+
- PostgreSQL 15+ (locally, or via Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Create .env from .env.example and fill in DATABASE_URL + JWT_SECRET_KEY
cp .env.example .env

# Apply migrations
alembic upgrade head

# Seed the catalogue (Amazon Reviews 2023, ~800 products)
python -m scripts.seed_amazon_catalogue

# Run
uvicorn app.main:app --reload
```

Backend serves on http://localhost:8000. Swagger UI at /docs.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend on http://localhost:5173.

## Project structure


SmartCart/
├── backend/
│   ├── app/
│   │   ├── ml/                  # DRL inference + training (PyTorch, replay buffer, baseline)
│   │   ├── models/              # SQLAlchemy ORM
│   │   ├── routers/             # FastAPI route handlers
│   │   ├── schemas/             # Pydantic request/response
│   │   ├── security/            # JWT, password hashing, auth dependencies
│   │   └── services/            # Business logic + telemetry queries
│   ├── alembic/                 # Database migrations
│   └── scripts/                 # Catalogue seeder, training utilities
└── frontend/
└── src/
├── api/                 # Typed HTTP client per backend router
├── components/          # UI components by domain
├── hooks/               # TanStack Query + Zustand wrappers
├── pages/               # Lazy-loaded route components
└── store/               # Zustand stores (auth, session)


## Author


**Adejokun Ibukunoluwa** — Lagos, Nigeria
[GitHub](https://github.com/IAdejokun) · [LinkedIn](https://www.linkedin.com/in/adejokun-ibukunoluwa/) · adejokunibk@gmail.com

Built as part of an MSc Computer Science research portfolio demonstrating how
applied AI/ML and security research translate to production-shaped software.