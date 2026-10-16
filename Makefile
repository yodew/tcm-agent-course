.PHONY: setup check test serve evaluate ui
setup:
	uv sync --all-extras --frozen
check:
	uv run ruff check src tests examples scripts ui
	uv run ruff format --check src tests examples scripts ui
	uv run basedpyright
	uv run pytest
	uv run python scripts/check_course.py
serve:
	uv run tcm serve
test:
	uv run pytest
evaluate:
	uv run tcm evaluate

ui:
	uv run --extra ui chainlit run ui/app.py --host 127.0.0.1 --port 8001
