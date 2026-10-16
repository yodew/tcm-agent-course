"""Native Chainlit components and per-browser presentation state."""

import re
from dataclasses import dataclass, field
from typing import Final, Literal
from uuid import UUID

import anyio
import chainlit as cl

from tcm_agent.domain import Contract, FactField, TurnRequest, VisitSnapshot
from tcm_agent.ui_client import UIError

LABELS: Final = {
    "complaint": "主要困扰",
    "onset": "开始时间",
    "history": "既往情况",
    "medication": "用药",
    "allergy": "过敏",
}


class Selection(Contract):
    command: Literal["consent", "confirm", "remove", "summary", "retry", "delete", "delete_yes"]
    field: FactField | None = None
    source_turn_id: UUID | None = None
    quote: str = ""


@dataclass(slots=True)  # noqa: MUTABLE_OK
class Screen:
    """Mutable, per-browser state and lock serialize UI operations, not API authority."""

    snapshot: VisitSnapshot | None = None
    pending: TurnRequest | None = None
    lock: anyio.Lock = field(default_factory=anyio.Lock)
    messages: list[cl.Message] = field(default_factory=list)


def screen() -> Screen:
    """Keep the untyped SDK session boundary outside application logic."""
    match cl.user_session.get("screen"):  # noqa: MATCH_OK
        case Screen() as current:
            return current
        case _:
            raise UIError("ui_session_missing")


async def message(
    content: str, actions: list[cl.Action] | None = None, elements: list[cl.Text] | None = None
) -> None:
    """Track rendered application messages so deletion clears current-page data."""
    plain = re.sub(r"([\\`*_{}\[\]()#+.!<>|~$-])", r"\\\1", content)
    item = cl.Message(content=plain, actions=actions or [], elements=elements or [])
    await item.send()
    screen().messages.append(item)


def button(label: str, selection: Selection) -> cl.Action:
    """Use parsed action payloads; never send authentication data to the browser."""
    return cl.Action(name="visit", label=label, payload=selection.model_dump(mode="json"))


async def controls(snapshot: VisitSnapshot) -> None:
    """Show candidates separately from confirmed facts, with provenance-bound buttons."""
    actions = [
        button("查看摘要", Selection(command="summary")),
        button("删除当前记录", Selection(command="delete")),
    ]
    for fact in snapshot.candidates:
        await message(
            f"待确认 · {LABELS[fact.field.value]}\n\n用户原文：{fact.quote}",
            [
                button(
                    "确认这条事实",
                    Selection(
                        command="confirm",
                        field=fact.field,
                        source_turn_id=fact.source_turn_id,
                        quote=fact.quote,
                    ),
                )
            ],
        )
    actions.extend(
        button("撤回" + LABELS[fact.field.value], Selection(command="remove", field=fact.field))
        for fact in snapshot.facts
    )
    await message("可继续描述情况；需要更正时先撤回对应事实，再输入正确描述并确认。", actions)
