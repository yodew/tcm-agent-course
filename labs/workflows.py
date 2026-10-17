# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run from the repository root: uv run python -m labs.workflows
"""Validate a fixed dependency plan; this experiment does not claim to plan with an LLM."""

from dataclasses import dataclass

from tcm_agent.errors import DataContractError


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    depends_on: tuple[str, ...] = ()


def order(tasks: tuple[Task, ...]) -> tuple[str, ...]:
    """Reject unknown dependencies and cycles before executing any plan side effect."""
    ids = {task.task_id for task in tasks}
    if len(ids) != len(tasks) or any(set(task.depends_on) - ids for task in tasks):
        raise DataContractError("Duplicate IDs or unknown dependencies")
    completed: tuple[str, ...] = ()
    remaining = list(tasks)
    while remaining:
        ready = [task for task in remaining if set(task.depends_on) <= set(completed)]
        if not ready:
            raise DataContractError("Dependency cycle")
        for task in ready:
            completed = (*completed, task.task_id)
            remaining.remove(task)
    return completed


def route(needs_external_evidence: bool) -> str:
    """A code-owned route is a workflow; the predicate is not an LLM decision."""
    return "retrieve_then_explain" if needs_external_evidence else "render_confirmed_summary"


def main() -> None:
    """Print a validated, fixed plan, not a simulated multi-agent collaboration."""
    plan = (Task("retrieve"), Task("explain", ("retrieve",)), Task("review", ("explain",)))
    print("FIXED PLAN EXECUTOR:", order(plan))
    print("DETERMINISTIC ROUTING:", route(needs_external_evidence=False))


if __name__ == "__main__":
    main()
