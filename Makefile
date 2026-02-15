.DEFAULT_GOAL := help

SHELL := /usr/bin/env bash

# Source nvm before running any Node/pnpm commands.
NVM_CMD := source ~/.nvm/nvm.sh && nvm use default --silent

.PHONY: help setup dev-api dev-web test-api test-web lint format migrate docker-build

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_-]+:.*##/ {printf "%-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install dependencies (pnpm + uv)
	@$(NVM_CMD) && pnpm install
	@cd apps/api && uv sync

dev-api: ## Run FastAPI dev server
	@cd apps/api && uv run python cli.py serve

dev-web: ## Run Next.js dev server
	@$(NVM_CMD) && pnpm --filter @biblical-evals/web dev

test-api: ## Run API tests with coverage gate
	@cd apps/api && uv run pytest -v --cov=src --cov-report=term-missing --cov-fail-under=85

test-web: ## Run web tests with coverage
	@$(NVM_CMD) && pnpm --filter @biblical-evals/web test:coverage

lint: ## Run linters (ruff + eslint)
	@cd apps/api && uv run ruff check src tests
	@$(NVM_CMD) && pnpm --filter @biblical-evals/web lint

format: ## Run formatters (API only)
	@cd apps/api && uv run ruff format src tests

migrate: ## Run Alembic migrations (upgrade head)
	@cd apps/api && uv run alembic upgrade head

docker-build: ## Build API Docker image
	@docker build -t biblical-evals-api:local apps/api
