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

ps:
	docker compose ps

app-logs:
	docker compose logs -f app

db-logs:
	docker compose logs -f db
