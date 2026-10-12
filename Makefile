.PHONY: help sync format typecheck test build publish clean all

help:
	@echo "Targets:"
	@echo "  sync         sync all dependencies"
	@echo "  format       run ruff"
	@echo "  typecheck    run mypy"
	@echo "  test         run pytest"
	@echo "  build        build project"
	@echo "  publish      publish to PyPi"
	@echo "  clean        remove caches & dist"
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
	rm -rf .ruff_cache/ .mypy_cache/ .pytest_cache/ dist/

all: sync format typecheck test
