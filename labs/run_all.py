# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run from the repository root: uv run python -m labs.run_all
"""Execute all offline mechanisms; never reads or calls a model provider."""

from collections.abc import Callable

from labs import context_memory, evaluation, model_mechanics, retrieval, tool_loop, workflows


def main() -> None:
    """Keep the six experiments individually runnable and easy to compare."""
    experiments: tuple[tuple[str, Callable[[], None]], ...] = (
        ("model_mechanics", model_mechanics.main),
        ("tool_loop", tool_loop.main),
        ("context_memory", context_memory.main),
        ("retrieval", retrieval.main),
        ("workflows", workflows.main),
        ("evaluation", evaluation.main),
    )
    for name, run in experiments:
        print("\nEXPERIMENT:", name)
        run()


if __name__ == "__main__":
    main()
