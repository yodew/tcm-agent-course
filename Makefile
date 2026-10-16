.PHONY: setup check test serve evaluate
setup:
	uv sync --all-extras --frozen
check:
	uv run ruff check src tests examples scripts
	uv run ruff format --check src tests examples scripts
	uv run basedpyright
	uv run pytest
	uv run python scripts/check_course.py
serve:
	uv run tcm serve
test:
	uv run pytest
evaluate:
	uv run tcm evaluate
