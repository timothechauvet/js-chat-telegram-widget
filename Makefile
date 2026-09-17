SHELL := /usr/bin/env bash

.PHONY: all help dev run start backend frontend install install-backend install-frontend test test-backend test-frontend build clean setup-env

# Default target
all: help

help:
	@echo "=========================================================="
	@echo "  Telegram Live Chat System - Makefile"
	@echo "=========================================================="
	@echo "Usage: make <target>"
	@echo ""
	@echo "Available targets:"
	@echo "  make dev       Start both backend & frontend concurrently (with auto-setup)"
	@echo "  make backend   Run only the FastAPI backend (http://127.0.0.1:8000)"
	@echo "  make frontend  Run only the Vite widget showcase (http://127.0.0.1:5173)"
	@echo "  make install   Install dependencies for backend (venv/pip) and widget (npm)"
	@echo "  make test      Run test suites (backend pytest + widget vitest)"
	@echo "  make build     Build the production distribution for the widget"
	@echo "  make clean     Clean caches, venvs, and build artifacts"
	@echo "=========================================================="

dev run start: setup-env install
	@echo "🚀 Starting Telegram Live Chat System..."
	@echo "   • Frontend: http://127.0.0.1:5173/"
	@echo "   • Backend:  http://127.0.0.1:8000/"
	@echo "   • Docs:     http://127.0.0.1:8000/docs"
	@echo "Press [Ctrl+C] to stop all services."
	@if curl -s -f http://127.0.0.1:8000/health >/dev/null 2>&1; then \
		echo "⚡ Backend is already running on port 8000. Launching frontend demo..."; \
		cd packages/widget && npm run dev -- --host 127.0.0.1 --port 5173; \
	else \
		trap 'kill $$BACKEND_PID $$FRONTEND_PID 2>/dev/null' SIGINT SIGTERM EXIT; \
		(cd packages/backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) & \
		BACKEND_PID=$$!; \
		sleep 1.5; \
		(cd packages/widget && npm run dev -- --host 127.0.0.1 --port 5173) & \
		FRONTEND_PID=$$!; \
		wait; \
	fi

setup-env:
	@if [ ! -f packages/backend/.env ]; then \
		echo "⚠️  Creating packages/backend/.env from .env.example..."; \
		cp packages/backend/.env.example packages/backend/.env; \
	fi
	@if ! grep -q "TELEGRAM_POLLING_MODE" packages/backend/.env; then \
		echo "TELEGRAM_POLLING_MODE=true" >> packages/backend/.env; \
	fi

install: install-backend install-frontend

install-backend:
	@if [ ! -d packages/backend/.venv ]; then \
		echo "📦 Creating Python venv in packages/backend/.venv..."; \
		python3 -m venv packages/backend/.venv; \
		packages/backend/.venv/bin/pip install --upgrade pip; \
		packages/backend/.venv/bin/pip install -r packages/backend/requirements.txt; \
	fi

install-frontend:
	@if [ ! -d packages/widget/node_modules ]; then \
		echo "📦 Installing widget dependencies..."; \
		cd packages/widget && npm install; \
	fi

backend: setup-env install-backend
	@echo "⚙️ Starting backend server on http://127.0.0.1:8000..."
	cd packages/backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

frontend: install-frontend
	@echo "🎨 Starting widget demo on http://127.0.0.1:5173..."
	cd packages/widget && npm run dev -- --host 127.0.0.1 --port 5173

test: test-backend test-frontend

test-backend: install-backend
	@echo "🧪 Running backend pytest..."
	cd packages/backend && .venv/bin/pytest

test-frontend: install-frontend
	@echo "🧪 Running widget vitest..."
	cd packages/widget && npm run test:run

build: install-frontend
	@echo "📦 Building widget production package..."
	cd packages/widget && npm run build

clean:
	@echo "🧹 Cleaning build artifacts and caches..."
	rm -rf packages/widget/dist packages/widget/node_modules
	rm -rf packages/backend/.venv packages/backend/.pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
