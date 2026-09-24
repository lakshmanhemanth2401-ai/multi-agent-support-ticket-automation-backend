.PHONY: install test lint migrate run compose-up compose-down

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest -q

lint:
	python -m ruff check app tests

migrate:
	python -m alembic upgrade head

run:
	python -m uvicorn app.main:app --reload

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down
