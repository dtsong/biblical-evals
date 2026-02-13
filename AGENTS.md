# AGENTS.md

Guidance for AI coding agents working in this repository.

## Mission

Build and maintain a reliable evaluation platform for biblical/theological LLM responses, while preserving current architecture and quality gates.

## Repo Context

- Monorepo with two apps:
  - `apps/api`: FastAPI + async SQLAlchemy + Pydantic v2
  - `apps/web`: Next.js 14 + React 18 + Auth.js v5 beta
- Shared auth model: HS256 JWT, signed in web, verified in API via shared `NEXTAUTH_SECRET`.
- IaC and deployment logic in `terraform/` and `.github/workflows/`.

## Non-Negotiables

- Do not commit secrets, `.env` files, credential material, or local tokens.
- Keep auth compatibility intact (`NEXTAUTH_SECRET` parity across web/api).
- Do not lower test coverage thresholds:
  - API: 85%
  - Web: 80%
- Avoid destructive git operations unless explicitly requested.

## Local Commands

Use these exact command families when validating changes.

### Node/pnpm commands

Always source nvm first:

```bash
source ~/.nvm/nvm.sh && nvm use default --silent && <command>
```

Examples:

- `source ~/.nvm/nvm.sh && nvm use default --silent && pnpm --filter @biblical-evals/web dev`
- `source ~/.nvm/nvm.sh && nvm use default --silent && pnpm --filter @biblical-evals/web test:coverage`

### API commands (`apps/api`)

- `uv sync`
- `uv run ruff check src tests`
- `uv run ruff format --check src tests`
- `uv run pytest -v --cov=src --cov-report=term-missing --cov-fail-under=85`
- `uv run python cli.py serve`

## Coding Conventions

### Python (API)

- Python 3.11+ with type hints on function signatures.
- Async-first for route handlers and DB operations.
- Ruff config in `apps/api/pyproject.toml` (line length 88).
- Put tests in `apps/api/tests/`, favor focused unit tests with stubs/mocks over brittle integration tests unless integration behavior is the target.

### TypeScript (Web)

- TS strict mode is enabled; keep types explicit where useful.
- Use `@/*` path alias (`apps/web/src/*`).
- Use Vitest + Testing Library for component/module tests.
- Keep coverage-relevant tests near the changed module when practical.

## Change Heuristics

- If you change API routes/logic, update or add tests under `apps/api/tests/`.
- If you change API client/auth/middleware/UI behavior, add/update web tests in `apps/web/src/**/*.test.ts(x)`.
- If you add env vars or configuration fields, update both:
  - `.env.example` files
  - docs/scripts that generate env (`scripts/setup-env.sh` when applicable)
- If you alter CI behavior, validate impacted local commands before finalizing.

## Files to Keep in Sync

- Coverage and test scripts: `apps/web/package.json`, `apps/web/vitest.config.ts`, `.github/workflows/ci.yml`
- Auth contract: `apps/web/src/lib/auth.ts`, `apps/api/src/core/jwt.py`, `apps/api/src/dependencies/auth.py`
- API base URL and token flow: `apps/web/src/lib/api.ts`, `apps/web/src/app/api/auth/token/route.ts`

## Pre-PR Checklist for Agents

- Relevant lint/type/test commands pass locally.
- Coverage thresholds remain satisfied.
- No generated artifacts are staged (`coverage/`, `.coverage`, `__pycache__`, etc.).
- Docs updated when behavior/setup changed.
