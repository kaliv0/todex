.PHONY: help sync lint test all

help:
	@echo "Targets:"
	@echo "  sync         uv sync --all-extras --dev"
	@echo "  lint         uv run ruff check && uv run ruff format"
	@echo "  test         uv run pytest -v ."
	@echo "  all          sync lint test"

sync:
	uv sync --all-extras --dev

format:
	uv run ruff check && uv run ruff format

typecheck:
	uv run mypy .

test:
	uv run pytest

build:
	uv build

clean:
	rm -rf .ruff_cache/ .mypy_cache/ .pytest_cache/

all: sync format typecheck test
