"""Pydantic contracts for sources, claims, evidence, and epistemic history."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SourceKind = Literal["document", "url", "message", "user_statement", "agent_output", "dataset"]
ClaimType = Literal["factual", "causal", "normative", "predictive", "definition", "other"]
EpistemicStatus = Literal[
    "proposed", "reported", "inferred", "corroborated", "contested",
    "accepted", "rejected", "superseded", "unresolved", "unknown",
]
ActorKind = Literal["user", "agent", "system"]
OriginKind = Literal["user", "agent", "extraction", "import"]
AssessmentDimension = Literal[
    "source_reliability", "evidence_strength", "extraction_reliability",
    "verification_status", "temporal_validity", "argument_strength",
]
EvidenceStance = Literal["supports", "challenges", "context"]
ClaimRelation = Literal["contradicts", "supports", "supersedes", "refines", "depends_on"]
ContradictionBasis = Literal[
    "direct", "different_time", "different_context", "different_definition", "unclear"
]
QuestionState = Literal["open", "investigating", "answered", "dropped"]


class SourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    project_id: str | None = None
    kind: SourceKind
    title: str | None = Field(default=None, max_length=500)
    uri: str | None = Field(default=None, max_length=2_000)
    content_hash: str | None = Field(default=None, min_length=64, max_length=64)
    retrieved_at: str | None = Field(default=None, max_length=40)


class ClaimCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    project_id: str | None = None
    claim_type: ClaimType
    text: str = Field(min_length=1, max_length=20_000)
    subject: str | None = Field(default=None, max_length=2_000)
    predicate: str | None = Field(default=None, max_length=2_000)
    object: str | None = Field(default=None, max_length=2_000)
    valid_from: str | None = Field(default=None, max_length=40)
    valid_to: str | None = Field(default=None, max_length=40)
    origin_kind: OriginKind = "user"
    origin_ref: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_text(self):
        if not self.text.strip():
            raise ValueError("Claim text must contain non-whitespace text.")
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not precede valid_from.")
        return self


class ClaimStatusCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    status: EpistemicStatus
    scope: str = Field(default="default", min_length=1, max_length=300)
    policy: str | None = Field(default=None, max_length=500)
    rationale: str | None = Field(default=None, max_length=10_000)
    actor_kind: ActorKind = "user"
    actor_ref: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_policy(self):
        if self.status == "accepted" and not (self.policy and self.policy.strip()):
            raise ValueError("policy is required when status is accepted.")
        return self


class ClaimAssessmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    dimension: AssessmentDimension
    value_num: float | None = Field(default=None, ge=0, le=1)
    value_text: str | None = Field(default=None, max_length=2_000)
    rationale: str | None = Field(default=None, max_length=10_000)
    actor_kind: ActorKind = "user"
    actor_ref: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_value(self):
        if self.value_num is None and not (self.value_text and self.value_text.strip()):
            raise ValueError("An assessment requires value_num or value_text.")
        return self


class EvidenceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    source_id: str
    stance: EvidenceStance
    excerpt: str | None = Field(default=None, max_length=20_000)
    locator: str | None = Field(default=None, max_length=2_000)


class ClaimRelationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    to_claim_id: str
    rel: ClaimRelation
    contradiction_basis: ContradictionBasis | None = None
    note: str | None = Field(default=None, max_length=10_000)

    @model_validator(mode="after")
    def validate_basis(self):
        if self.rel == "contradicts" and self.contradiction_basis is None:
            raise ValueError("contradiction_basis is required for contradicts relations.")
        if self.rel != "contradicts" and self.contradiction_basis is not None:
            raise ValueError("contradiction_basis is only valid for contradicts relations.")
        return self


class OpenQuestionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    project_id: str | None = None
    text: str = Field(min_length=1, max_length=20_000)
    related_claim_id: str | None = None

    @model_validator(mode="after")
    def validate_text(self):
        if not self.text.strip():
            raise ValueError("Question text must contain non-whitespace text.")
        return self


class OpenQuestionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    state: QuestionState
