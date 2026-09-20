from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EdgeRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    event_id: UUID
    platform: str
    source_platform_user_id: str
    target_platform_user_id: str
    interaction_type: str
    weight: float = Field(gt=0)
    occurred_at: datetime


class NodeMetrics(BaseModel):
    node_id: str
    in_degree_centrality: float
    out_degree_centrality: float
    betweenness_centrality: float
    closeness_centrality: float
    pagerank: float
    hub_score: float
    authority_score: float
    community: int | None = None


class NetworkSummary(BaseModel):
    nodes: int
    edges: int
    density: float
    communities: int
    metrics: list[NodeMetrics]
    interpretation: str = (
        "These structural metrics describe collected interactions; they are not causal measures of real-world influence."
    )

