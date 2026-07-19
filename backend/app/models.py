"""Public API response models."""

from typing import Literal

from pydantic import BaseModel, Field


Verdict = Literal[
    "covered", "watch", "medical_desert", "underserved_need_unknown", "data_desert"
]


class CapabilityItem(BaseModel):
    id: str
    label: str
    has_need_signal: bool


class CapabilityList(BaseModel):
    capabilities: list[CapabilityItem]


class RegionResult(BaseModel):
    capability_id: str
    state: str
    district: str
    lat: float | None = None
    lon: float | None = None
    n_records: int
    n_candidates: int
    claiming: int
    corroborated: int
    trust_weighted_supply: float = Field(ge=0)
    coverage: float = Field(ge=0, le=1)
    knowledge: float = Field(ge=0, le=1)
    mean_source_trust: float = Field(ge=0, le=1)
    need_score: float | None = Field(default=None, ge=0, le=100)
    n_indicators: int
    data_confidence: Literal["solid", "thin", "data_desert"]
    verdict: Verdict
    risk_score: float = Field(ge=0, le=1)


class EvidenceItem(BaseModel):
    field: str
    snippet: str


class FacilityEvidence(BaseModel):
    capability_id: str
    facility_id: str
    name: str
    state: str
    district: str
    pin: str | None = None
    is_candidate: int
    claiming: int
    n_corroborating: int
    tier: Literal["strong", "moderate", "weak", "none"]
    trust_weight: float = Field(ge=0, le=1)
    knowledge: float = Field(ge=0, le=1)
    source_trust: float = Field(ge=0, le=1)
    data_confidence: Literal["high", "medium", "low"]
    evidence: list[EvidenceItem]
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    source_urls: str | None = None
