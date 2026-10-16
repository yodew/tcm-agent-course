"""Conservative engineering gates, not a clinically validated triage system."""

from typing import Final, assert_never

from tcm_agent.domain import Action, Fact, FactField, FinalTurn, QuestionKey, RuntimeInput
from tcm_agent.errors import AgentError

QUESTION_TEXT: Final[dict[QuestionKey, str]] = {
    QuestionKey.COMPLAINT: "这次最想向医师说明的困扰是什么？可以跳过或直接生成已有信息的摘要。",
    QuestionKey.ONSET: "这一情况大约从什么时候开始，有怎样的变化？可以跳过。",
    QuestionKey.HISTORY: "有没有希望医师了解的既往情况？只需提供与本次就诊相关的内容。",
    QuestionKey.MEDICATION: "是否有需要在摘要中记录的现用药品？可以选择不提供。",
    QuestionKey.ALLERGY: "是否有本人已知、希望记录的过敏情况？不确定可以保留为未提供。",
    QuestionKey.NONE: "你可以核对待确认信息，补充资料，或直接生成就诊摘要。",
}
FIELD_TEXT: Final[dict[FactField, str]] = {
    FactField.COMPLAINT: "本次困扰",
    FactField.ONSET: "起始时间与变化",
    FactField.HISTORY: "既往情况",
    FactField.MEDICATION: "现用药品",
    FactField.ALLERGY: "过敏情况",
}
HANDOFF: Final[str] = (
    "本助手用于整理就诊资料，无法判断个人病情或提供诊疗方案。请向合格医师咨询；若情况紧急或明显加重，请立即寻求当地急救或线下医疗帮助。"
)


def needs_handoff(text: str) -> bool:
    """Illustrative trigger set with deliberate over-triage; never claim full coverage."""
    return any(
        word in text
        for word in (
            "胸痛",
            "呼吸困难",
            "昏迷",
            "自杀",
            "自伤",
            "开方",
            "开处方",
            "吃多少克",
            "用药剂量",
        )
    )


def validate_final(final: FinalTurn, context: RuntimeInput) -> list[Fact]:
    """Proposed facts must quote CURRENT input; user confirmation decides semantics."""
    if len({f.field for f in final.facts}) != len(final.facts):
        raise AgentError("duplicate_fact_field", 422)
    for draft in final.facts:
        if draft.quote not in context.request.text:
            raise AgentError("ungrounded_fact", 422)
    if final.action != Action.ASK and final.question != QuestionKey.NONE:
        raise AgentError("invalid_question_action", 422)
    return [Fact(field=f.field, quote=f.quote, source_turn_id=context.turn_id) for f in final.facts]


def render_summary(facts: list[Fact]) -> str:
    """No model call: missing facts stay missing, never inferred negative."""
    indexed = {fact.field: fact for fact in facts if fact.confirmed}
    lines = ["就诊准备摘要（用户确认资料）"]
    for field, label in FIELD_TEXT.items():
        fact = indexed.get(field)
        lines.append(f"{label}：{fact.quote if fact else '未提供'}")
    lines.append("此摘要不包含诊断或处方；请由医师结合实际情况判断。")
    return "\n".join(lines)


def render_answer(final: FinalTurn, context: RuntimeInput, quotes: list[str]) -> str:
    """Render trusted templates and verified extractive evidence only."""
    match final.action:
        case Action.ASK:
            return QUESTION_TEXT[final.question]
        case Action.KNOWLEDGE:
            return (
                "\n\n".join(quotes)
                if quotes
                else "当前知识库没有足够依据回答这个问题。可以记录问题并向医师咨询。"
            )
        case Action.SUMMARY:
            return render_summary(context.snapshot.facts)
        case Action.HANDOFF:
            return HANDOFF
        case unreachable:
            assert_never(unreachable)
