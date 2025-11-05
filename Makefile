

PYTHON ?= python3

.PHONY: help install dev-install run lint format test docker-build compose-up compose-down docker-logs clean

help: ## Показать список доступных команд
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS=":.*?## "}; {printf "%-18s %s\n", $$1, $$2}'

install: ## Установить зависимости проекта в текущее окружение
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .

dev-install: ## Установить зависимости проекта и инструменты разработки
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

run: ## Запустить Telegram-бота локально (требуется файл .env)
	$(PYTHON) -m main

lint: ## Проверить стиль кода с помощью ruff
	@command -v ruff >/dev/null || { echo "❌ ruff не установлен. Запусти 'make dev-install'."; exit 1; }
	ruff check .

format: ## Отформатировать код с помощью ruff (требует ruff)
	@command -v ruff >/dev/null || { echo "❌ ruff не установлен. Запусти 'make dev-install'."; exit 1; }
	ruff format .

test: ## Запустить pytest
	@command -v pytest >/dev/null || { echo "❌ pytest не установлен. Запусти 'make dev-install'."; exit 1; }
	pytest

build: ## Собрать Docker-образ бота
	docker compose build

up: ## Запустить сервисы через docker-compose в фоне
	docker compose up -d --build

down: ## Остановить и удалить сервисы docker-compose
	docker compose down

logs: ## Посмотреть логи docker-compose
	docker compose logs -f

clean: ## Очистить кэши, coverage и сборочные артефакты
	$(Q)echo "🧺 Cleaning caches..."
	$(Q)find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	$(Q)rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml htmlcov build dist *.egg-info
