.PHONY: help install test lint format typecheck clean dev run

help:
	@echo "QBench - Available commands:"
	@echo "  make install    - Install dependencies using uv"
	@echo "  make dev        - Install with dev dependencies"
	@echo "  make test       - Run tests with pytest"
	@echo "  make lint       - Run ruff linter"
	@echo "  make format     - Format code with ruff"
	@echo "  make typecheck  - Run mypy type checker"
	@echo "  make clean      - Remove cache and build files"
	@echo "  make all        - Run lint, typecheck, and test"

install:
	uv sync

dev:
	uv sync --extra dev

test:
	uv run pytest

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

typecheck:
	uv run mypy src/

clean:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

all: lint typecheck test
