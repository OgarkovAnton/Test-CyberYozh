.PHONY: help up down build migrate seed shell test test-domain logs backend-shell frontend-shell

help:
	@echo "Available targets:"
	@echo "  up            - Start all services"
	@echo "  down          - Stop all services"
	@echo "  build         - Build images"
	@echo "  migrate       - Run Django migrations"
	@echo "  seed          - Seed demo users (alice is admin) and a sample task"
	@echo "  shell         - Django shell"
	@echo "  test          - Run all backend tests"
	@echo "  test-domain   - Run domain unit tests"
	@echo "  logs          - Tail compose logs"
	@echo "  backend-shell - Shell into web container"
	@echo "  frontend-shell- Shell into frontend container"

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

migrate:
	docker compose run --rm web python manage.py migrate

seed:
	docker compose exec web python manage.py seed_demo

shell:
	docker compose run --rm web python manage.py shell

test:
	docker compose run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test web pytest -q

test-domain:
	cd backend && PYTHONPATH=. pytest -c pytest-domain.ini

logs:
	docker compose logs -f

backend-shell:
	docker compose exec web sh

frontend-shell:
	docker compose exec frontend sh
