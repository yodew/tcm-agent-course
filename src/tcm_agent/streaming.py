"""SSE of real workflow progress, with bounded backpressure and cancellation."""

from collections.abc import AsyncIterator

import anyio

from tcm_agent.domain import TurnRequest
from tcm_agent.errors import AgentError
from tcm_agent.events import Progress
from tcm_agent.service import Access, Services


async def stream_turn(
    services: Services, access: Access, request: TurnRequest
) -> AsyncIterator[str]:
    """Stream progress immediately; final content is emitted only after commit."""
    send, receive = anyio.create_memory_object_stream[str](16)

    async def progress(event: Progress) -> None:
        await send.send("event: progress\ndata: " + event.model_dump_json() + "\n\n")

    async def execute() -> None:
        async with send:
            try:
                result = await services.turn(access, request, progress)
                await send.send("event: committed\ndata: " + result.model_dump_json() + "\n\n")
                await send.send("event: done\ndata: {}\n\n")
            except AgentError as error:
                await send.send('event: error\ndata: {"error":"' + error.code + '"}\n\n')

    async with anyio.create_task_group() as tasks:
        tasks.start_soon(execute)
        try:
            yield "event: accepted\ndata: {}\n\n"
            async with receive:
                async for frame in receive:
                    yield frame
        finally:
            tasks.cancel_scope.cancel()
