"""Chainlit adapter for the authenticated API, not a second agent implementation."""

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from os import environ
from typing import Final, assert_never
from uuid import uuid4

import chainlit as cl
import httpx2
from pydantic import ValidationError
from view import Screen, Selection, button, controls, message, screen

from tcm_agent.config import Settings
from tcm_agent.domain import (
    ConfirmRequest,
    TurnRequest,
    TurnResponse,
)
from tcm_agent.events import Progress
from tcm_agent.http_client import create_client
from tcm_agent.ui_client import UIError, VisitClient

SETTINGS: Final = Settings()
SERVER: Final = environ.get("TCM_SERVER_URL", "http://127.0.0.1:8000").rstrip("/")


@cl.password_auth_callback
def authenticate(username: str, password: str) -> cl.User | None:
    """Reuse application identity; never return tokens as user metadata."""
    for token, identity in SETTINGS.access_tokens.items():
        if secrets.compare_digest(password.encode(), token.encode()) and username == identity:
            return cl.User(identifier=identity)
    return None


def token() -> str:
    """Derive the API credential server-side from the authenticated identity."""
    user = cl.user_session.get("user")
    if user is not None:
        for credential, identity in SETTINGS.access_tokens.items():
            if identity == user.identifier:
                return credential
    raise UIError("authentication_required")


@asynccontextmanager
async def operation() -> AsyncIterator[VisitClient]:
    """Serialize browser actions and report bounded errors without logging bodies."""
    try:
        async with screen().lock, create_client() as http:
            http.headers["Authorization"] = "Bearer " + token()
            yield VisitClient(http, SERVER)
    except (UIError, httpx2.RequestError, ValidationError):
        actions = [button("重试同一请求", Selection(command="retry"))] if screen().pending else []
        await message(
            "操作未能完成。请检查后端是否启动、登录身份是否匹配；版本冲突时请查看最新事实。若消息结果不确定，请重试同一请求。",
            actions,
        )


@cl.on_chat_start
async def start() -> None:
    """No health data is sent or persisted until explicit consent."""
    cl.user_session.set("screen", Screen())
    await message(
        "欢迎使用就诊准备助手。它可以整理困扰、解释课程知识并生成摘要，不提供诊断或处方。\n\n同意后，你输入的内容将发送到本地后端；启用真实模型时也会发往你配置的平台。可撤回事实、删除当前记录。刷新页面不会恢复当前会话，请先查看摘要或删除记录。",
        [button("同意并开始", Selection(command="consent"))],
    )


async def execute(client: VisitClient) -> None:
    """Display actual SSE progress and only render a committed final response."""
    state = screen()
    if state.snapshot is None or state.pending is None:
        raise UIError("no_pending_request")
    result: TurnResponse | None = None
    try:
        async with cl.Step(name="处理本次输入", type="run", show_input=False) as step:
            async for event in client.events(state.snapshot.session_id, state.pending):
                match event.kind:
                    case "progress":
                        progress = Progress.model_validate_json(event.data)
                        step.output = f"步骤 {progress.step} · {progress.kind}" + (
                            " · " + progress.tool if progress.tool else ""
                        )
                        await step.update()
                    case "committed":
                        result = TurnResponse.model_validate_json(event.data)
                    case "accepted" | "done" | "error":
                        # VisitClient raises error frames before yielding them.
                        pass
                    case unreachable:
                        assert_never(unreachable)
            step.output = "结果已保存"
    except UIError as error:
        if error.code != "version_conflict":
            raise
        state.pending = None
        state.snapshot = await client.load(state.snapshot.session_id)
        await message("记录版本已更新，本次输入未保存。请核对最新事实后重新发送。")
        await controls(state.snapshot)
        return
    if result is None:
        raise UIError("stream_incomplete")
    state.snapshot = await client.load(state.snapshot.session_id)
    state.pending = None
    sources = [
        cl.Text(
            name=f"引用 {i + 1} · {cite.title}",
            content=f"{cite.text}\n来源：{cite.source_url}\n版本：{cite.version}",
            display="inline",
        )
        for i, cite in enumerate(result.citations)
    ]
    await message(
        result.answer + ("\n\n本次已降级为已有信息摘要。" if result.status == "degraded" else ""),
        elements=sources,
    )
    await controls(state.snapshot)


@cl.on_message
async def respond(incoming: cl.Message) -> None:
    """Preserve the idempotency key across failures; never silently resubmit new work."""
    screen().messages.append(incoming)
    async with operation() as client:
        state = screen()
        if state.snapshot is None:
            await message("请先点击“同意并开始”。")
            return
        if state.pending is not None:
            await message(
                "上一次请求结果尚不确定，请先重试。",
                [button("重试同一请求", Selection(command="retry"))],
            )
            return
        state.snapshot = await client.load(state.snapshot.session_id)
        state.pending = TurnRequest(
            request_id=uuid4(), expected_version=state.snapshot.version, text=incoming.content
        )
        await execute(client)


@cl.action_callback("visit")
async def act(action: cl.Action) -> None:  # noqa: C901, PLR0912
    """Route UI intent through the same authenticated, versioned API contracts."""
    async with operation() as client:
        selection = Selection.model_validate(action.payload)
        state = screen()
        if state.pending is not None and selection.command in {"confirm", "remove"}:
            await message(
                "上一次请求结果尚不确定，请先重试后再修改事实。",
                [button("重试同一请求", Selection(command="retry"))],
            )
            return
        if selection.command == "consent":
            if state.snapshot is None:
                state.snapshot = await client.create()
            health = await client.health()
            await action.remove()
            mode = (
                "当前后端模式：offline，使用固定策略工程夹具，不调用语言模型。"
                if health.model_mode == "offline"
                else f"当前后端模式：{health.model_mode}，使用已配置的平台；连通性以实际请求为准。"
            )
            await message(mode)
            await message("已开始。你可以描述主要困扰，或问“什么是四诊？”。")
            await controls(state.snapshot)
            return
        if state.snapshot is None:
            raise UIError("consent_required")
        state.snapshot = await client.load(state.snapshot.session_id)
        match selection.command:
            case "confirm":
                candidate = next(
                    (
                        f
                        for f in state.snapshot.candidates
                        if f.field == selection.field
                        and f.source_turn_id == selection.source_turn_id
                        and f.quote == selection.quote
                    ),
                    None,
                )
                if candidate is None:
                    await message("这条候选已失效，请使用最新的候选事实。")
                    return
                state.snapshot = await client.confirm(
                    state.snapshot.session_id,
                    ConfirmRequest(
                        expected_version=state.snapshot.version,
                        field=candidate.field,
                        quote=candidate.quote,
                        source_turn_id=candidate.source_turn_id,
                    ),
                )
                await action.remove()
                await message("已确认。\n\n确认原文：" + candidate.quote)
                await controls(state.snapshot)
            case "remove":
                if selection.field is None:
                    raise UIError("missing_field")
                state.snapshot = await client.remove(state.snapshot, selection.field)
                await action.remove()
                await message("已撤回。请重新描述并确认正确事实。")
                await controls(state.snapshot)
            case "summary":
                await message(
                    "摘要只包含已确认事实。\n\n" + await client.summary(state.snapshot.session_id)
                )
            case "retry":
                await execute(client)
            case "delete":
                await message(
                    "确认删除后端保存的当前会话、输入和事实？",
                    [button("确认删除", Selection(command="delete_yes"))],
                )
            case "delete_yes":
                await client.delete(state.snapshot.session_id)
                for item in state.messages:
                    await item.remove()
                cl.user_session.set("screen", Screen())
                await start()
                await message("当前后端记录已删除。配置平台的留存规则由该平台决定。")
            case unreachable:
                assert_never(unreachable)
