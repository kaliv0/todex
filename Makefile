.PHONY: help sync format typecheck test build publish clean all

help:
	@echo "Targets:"
	@echo "  sync         uv sync --all-extras --dev"
	@echo "  format       uv run ruff check && uv run ruff format"
	@echo "  typecheck    uv run mypy ."
	@echo "  test         uv run pytest"
	@echo "  build        uv build"
	@echo "  clean        remove ruff/mypy/pytest caches"
	@echo "  all          sync format typecheck test"

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

publish: build
	uvx uv-publish

clean:
	rm -rf .ruff_cache/ .mypy_cache/ .pytest_cache/

all: sync format typecheck test
