"""Bounded native tool loop: proposal, observation, validation, final rendering."""

from dataclasses import dataclass

from pydantic import ValidationError

from tcm_agent.context import ContextBuilder
from tcm_agent.domain import (
    Action,
    EmptyArgs,
    Evidence,
    FinalTurn,
    RuntimeInput,
    SearchArgs,
    ToolResult,
    TurnResponse,
    Usage,
)
from tcm_agent.errors import AgentError
from tcm_agent.events import Progress, ProgressSink
from tcm_agent.gateway import ModelGateway
from tcm_agent.policy import HANDOFF, needs_handoff, render_answer, validate_final
from tcm_agent.retrieval import KnowledgeBase


@dataclass(frozen=True, slots=True)
class AgentRuntime:
    gateway: ModelGateway
    knowledge: KnowledgeBase
    max_steps: int
    context_chars: int

    async def run(self, context: RuntimeInput, emit: ProgressSink | None = None) -> TurnResponse:  # noqa: C901, PLR0912
        # Keep the bounded decision loop visible as one teaching unit.
        """Model decisions never get credentials, owner IDs, arbitrary SQL or writes."""
        if needs_handoff(context.request.text):
            return self.handoff(context)
        conversation = self.gateway.conversation(ContextBuilder(self.context_chars).build(context))
        observations: list[ToolResult] = []
        retrieved: dict[str, Evidence] = {}
        used_ids: set[str] = set()
        totals = Usage()
        for step_index in range(1, self.max_steps + 1):
            if emit is not None:
                await emit(Progress(kind="model_step", step=step_index))
            step = await conversation.step(observations)
            totals = Usage(
                input_tokens=totals.input_tokens + step.usage.input_tokens,
                output_tokens=totals.output_tokens + step.usage.output_tokens,
            )
            if len(step.calls) != 1:
                raise AgentError("expected_single_tool_call", 422)
            call = step.calls[0]
            if call.call_id in used_ids:
                raise AgentError("duplicate_tool_call_id", 422)
            used_ids.add(call.call_id)
            if emit is not None:
                await emit(
                    Progress(
                        kind="tool_started",
                        step=step_index,
                        tool=call.name
                        if call.name in {"search_knowledge", "read_visit_facts", "submit_turn"}
                        else "rejected",
                    )
                )
            try:
                match call.name:  # noqa: MATCH_OK
                    # Names cross an open untrusted string boundary; reject unknowns.
                    case "search_knowledge":
                        args = SearchArgs.model_validate_json(call.arguments)
                        entries = await self.knowledge.search(args.query)
                        retrieved.update((entry.entry_id, entry) for entry in entries)
                        observations = [
                            ToolResult(
                                call_id=call.call_id,
                                output="[" + ",".join(e.model_dump_json() for e in entries) + "]",
                            )
                        ]
                    case "read_visit_facts":
                        EmptyArgs.model_validate_json(call.arguments)
                        observations = [
                            ToolResult(
                                call_id=call.call_id,
                                output="["
                                + ",".join(f.model_dump_json() for f in context.snapshot.facts)
                                + "]",
                            )
                        ]
                    case "submit_turn":
                        final = FinalTurn.model_validate_json(call.arguments)
                        candidates = validate_final(final, context)
                        citations: list[Evidence] = []
                        for citation in final.citations:
                            evidence = retrieved.get(citation.entry_id)
                            if evidence is None or citation.quote not in evidence.text:
                                raise AgentError("ungrounded_citation", 422)
                            citations.append(evidence.model_copy(update={"text": citation.quote}))
                        if emit is not None:
                            await emit(Progress(kind="validated", step=step_index))
                        return TurnResponse(
                            turn_id=context.turn_id,
                            session_id=context.snapshot.session_id,
                            version=context.snapshot.version + 1,
                            action=final.action,
                            answer=render_answer(final, context, [e.text for e in citations]),
                            candidates=candidates,
                            citations=citations,
                            usage=totals,
                            steps=step_index,
                        )
                    case _:
                        raise AgentError("tool_not_allowed", 422)
            except ValidationError as error:
                raise AgentError("invalid_tool_arguments", 422) from error
        raise AgentError("step_budget_exceeded")

    def handoff(self, context: RuntimeInput) -> TurnResponse:
        """Fail closed before model invocation for explicitly recognized triggers."""
        return TurnResponse(
            turn_id=context.turn_id,
            session_id=context.snapshot.session_id,
            version=context.snapshot.version + 1,
            action=Action.HANDOFF,
            answer=HANDOFF,
            candidates=[],
            citations=[],
            usage=Usage(),
            steps=0,
        )
