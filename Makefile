.PHONY: setup check test serve evaluate ui labs
setup:
	uv sync --all-extras --frozen
check:
	uv run ruff check src tests examples scripts ui labs exercises
	uv run ruff format --check src tests examples scripts ui labs exercises
	uv run basedpyright
	uv run pytest
	TCM_EXERCISE=solution uv run pytest exercises/acceptance.py -q
	uv run python -m labs.run_all
	uv run python scripts/check_course.py
serve:
	uv run tcm serve
test:
	uv run pytest
evaluate:
	uv run tcm evaluate

ui:
	uv run --extra ui chainlit run ui/app.py --host 127.0.0.1 --port 8001

labs:
	uv run python -m labs.run_all
