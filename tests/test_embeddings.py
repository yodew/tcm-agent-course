import httpx2
import pytest
from pydantic import SecretStr

from tcm_agent.config import Settings
from tcm_agent.embeddings import ProviderEmbedder
from tcm_agent.errors import AgentError


@pytest.mark.anyio
async def test_embeddings_when_provider_returns_reordered_rows_restores_order() -> None:
    # Given: only the wire is faked, the real adapter sends/parses the payload.
    def handle(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/v1/embeddings"
        return httpx2.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0]},
                    {"index": 0, "embedding": [1.0, 0.0]},
                ]
            },
        )

    config = Settings(
        model_api_key=SecretStr("synthetic-key"), embedding_model="synthetic-embedding"
    )
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as client:
        # When
        vectors = await ProviderEmbedder(config, client).embed(["a", "b"])
    # Then
    assert vectors == [[1.0, 0.0], [0.0, 1.0]]


@pytest.mark.anyio
async def test_embeddings_when_row_missing_rejects() -> None:
    # Given
    def handle(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"data": []})

    config = Settings(
        model_api_key=SecretStr("synthetic-key"), embedding_model="synthetic-embedding"
    )
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as client:
        # When / Then
        with pytest.raises(AgentError, match="embedding_schema_error"):
            await ProviderEmbedder(config, client).embed(["a"])
