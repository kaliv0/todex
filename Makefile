.PHONY: help sync format typecheck test build publish clean all

help:
	@echo "Targets:"
	@echo "  sync         sync all dependencies"
	@echo "  format       run ruff"
	@echo "  typecheck    run typecheck"
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
	uv run pyrefly check --min-severity=warn

test:
	uv run pytest

build:
	uv build

publish: clean build
	uvx uv-publish

clean:
	rm -rf .ruff_cache/ .pytest_cache/ .pdm-build/ dist/ build/ *.egg-info/
	find . -path ./.venv -prune -o -type d -name __pycache__ -exec rm -rf {} +

all: sync format typecheck test
