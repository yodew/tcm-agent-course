"""Optional embeddings use a real provider; model identity defines the index version."""

from dataclasses import dataclass

import httpx2
from pydantic import BaseModel

from tcm_agent.config import Settings
from tcm_agent.errors import AgentError


class EmbeddingRow(BaseModel):
    index: int
    embedding: list[float]


class EmbeddingEnvelope(BaseModel):
    data: list[EmbeddingRow]


@dataclass(frozen=True, slots=True)
class ProviderEmbedder:
    settings: Settings
    client: httpx2.AsyncClient

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Keep this course corpus bounded; reject missing/reordered/empty embeddings."""
        response = await self.client.post(
            f"{self.settings.model_base_url.rstrip('/')}/embeddings",
            headers={"Authorization": f"Bearer {self.settings.model_api_key.get_secret_value()}"},
            json={
                "model": self.settings.embedding_model,
                "input": texts,
                "encoding_format": "float",
            },
        )
        if response.status_code != 200:
            raise AgentError("embedding_http_error")
        envelope = EmbeddingEnvelope.model_validate_json(response.content)
        rows = sorted(envelope.data, key=lambda r: r.index)
        if [r.index for r in rows] != list(range(len(texts))) or any(not r.embedding for r in rows):
            raise AgentError("embedding_schema_error")
        return [row.embedding for row in rows]
