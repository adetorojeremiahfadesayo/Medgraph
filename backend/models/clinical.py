from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


Severity = Literal["critical", "high", "medium", "low", "info"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Allergy(BaseModel):
    substance: str
    severity: Severity
    reaction: str
    drug_class: str | None = None


class Condition(BaseModel):
    name: str
    status: str = "active"
    evidence: list[str] = Field(default_factory=list)


class Medication(BaseModel):
    name: str
    dose: str
    status: str = "active"
    medication_class: str | None = None
    reason: str | None = None


class LabResult(BaseModel):
    name: str
    value: str
    unit: str | None = None
    flag: str | None = None
    collected_at: datetime = Field(default_factory=utc_now)


class ClinicalEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"event-{uuid4().hex[:8]}")
    event_type: Literal["admission", "test", "medication", "handoff", "review", "rounds", "discharge", "note"]
    title: str
    department: str
    clinician: str
    timestamp: datetime = Field(default_factory=utc_now)
    notes: str
    tests_ordered: list[str] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    labs: list[LabResult] = Field(default_factory=list)
    diagnoses: list[str] = Field(default_factory=list)


class Patient(BaseModel):
    id: str
    display_name: str
    age: int
    sex: str
    synthetic: bool = True
    mrn: str
    allergies: list[Allergy] = Field(default_factory=list)
    conditions: list[Condition] = Field(default_factory=list)
    current_medications: list[Medication] = Field(default_factory=list)
    events: list[ClinicalEvent] = Field(default_factory=list)


class ProposedAction(BaseModel):
    action_type: Literal["medication", "test", "diagnosis", "note", "handoff"]
    name: str
    requested_by: str
    notes: str = ""


class ProtocolMemoryInput(BaseModel):
    content: str
    source: str = "manual_mvp"


class ConflictFlag(BaseModel):
    id: str = Field(default_factory=lambda: f"conflict-{uuid4().hex[:8]}")
    kind: str
    severity: Severity
    title: str
    evidence: str
    recommendation: str
    requires_clinician_review: bool = True
    source: Literal["local_patient_brain", "cloud_protocol_brain", "hybrid"] = "hybrid"


class GuardrailDecision(BaseModel):
    allowed: bool
    severity: Literal["allowed", "needs_review", "blocked"]
    reasons: list[str] = Field(default_factory=list)
    required_disclaimer: str


class GuardrailAuditEntry(BaseModel):
    id: str = Field(default_factory=lambda: f"audit-{uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=utc_now)
    action: str
    allowed: bool
    severity: str
    reasons: list[str] = Field(default_factory=list)
    content_preview: str


class MemoryRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"memory-{uuid4().hex[:8]}")
    scope: Literal["local_patient", "cloud_protocol"]
    dataset_id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class MemoryStatus(BaseModel):
    local_mode: str = "open_source_cognee"
    cloud_mode: str = "cognee_cloud"
    cloud_configured: bool
    local_backend: str = "json_fallback"
    cloud_backend: str = "json_fallback"
    local_records: int
    cloud_records: int
    note: str
