.PHONY: install test lint run docker-build

install:
	python -m pip install -r requirements-dev.txt

test:
	python -m pytest

lint:
	ruff check .

run:
	uvicorn app.main:app --reload

docker-build:
	docker build -t tiendas-agent-azure-rag .
