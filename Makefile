.PHONY: help install dev dev-backend dev-frontend test test-backend test-frontend lint typecheck seed import-data docker-up docker-down clean

help:
	@echo "Zero-Friction Transit Orchestrator Development Commands:"
	@echo "  make install        Install all backend and frontend dependencies"
	@echo "  make dev            Run both backend and frontend development servers"
	@echo "  make dev-backend    Run FastAPI development server"
	@echo "  make dev-frontend   Run Next.js development server"
	@echo "  make test           Run all backend and frontend tests"
	@echo "  make test-backend   Run pytest test suite"
	@echo "  make test-frontend  Run Vitest test suite"
	@echo "  make lint           Run code linters (ruff, eslint)"
	@echo "  make typecheck      Run typecheckers (mypy, tsc)"
	@echo "  make seed           Seed baseline demo database"
	@echo "  make import-data    Run GTFS, Places, and Timetable import pipelines"
	@echo "  make docker-up      Start containerized stack via docker compose"
	@echo "  make docker-down    Stop containerized stack"

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting backend and frontend dev servers..."

test-backend:
	cd backend && pytest -v

test-frontend:
	cd frontend && npm test

test: test-backend test-frontend

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

typecheck:
	cd backend && mypy app tests
	cd frontend && npm run typecheck

seed:
	cd backend && python -m app.db.seed

import-data:
	cd backend && python scripts/import_places.py
	cd backend && python scripts/import_gtfs.py

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
