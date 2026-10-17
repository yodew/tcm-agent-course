# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2.10,<3"]
# ///
# Run from the repository root: uv run python -m labs.tool_loop
"""A minimal tool executor with explicit scripted decisions, not an AI simulation."""

from dataclasses import dataclass
from typing import ClassVar, Protocol, assert_never

from pydantic import BaseModel, ConfigDict, Field

from tcm_agent.errors import DataContractError


class LookupArgs(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
    term: str = Field(min_length=1, max_length=30)


@dataclass(frozen=True, slots=True)
class Call:
    call_id: str
    name: str
    arguments: str


@dataclass(frozen=True, slots=True)
class Finish:
    answer: str


@dataclass(frozen=True, slots=True)
class Observation:
    call_id: str
    output: str


class DecisionSource(Protocol):
    def decide(self, observations: tuple[Observation, ...]) -> Call | Finish:
        """A real adapter would request a model here; the fixture provides fixed decisions."""
        ...


@dataclass(frozen=True, slots=True)
class ScriptedDecisions:
    """Supply a deterministic trace so executor errors are reproducible."""

    decisions: tuple[Call | Finish, ...]

    def decide(self, observations: tuple[Observation, ...]) -> Call | Finish:
        """Advance after each actual tool observation; reject an exhausted fixture."""
        if len(observations) >= len(self.decisions):
            raise DataContractError("Fixture exhausted before finish")
        return self.decisions[len(observations)]


def lookup(term: str) -> str:
    """Look up original teaching text; no network, medical diagnosis or side effect."""
    terms = {"四诊": "四诊是望、闻、问、切的传统信息采集方法。"}
    return terms.get(term, "教学词表没有这个条目")


def run(source: DecisionSource, max_steps: int = 3) -> tuple[str, tuple[Observation, ...]]:
    """The host owns validation, execution, result linkage and termination."""
    observations: tuple[Observation, ...] = ()
    seen: set[str] = set()
    for _ in range(max_steps):
        match source.decide(observations):
            case Call(call_id=call_id, name=name, arguments=arguments):
                if not call_id or call_id in seen:
                    raise DataContractError("Missing or repeated call ID")
                if name != "lookup_term":
                    raise DataContractError("Tool is not registered")
                parsed = LookupArgs.model_validate_json(arguments)
                seen.add(call_id)
                observations = (*observations, Observation(call_id, lookup(parsed.term)))
            case Finish(answer=answer):
                return answer, observations
            case unreachable:
                assert_never(unreachable)
    raise DataContractError("Step budget exhausted")


def main() -> None:
    """Execute search then finish and display the real tool observation."""
    source = ScriptedDecisions(
        (Call("call-1", "lookup_term", '{"term":"四诊"}'), Finish("查看工具返回的教学解释"))
    )
    answer, observations = run(source)
    print("SCRIPTED DECISIONS ONLY:", answer)
    for observation in observations:
        print(observation.call_id, observation.output)


if __name__ == "__main__":
    main()
