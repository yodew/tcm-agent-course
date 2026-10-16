"""Fail closed configuration; never infer providers or reuse credentials."""

from pathlib import Path
from typing import ClassVar, Literal, Self
from urllib.parse import urlparse

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from tcm_agent.errors import ConfigurationError


class Settings(BaseSettings):
    """Environment settings. Tokens and model credentials stay out of repr."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="TCM_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )
    model_mode: Literal["responses", "chat", "offline"] = "offline"
    model_base_url: str = "http://127.0.0.1:9001/v1"
    model_name: str = "contract-fixture"
    model_api_key: SecretStr = SecretStr("")
    access_tokens: dict[str, str] = Field(default_factory=dict, repr=False)
    database_url: str = "sqlite+aiosqlite:///./data/tcm.db"
    knowledge_path: Path = Path("knowledge/entries.json")
    max_steps: int = Field(default=6, ge=1, le=12)
    turn_timeout_seconds: float = Field(default=90, gt=0, le=300)
    max_output_tokens: int = Field(default=1600, ge=128, le=8000)
    rate_limit_per_minute: int = Field(default=20, ge=1)
    embedding_model: str = ""
    responses_include_reasoning: bool = True
    # This names an API parameter, not a secret credential.
    chat_token_parameter: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"  # noqa: S105
    context_chars: int = Field(default=16000, ge=5000, le=64000)

    @model_validator(mode="after")
    def check_provider(self) -> Self:
        """Allow local HTTP fixtures; require TLS for remote credentials."""
        parsed = urlparse(self.model_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ConfigurationError("Model endpoint must be an HTTP(S) base URL")
        if parsed.scheme != "https" and parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise ConfigurationError("Remote model endpoints require HTTPS")
        if parsed.query or parsed.fragment or parsed.username:
            raise ConfigurationError("Base URL must not contain credentials, query or fragment")
        if (
            self.model_mode != "offline" or self.embedding_model
        ) and not self.model_api_key.get_secret_value():
            raise ConfigurationError("Set TCM_MODEL_API_KEY for a real provider")
        return self
