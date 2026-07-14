from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


ReviewDecision = Literal["pending", "approved", "rejected"]


class ProviderConnect(BaseModel):
    apiKey: str = Field(min_length=1, max_length=4096)
    model: str = Field(min_length=1, max_length=160)


class ActionPlanRequest(BaseModel):
    action: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=800)
    frameCount: Literal[8, 12, 16] = 8
    loop: bool = True


class ActionCreateRequest(ActionPlanRequest):
    view: Literal["side", "front", "three_quarter"]
    customPrompt: str = Field(default="", max_length=1200)


class SelectionRequest(BaseModel):
    versionId: str = Field(min_length=1, max_length=100)


class ReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str = Field(default="", max_length=500)


class RegenerateRequest(BaseModel):
    note: str = Field(default="", max_length=800)


class CharacterCreateFields(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=8, max_length=1600)
    style: Literal["hand_drawn", "anime", "semi_realistic"]
    customStyle: str = Field(default="", max_length=500)

    @field_validator("name", "description")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("内容不能为空")
        return cleaned
