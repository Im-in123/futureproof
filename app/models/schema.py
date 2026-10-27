"""FutureProof data models."""
from __future__ import annotations
from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Verdict(str, Enum):
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT = "INSUFFICIENT"
    NO_EVIDENCE = "NO_EVIDENCE"


class Decision(str, Enum):
    ACCEPT = "ACCEPT"
    DOWNGRADE = "DOWNGRADE"
    REMOVE = "REMOVE"
    NO_EVIDENCE = "NO_EVIDENCE"


class SourceTier(str, Enum):
    OFFICIAL = "official"
    LEGAL_DB = "legal_db"
    COMMERCIAL = "commercial"
    BLOG = "blog"
    UNKNOWN = "unknown"


class Clause(BaseModel):
    clause_id: str
    text: str
    clause_type: str
    temporal_trigger: Optional[str] = None
    is_one_time: bool = False
    stated_amount: Optional[float] = None


class Event(BaseModel):
    event_id: str
    clause_id: str
    trigger_date: date
    is_one_time: bool = False
    dollar_amount: Optional[float] = None
    dollar_formula: Optional[str] = None
    dollar_basis: str = "unknown"
    rate_pct: Optional[float] = None
    probability: float = Field(ge=0.0, le=1.0)
    probability_basis: str
    description: str


class TavilyResult(BaseModel):
    event_id: str
    verdict: Verdict
    query: str
    source_url: Optional[str] = None
    source_tier: str = "unknown"
    snippet: Optional[str] = None
    published_date: Optional[str] = None
    jurisdiction_match: bool = False
    legal_rate_pct: Optional[float] = None


class GateResult(BaseModel):
    event_id: str
    decision: Decision
    rules_fired: list[str] = Field(default_factory=list)
    reason: str


class RateExtraction(BaseModel):
    rate: Optional[float] = None
    rate_kind: str = "unknown"
    effective_date: Optional[str] = None
    scope: str = "unknown"
    jurisdiction: Optional[str] = None
    source_url: Optional[str] = None
