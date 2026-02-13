# Biblical Evals

A monorepo for evaluating LLM responses to biblical and theological questions.

It includes:

- A FastAPI backend for evaluations, scoring, and report generation.
- A Next.js frontend for running evaluations and reviewing model responses.
- Terraform and GitHub Actions workflows for CI and deployment.

## Architecture

- `apps/api`: FastAPI app, SQLAlchemy models, scoring/reporting logic, tests.
- `apps/web`: Next.js 14 app, Auth.js login, API client, UI and tests.
- `terraform`: infrastructure modules (Cloud Run, Cloud SQL, IAM/OIDC).
- `scripts/setup-env.sh`: helper to generate local `.env.local` files (optionally push Vercel env vars).

## Prerequisites

- Node.js 20+ and pnpm
- Python 3.11+ and `uv`
- PostgreSQL (local dev defaults to `localhost:5432`)

## Quick Start

1) Install workspace dependencies

```bash
source ~/.nvm/nvm.sh && nvm use default --silent && pnpm install
```

2) Install API dependencies

```bash
cd apps/api && uv sync
```

3) Configure environment files (choose one)

- Copy examples manually:

```bash
cp apps/api/.env.example apps/api/.env.local
cp apps/web/.env.example apps/web/.env.local
```

- Or generate from GCP secrets:

```bash
./scripts/setup-env.sh
```

4) Run services

- API:

```bash
cd apps/api && uv run python cli.py serve
```

- Web:

```bash
source ~/.nvm/nvm.sh && nvm use default --silent && pnpm --filter @biblical-evals/web dev
```

## Development Commands

From repo root:

- Lint all: `source ~/.nvm/nvm.sh && nvm use default --silent && pnpm -r lint`
- Typecheck all: `source ~/.nvm/nvm.sh && nvm use default --silent && pnpm -r typecheck`

API (`apps/api`):

- Lint: `uv run ruff check src tests`
- Format check: `uv run ruff format --check src tests`
- Tests + coverage: `uv run pytest -v --cov=src --cov-report=term-missing --cov-fail-under=85`

Web (`apps/web`):

- Lint: `source ~/.nvm/nvm.sh && nvm use default --silent && pnpm lint`
- Typecheck: `source ~/.nvm/nvm.sh && nvm use default --silent && pnpm typecheck`
- Tests + coverage: `source ~/.nvm/nvm.sh && nvm use default --silent && pnpm test:coverage`

## CI Gates

GitHub Actions (`.github/workflows/ci.yml`) enforces:

- API lint + tests with coverage fail-under **85%**
- Web lint + typecheck + tests with coverage fail-under **80%**
- Terraform format/validate checks

## Environment Notes

- `NEXTAUTH_SECRET` must match between web and API for JWT verification.
- `NEXT_PUBLIC_API_URL` points the frontend to the API base URL.
- `ADMIN_EMAILS` defines admin allowlist emails (comma-separated) for access approvals.
- Do not commit `.env*`, coverage outputs, or cache artifacts.

## Closed Beta Access Flow

- Users can sign in with Google, but non-approved users are routed to `/access/pending`.
- Pending users can submit an access request from that page.
- Admins can approve/reject users at `/admin/access`.
- API access is enforced server-side; non-approved users receive `403 ACCESS_PENDING`.

## Deployment

- API deploy workflow: `.github/workflows/deploy-api.yml`
- Main target: Google Cloud Run (`trainerlab-prod`, `us-west1`)
