# Twinkle Kids ✦

**Cute Styles for Little Smiles.** A premium children's clothing store: Next.js storefront and admin
UI, FastAPI backend, PostgreSQL (Neon).

```
twinkle-kids/
  frontend/          Next.js 16 · React 19 · TypeScript · CSS Modules · Lucide
  backend/           FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · psycopg 3
  docs/              architecture.md · implementation-plan.md
  docker-compose.yml Local PostgreSQL (optional)
```

See [docs/architecture.md](docs/architecture.md) for the design and
[docs/implementation-plan.md](docs/implementation-plan.md) for the phased roadmap.

## Prerequisites

- Node.js **22+** and npm
- Python **3.12+** (developed on 3.14)
- Optional: Docker Desktop (local Postgres), or a Neon project

## 1. Backend (FastAPI) — http://localhost:8000

PowerShell (Windows):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env          # Neon values come from <repo>/.env.local
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

macOS / Linux / Git Bash:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Git Bash: source .venv/Scripts/activate
pip install -e ".[dev]"
cp .env.example .env     # Neon values come from <repo>/.env.local
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Check it: <http://localhost:8000/api/v1/health>, <http://localhost:8000/api/v1/health/ready>,
API docs at <http://localhost:8000/docs>.

### Neon (PostgreSQL + Object Storage)

The repo is linked to Neon project **Twinkle_Kids** (`floral-moon-84030079`, branch `production`,
`aws-us-east-2`). `neon.ts` declares the services; buckets: `media` (public_read, storefront
images) and `assets` (private).

```bash
npm i -g neon            # Neon CLI
neon login               # once per machine (a human completes the browser sign-in)
neon env pull            # writes Neon variables into <repo>/.env.local (git-ignored)
neon deploy              # only after editing neon.ts: provisions services + pulls env
```

How configuration is loaded by the backend (highest priority first):

| Source | Contains |
| --- | --- |
| process environment | production hosts inject everything here |
| `backend/.env` | app settings (`APP_ENV`, `SECRET_KEY`, `ADMIN_API_TOKEN`, ...) |
| `<repo>/.env.local` | **Neon-managed**: `DATABASE_URL` (pooled), `DATABASE_URL_UNPOOLED` (direct, used by Alembic), `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL_S3`, `AWS_REGION`, `NEON_BRANCH` |

Next.js never reads the repo-root `.env.local` (only `frontend/.env*`), so database and storage
credentials cannot reach the browser.

**Offline alternatives:** delete/rename the root `.env.local` (or set `DATABASE_URL=sqlite:///./twinkle_dev.db`
in `backend/.env`) to run with SQLite + in-memory storage; or use Docker Postgres on port 5433
(`docker compose up -d db`, `DATABASE_URL=postgresql://twinkle:twinkle@localhost:5433/twinkle_kids`).

### Media API (temporary admin guard)

Until Phase 3 admin auth, admin media endpoints require `X-Admin-Token: <ADMIN_API_TOKEN>`
(set in `backend/.env`; endpoints return 503 when it is unset).

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/admin/media` | multipart upload: `file`, `purpose`, `visibility`, `alt_text` |
| `GET /api/v1/admin/media` / `GET /api/v1/admin/media/{id}` | list / inspect |
| `DELETE /api/v1/admin/media/{id}` | delete row, then object |
| `GET /api/v1/media/{id}` | public metadata + URL (public assets only) |

Accepted: JPEG, PNG, WebP, AVIF up to 5 MiB (`MEDIA_MAX_UPLOAD_BYTES`), verified by decoding the
bytes (SVG and spoofed types are rejected).

## 2. Frontend (Next.js) — http://localhost:3000

```bash
cd frontend
npm install
cp .env.example .env.local          # PowerShell: Copy-Item .env.example .env.local
npm run dev
```

Open <http://localhost:3000> and <http://localhost:3000/status> (shows live API + database health).

## Quality checks

| Where | Command | What it runs |
| --- | --- | --- |
| backend | `pytest` | unit, integration, migration and architecture-rule tests (offline) |
| backend | `pytest -m live` | real Neon Postgres CRUD + Object Storage upload/retrieval (self-cleaning) |
| backend | `alembic upgrade head` then `alembic check` | apply migrations; detect model/migration drift |
| backend | `ruff check . && ruff format --check .` | lint + formatting |
| backend | `mypy` | strict type checking |
| frontend | `npm run check` | ESLint + `tsc --noEmit` + Vitest |
| frontend | `npm run build` | production build |
| frontend | `npx playwright install chromium` (once), then `npm run test:e2e` | e2e on desktop + mobile; starts the dev server itself |

(On Windows without an activated venv, prefix backend tools with `.\.venv\Scripts\`.)

## Environment & secrets

- `backend/.env.example` and `frontend/.env.example` document every variable.
- Real `.env` / `.env.local` files are git-ignored — never commit them.
- In `APP_ENV=production` the API refuses to start with the dev `SECRET_KEY`, a SQLite database, or
  `DEBUG=true`.

## Scope notes

No payment gateway and no customer-facing order tracking in this version. WhatsApp orders are
recorded as enquiries that staff confirm — opening WhatsApp is not treated as a sent message.

Admin Creadentials:
Email - oddtechteam
Password - Twinkle_Kids@26
