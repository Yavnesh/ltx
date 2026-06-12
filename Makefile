.PHONY: install test lint up down migrate format

install:
	poetry install

test:
	poetry run pytest --cov=app tests/ -v

lint:
	poetry run black --check app tests/
	poetry run isort --check app tests/
	poetry run flake8 app tests/

format:
	poetry run black app tests/
	poetry run isort app tests/

up:
	docker compose up -d

down:
	docker compose down

migrate:
	poetry run alembic upgrade head
