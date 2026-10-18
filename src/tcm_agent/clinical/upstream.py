"""Minimal source projections: raw narratives and reasoning never enter exported contracts."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class Projection(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")


class TCMEvalRow(Projection):
    information: str = Field(alias="Clinical Information")
    syndrome: str = Field(alias="TCM Syndrome")


class MTCMBAnswer(Projection):
    disease: str = Field(alias="疾病名称")
    location: str = Field(alias="病位证素")
    nature: str = Field(alias="病性证素")
    syndrome: str = Field(alias="证名")


class MTCMBRow(Projection):
    answer: MTCMBAnswer


class InputSpec(Projection):
    source_id: str
    url: str
    local_name: str
    sha256: str
    license_url: str
    license_local_name: str
    license_sha256: str
