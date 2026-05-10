# Railway Deployment

This project deploys to Railway as **four services** in a single project:

| Service     | Type            | Source / Image           | Config file                               |
| ----------- | --------------- | ------------------------ | ----------------------------------------- |
| `backend`   | App (Nixpacks)  | `backend/`               | `deploy/backend.railway.json`             |
| `frontend`  | App (Nixpacks)  | `frontend/`              | `deploy/frontend.railway.json`            |
| `postgres`  | Managed plugin  | Railway Postgres         | (provisioned via Railway dashboard)       |
| `redis`     | Managed plugin  | Railway Redis            | (provisioned via Railway dashboard)       |

## Environment variables

Set on the **backend** service:

- `DATABASE_URL` — injected from the Postgres plugin (rewrite scheme to `postgresql+asyncpg://`)
- `REDIS_URL` — injected from the Redis plugin
- `SECRET_KEY` — 32+ char random string
- `ALLOWED_ORIGINS` — public frontend URL (comma-separated for multiple)
- `OPENAI_API_KEY`
- `GOOGLE_SHEETS_CREDENTIALS_JSON` — JSON string of service-account credentials
- `GLOBAL_UTM_PREFIX`
- `SERVICE_ACCOUNT_EMAIL`

Set on the **frontend** service:

- `VITE_API_BASE_URL` — public backend URL
- `VITE_SERVICE_ACCOUNT_EMAIL` — surfaced in the New Campaign modal

## Service config files

Each app service points to its own `*.railway.json` via the Railway dashboard
(`Settings → Config-as-code path`). Both files pin a Nixpacks build and an
explicit start command; the backend's start command runs Alembic migrations
before launching `uvicorn`.

## Health check

The backend exposes `GET /health` returning `{"status": "ok"}`. Railway is
configured to hit this path with a 30s timeout.
