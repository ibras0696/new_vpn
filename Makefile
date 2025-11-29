up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose run --rm app alembic upgrade head

app:
	docker compose up --build app

compose-recreate:
	docker compose up -d --force-recreate app

ps:
	docker compose ps

app-logs:
	docker compose logs -f app

db-logs:
	docker compose logs -f db


clean: ## Очистить кэши, coverage и сборочные артефакты
	$(Q)echo "🧺 Cleaning caches..."
	$(Q)find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	$(Q)rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml htmlcov build dist *.egg-info
