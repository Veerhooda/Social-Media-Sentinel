"""API contracts and model-output contracts for the Audience Lab."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Audience profile store (extensible)
# ---------------------------------------------------------------------------


class ProfileIn(BaseModel):
    """One audience record from any source. ``attributes`` is free-form on purpose."""

    model_config = ConfigDict(extra="forbid")
    source: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.:-]+$")
    external_ref: str = Field(min_length=1, max_length=256)
    platform: str | None = Field(default=None, max_length=32)
    label: str | None = Field(default=None, max_length=256)
    attributes: dict[str, Any] = Field(default_factory=dict)
    behaviour: dict[str, Any] = Field(default_factory=dict)
    sample_texts: list[str] = Field(default_factory=list, max_length=20)
    weight: float = Field(default=1.0, gt=0, le=1_000_000, description="How many real people this record represents")


class ProfileImport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profiles: list[ProfileIn] = Field(min_length=1, max_length=5000)


class ProfileOut(BaseModel):
    profile_id: UUID
    source: str
    external_ref: str
    platform: str | None
    label: str | None
    attributes: dict[str, Any]
    behaviour: dict[str, Any]
    sample_texts: list[str]
    weight: float
    updated_at: datetime | None = None


class ProfilePage(BaseModel):
    total: int
    items: list[ProfileOut]


class UpsertResult(BaseModel):
    created: int
    updated: int
    total_profiles: int
    by_source: dict[str, int]


class LabStatus(BaseModel):
    model_name: str
    api_configured: bool
    base_url: str
    total_profiles: int
    by_source: dict[str, int]
    latest_segmentation_id: UUID | None
    platforms: list[str] = Field(default_factory=list, description="Platforms present in the audience database")


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------


class SegmentationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    focus: str | None = Field(default=None, max_length=1000, description="Optional steer, e.g. 'group by buying intent'")
    min_segments: int | None = Field(default=None, ge=1, le=30)
    max_segments: int | None = Field(default=None, ge=1, le=30)
    sources: list[str] | None = Field(default=None, description="Restrict to these profile sources")


class SegmentOut(BaseModel):
    segment_id: UUID
    code: str
    name: str
    description: str
    defining_traits: list[str]
    member_count: int
    weight_total: float
    share: float
    attribute_breakdown: dict[str, Any]
    persona: dict[str, Any] | None


class SegmentationOut(BaseModel):
    segmentation_id: UUID
    status: str
    model_name: str
    params: dict[str, Any]
    profile_count: int
    assigned_count: int
    rationale: str | None
    progress: dict[str, Any]
    error: str | None
    created_at: datetime | None
    completed_at: datetime | None
    segments: list[SegmentOut] = Field(default_factory=list)


# -- model outputs ----------------------------------------------------------


class DiscoveredSegment(BaseModel):
    id: str = Field(description="Short id such as S1, S2 …")
    name: str
    description: str
    defining_traits: list[str]
    membership_rule: str = Field(description="Plain-language rule a reviewer can use to place a profile in this segment")
    estimated_share_pct: float


class DiscoveryOutput(BaseModel):
    rationale: str = Field(description="Why this segmentation and this number of segments fits the data")
    segments: list[DiscoveredSegment]


class Assignment(BaseModel):
    ref: str
    segment_id: str = Field(description="One of the segment ids, or UNASSIGNED")
    confidence: float


class AssignmentOutput(BaseModel):
    assignments: list[Assignment]


class PersonaOutput(BaseModel):
    persona_name: str
    summary: str
    demographics: str = Field(description="Who these people are, grounded only in the supplied member evidence")
    interests: list[str]
    values: list[str]
    communication_style: str
    positive_triggers: list[str]
    negative_triggers: list[str]
    sarcasm_tendency: Literal["low", "medium", "high"]
    evidence_strength: Literal["weak", "moderate", "strong"]
    agent_instructions: str = Field(description="Second-person system prompt for the agent that will role-play this segment")


# ---------------------------------------------------------------------------
# Post simulation
# ---------------------------------------------------------------------------



class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=8000)
    platform: str = Field(default="x")
    segmentation_id: UUID | None = None
    image_data_url: str | None = Field(default=None, description="Optional data:image/...;base64,... attachment")
    media_description: str | None = Field(default=None, max_length=2000)
    auto_improve: bool = True

    @field_validator("platform")
    @classmethod
    def platform_slug(cls, value: str) -> str:
        value = value.lower().strip()
        if not re.fullmatch(r"[a-z0-9_.-]{1,32}", value):
            raise ValueError("platform must be a short slug such as x, telegram or youtube")
        return value

    @field_validator("text")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("post text must not be blank")
        return value.strip()

    @field_validator("image_data_url")
    @classmethod
    def image_shape(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not value.startswith("data:image/") or ";base64," not in value:
            raise ValueError("image_data_url must be a base64 data:image/* URL")
        return value


class ReactionMix(BaseModel):
    positive: float
    neutral: float
    negative: float
    sarcastic: float


class SampleReaction(BaseModel):
    voice: str = Field(description="Short descriptor of the simulated member, e.g. 'early-career developer'")
    tone: Literal["positive", "neutral", "negative", "sarcastic"]
    text: str


class InterestedSubgroup(BaseModel):
    who: str
    why: str
    share_of_segment_pct: float


class SuggestedEdit(BaseModel):
    change: str
    expected_effect: str


class SegmentReaction(BaseModel):
    """What one segment agent returns for one post."""

    first_impression: str
    reaction_mix_pct: ReactionMix = Field(description="Share of the segment reacting each way; sums to 100")
    interested_pct: float = Field(description="Share of the segment that would be interested enough to engage (0-100)")
    engage_pct: float = Field(description="Share likely to like/comment/click (0-100)")
    share_pct: float = Field(description="Share likely to repost/forward (0-100)")
    interested_subgroups: list[InterestedSubgroup]
    sample_reactions: list[SampleReaction]
    what_works: list[str]
    what_fails: list[str]
    misread_risks: list[str]
    suggested_edits: list[SuggestedEdit]
    confidence: Literal["low", "medium", "high"]
    confidence_reason: str


class Recommendation(BaseModel):
    change: str
    rationale: str
    segments_helped: list[str]
    segments_at_risk: list[str]
    priority: Literal["high", "medium", "low"]


class AnalystOutput(BaseModel):
    headline: str
    verdict: Literal["post_as_is", "minor_edits", "major_rework", "do_not_post"]
    summary: str
    key_insights: list[str]
    risks: list[str]
    interested_audience_profile: str = Field(description="Demographic/psychographic description of who is interested")
    recommendations: list[Recommendation]
    should_rewrite: bool
    improved_post: str = Field(description="Rewritten post applying the recommendations; empty string if no rewrite")
    rewrite_notes: str


class SimulationOut(BaseModel):
    simulation_id: UUID
    segmentation_id: UUID
    status: str
    model_name: str
    platform: str
    post_text: str
    media: dict[str, Any]
    progress: dict[str, Any]
    baseline: dict[str, Any] | None
    analysis: dict[str, Any] | None
    improved_post: str | None
    improved: dict[str, Any] | None
    uplift: dict[str, Any] | None
    error: str | None
    created_at: datetime | None
    completed_at: datetime | None


class SimulationSummary(BaseModel):
    simulation_id: UUID
    status: str
    platform: str
    post_text: str
    created_at: datetime | None
    headline: str | None = None
