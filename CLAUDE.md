# Biblical Evals — CLAUDE.md

Framework for evaluating LLM responses to biblical and theological questions.

## Architecture

Monorepo with two apps sharing auth via HS256 JWT (NEXTAUTH_SECRET):

```
apps/web/    → Next.js 14 frontend (Vercel)
apps/api/    → FastAPI backend (Cloud Run)
terraform/   → GCP infrastructure (trainerlab-prod, temporary — see #2)
scripts/     → Developer tooling
```

## Commands

```bash
# Frontend (from repo root)
pnpm dev                          # Next.js dev server at :3000
pnpm build                        # Production build
pnpm lint                         # ESLint across all packages
pnpm typecheck                    # TypeScript checking

# Backend (from apps/api/)
uv run uvicorn src.main:app --reload  # API dev server at :8000
uv run ruff check src/ tests/        # Lint
uv run ruff format src/ tests/       # Format
uv run pytest                         # Tests (async, Postgres required)
uv run alembic upgrade head           # Run migrations

# Terraform (from terraform/)
terraform init
terraform plan
terraform apply

# Environment setup
./scripts/setup-env.sh            # Pull secrets from GCP → .env.local
./scripts/setup-env.sh --vercel   # Also push to Vercel
```

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Next.js 14, React 18, Tailwind CSS 3 | `@/*` path alias to `./src/*` |
| Auth | NextAuth.js v5 (beta.30) + Google OAuth | Shared HS256 JWT with backend |
| Charts | Recharts 3 | Report visualizations |
| Backend | FastAPI, Pydantic v2, pydantic-settings | Async everywhere |
| ORM | SQLAlchemy 2 (async) + Alembic | asyncpg driver |
| LLM | LiteLLM | Multi-provider abstraction |
| CLI | Typer | `uv run python -m cli` |
| DB | PostgreSQL 16 (Cloud SQL) | Local: plain Postgres on :5432 |
| IaC | Terraform >= 1.5, Google provider ~> 5.0 | State in GCS |
| CI/CD | GitHub Actions | WIF auth, no service account keys |
| Package mgmt | pnpm (frontend), uv (backend) | pnpm workspaces at root |

## Frontend Conventions

- **TypeScript strict mode** — `strict: true` in tsconfig.json
- **Path alias**: `@/components/Foo` → `src/components/Foo`
- **Design aesthetic**: Editorial/scholarly — warm parchment tones, not tech-startup
  - Display font: Crimson Pro (serif)
  - Body font: Source Sans 3 (sans-serif)
  - Colors: HSL CSS variables — warm amber primary (`--primary: 24 70% 35%`), parchment backgrounds
  - Scoring colors: Red (1) → Orange → Yellow → Green → Dark green (5)
- **Component style**: Tailwind utility classes, no CSS modules
  - Use `clsx` + `tailwind-merge` for conditional classes
  - Icons from `lucide-react`
- **API client**: `apps/web/src/lib/api.ts` — typed fetch wrappers with Bearer auth
- **Types**: Shared types in `apps/web/src/lib/types.ts`
- **Testing**: Vitest + React Testing Library

## Backend Conventions

- **Python 3.11+** — type hints on all function signatures
- **Pydantic v2** for all request/response schemas (in `src/models/`)
- **pydantic-settings** for config (`src/config.py`) — env vars loaded from `.env` / `.env.local`
- **Async throughout** — async def for all route handlers and DB operations
- **Ruff** for linting and formatting (line-length 88)
  - Rules: E, F, I, UP, B, SIM, ASYNC, N, S, C4, PT
  - `S101` (assert) ignored globally; `S105`/`S106` ignored in tests
- **Tests**: pytest + pytest-asyncio (`asyncio_mode = "auto"`)
- **Imports**: isort via ruff, `src` as known first-party
- **JWT verification**: python-jose with HS256, shared NEXTAUTH_SECRET

## Question Format

Questions live in `apps/api/questions/<category>/<subcategory>.yaml`:

```yaml
metadata:
  category: theological
  subcategory: soteriology

questions:
  - id: SOT-001        # Category prefix + sequential number
    text: "..."
    type: theological   # theological | factual | interpretive
    difficulty: intermediate  # easy | intermediate | advanced
    scripture_references: ["James 2:14-26", "Ephesians 2:8-9"]
    evaluation_notes: "What to look for in model responses"
    denominational_sensitivity: high  # low | medium | high
    tags: ["justification", "pauline"]
```

ID prefixes: `SOT` (soteriology), `CHR` (christology), `BIB` (biblical knowledge), `ETH` (ethics), `NAR` (biblical narrative).

## Terraform Conventions

- **Temporary home**: All resources in `trainerlab-prod` with `biblical-evals-*` prefixes (migration tracked in #2)
- **Modules**: `modules/cloud_run/` and `modules/cloud_sql/` — adapted from trainerlab patterns
- **State**: GCS backend at `trainerlab-tfstate-1d22e2f5`, prefix `biblical-evals/app`
- **Naming**: WIF pool `github-biblical-evals`, SA `gh-biblical-evals` (avoid collisions with trainerlab)
- **Style**: Use `depends_on` at module level (not variable passthrough)

## Git Conventions

- **Commit format**: `type(scope): description` — types: `feat`, `fix`, `chore`, `infra`, `content`, `docs`
- **Branch**: `main` only for now; feature branches as complexity grows
- **CI**: Path-filtered — Python changes trigger backend checks, web changes trigger frontend checks, terraform changes trigger validate

## Environment & Secrets

- **Local dev**: `./scripts/setup-env.sh` generates `.env.local` files from GCP Secret Manager
- **Secrets in GCP**: All prefixed `biblical-evals-*` (db-password, nextauth-secret, openai-api-key, anthropic-api-key, google-ai-api-key)
- **GitHub secret**: `GCP_PROJECT_NUMBER` for WIF authentication
- **Never commit**: `.env`, `.env.local`, API keys, credentials
