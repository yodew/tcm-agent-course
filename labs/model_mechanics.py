# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run from the repository root: uv run python -m labs.model_mechanics
"""Calculate sampling probabilities without pretending to run an LLM."""

import math

from tcm_agent.errors import DataContractError


def probabilities(logits: tuple[float, ...], temperature: float) -> tuple[float, ...]:
    """Stable softmax: temperature changes a distribution, not knowledge or permissions."""
    if not logits or not math.isfinite(temperature) or temperature <= 0:
        raise DataContractError("Use nonempty logits and positive finite temperature")
    if not all(math.isfinite(value) for value in logits):
        raise DataContractError("Logits must be finite")
    maximum = max(logits)
    weights = tuple(math.exp((value - maximum) / temperature) for value in logits)
    total = sum(weights)
    return tuple(value / total for value in weights)


def request_messages(current: str, history: tuple[str, ...] = ()) -> tuple[str, ...]:
    """History is explicitly supplied by the application, not remembered by this function."""
    return (*history, current)


def main() -> None:
    """Print arithmetic results, UTF-8 sizes and independent request contents."""
    print("ARITHMETIC ONLY: these logits do not come from a model")
    for temperature in (0.2, 1.0, 2.0):
        print(temperature, tuple(round(p, 4) for p in probabilities((3, 2, 0), temperature)))
    text = "四诊"
    print("characters", len(text), "UTF-8 bytes", len(text.encode()), "tokens: tokenizer required")
    print("without history", request_messages("它包括什么？"))
    print("with history", request_messages("它包括什么？", ("四诊是什么？",)))


if __name__ == "__main__":
    main()
