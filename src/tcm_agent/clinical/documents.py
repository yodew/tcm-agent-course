"""Convert reviewed research projections into self-contained retrieval documents."""

import hashlib
from typing import Literal

from tcm_agent.clinical.contracts import Citation, Source
from tcm_agent.clinical.store import ResearchKnowledge
from tcm_agent.domain import Contract

DocumentKind = Literal["question", "terminology", "corpus_association", "literature_reference"]


class Reference(Contract):
    source: Source
    locator: str


class KnowledgeDocument(Contract):
    document_id: str
    kind: DocumentKind
    title: str
    text: str
    references: list[Reference]
    clinical_use: Literal["disabled"] = "disabled"


class SearchHit(Contract):
    document: KnowledgeDocument
    relevance: float
    score_meaning: Literal["lexical_relevance_not_diagnostic_probability"] = (
        "lexical_relevance_not_diagnostic_probability"
    )


def compile_documents(pack: ResearchKnowledge) -> tuple[KnowledgeDocument, ...]:
    """Preserve citations, limitations and evidence kinds at the retrieval boundary."""
    sources = {source.source_id: source for source in pack.sources}
    terms = {term.term_id: term for term in pack.terms}

    def references(citations: list[Citation]) -> list[Reference]:
        return [Reference(source=sources[c.source_id], locator=c.locator) for c in citations]

    documents = [
        KnowledgeDocument(
            document_id=q.question_id,
            kind="question",
            title=q.prompt,
            text=(
                f"采集字段：{q.target_field}；采集域：{q.domain}。\n"
                f"提问原因：{q.reason}\n场景：{'、'.join(q.profiles)}；"
                f"前置问题：{'、'.join(q.prerequisites) or '无'}；"
                f"工程优先级：{q.priority}，不是诊断权重。\n"
                "原创问诊采集草案，尚未经临床路径验证，不能据此自动作出诊断。"
            ),
            references=references(q.source_refs),
        )
        for q in pack.questions
    ]
    documents.extend(
        KnowledgeDocument(
            document_id=term.term_id,
            kind="terminology",
            title=term.label,
            text=(
                f"来源术语：{term.label}；类别：{term.kind}；"
                f"来源别名：{'、'.join(term.aliases) or '未提供'}。\n"
                "仅为来源标签与出处，未提供医学定义或诊断标准；不能据标签判断患者患病。"
            ),
            references=references(term.citations),
        )
        for term in pack.terms
    )
    for card in pack.cards:
        edges = [
            edge
            for edge in pack.associations
            if edge.syndrome_id == card.syndrome_id and edge.source_id == card.source_id
        ]
        observations = "、".join(
            f"{terms[edge.observation_id].label}（{edge.record_count}条记录）" for edge in edges
        )
        documents.append(
            KnowledgeDocument(
                document_id=card.card_id,
                kind="corpus_association",
                title=terms[card.syndrome_id].label + "：训练语料共现资料",
                text=(
                    f"含此证候标签的来源记录数：{card.source_record_count}。\n"
                    f"保留的共现观察：{observations or '无，不能作为观察依据'}。\n"
                    "证据类型：训练记录中的描述性共现。计数不是患病概率或诊断权重。"
                    "诊断必要条件、排除条件、鉴别规则均未知；单条记录尤其不足以泛化。"
                ),
                references=references(
                    [c for c in terms[card.syndrome_id].citations if c.source_id == card.source_id]
                ),
            )
        )
    documents.extend(
        KnowledgeDocument(
            document_id=card.card_id,
            kind="literature_reference",
            title=f"{card.topic}：{card.pattern_label}",
            text=(
                f"文献整理的相关表现：{'、'.join(card.related_features)}。\n"
                f"可关联的采集问题：{'、'.join(card.question_links)}。\n"
                f"局限：{'；'.join(card.limitations)}。\n"
                "这是历史文献的描述性参考；必要条件和排除条件未知，未经临床验证。"
            ),
            references=references([Citation(source_id=card.source_id, locator=card.locator)]),
        )
        for card in pack.literature
    )
    return tuple(sorted(documents, key=lambda document: document.document_id))


def document_fingerprint(documents: tuple[KnowledgeDocument, ...]) -> str:
    """Include content and provenance so source or license edits invalidate the index."""
    canonical = "\n".join(document.model_dump_json() for document in documents)
    return hashlib.sha256(canonical.encode()).hexdigest()
