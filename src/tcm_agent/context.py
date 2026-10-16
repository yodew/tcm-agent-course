"""Bound context by characters conservatively; never truncate confirmed facts silently."""

import json
from dataclasses import dataclass

from tcm_agent.domain import Message, RuntimeInput
from tcm_agent.errors import AgentError


@dataclass(frozen=True, slots=True)
class ContextBuilder:
    max_chars: int

    def build(self, context: RuntimeInput) -> list[Message]:
        """Newest history fits first; current input and confirmed state are mandatory."""
        current = Message(role="user", content=context.request.text)
        facts = Message(
            role="user",
            content=json.dumps(
                {
                    "confirmed_facts_data": [
                        f.model_dump(mode="json") for f in context.snapshot.facts
                    ]
                },
                ensure_ascii=False,
            ),
        )
        remaining = self.max_chars - len(current.content) - len(facts.content)
        if remaining < 0:
            raise AgentError("context_budget_exceeded", 413)
        history: list[Message] = []
        for message in reversed(context.snapshot.messages):
            if len(message.content) > remaining:
                break
            history.insert(0, message)
            remaining -= len(message.content)
        return [facts, *history, current]
