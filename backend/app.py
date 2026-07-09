from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.models.clinical import ClinicalEvent, ProposedAction, ProtocolMemoryInput
from backend.services.conflict_detection import ConflictDetectionService
from backend.services.guardrails import SAFETY_DISCLAIMER, GuardrailService
from backend.services.memory import MemoryRouter
from backend.services.patient_journey import PatientJourneyService
from backend.services.summaries import SummaryService


app = FastAPI(
    title="MedGraph API",
    description="Synthetic patient journey memory backend powered by local/cloud Cognee architecture.",
    version="0.1.0",
)

# Default is permissive so the deployed frontend can reach the API without extra
# configuration; set FRONTEND_ORIGINS to a comma-separated list to lock it down.
frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory_router = MemoryRouter()
guardrails = GuardrailService()
conflict_detection = ConflictDetectionService()
summaries = SummaryService()
journeys = PatientJourneyService(memory_router, conflict_detection)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "guardrails": "enabled",
        "memory": memory_router.status().model_dump(),
    }


@app.get("/patients")
def list_patients() -> list[dict]:
    return [patient.model_dump() for patient in journeys.list_patients()]


@app.get("/patients/{patient_id}")
def get_patient(patient_id: str) -> dict:
    patient = journeys.get_patient(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient.model_dump()


@app.post("/patients/{patient_id}/events")
def add_event(patient_id: str, event: ClinicalEvent) -> dict:
    patient = journeys.add_event(patient_id, event)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient.model_dump()


@app.post("/patients/{patient_id}/check-action")
def check_action(patient_id: str, action: ProposedAction) -> dict:
    guardrail = guardrails.evaluate(
        action="check_action",
        content=(
            f"Possible context flag for clinician review using synthetic demo data. "
            f"Action: {action.action_type} {action.name}. Notes: {action.notes}"
        ),
    )
    conflicts = journeys.check_action(patient_id, action)
    if conflicts is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "guardrail": guardrail.model_dump(),
        "conflicts": [conflict.model_dump() for conflict in conflicts],
        "disclaimer": SAFETY_DISCLAIMER,
    }


@app.get("/patients/{patient_id}/briefing")
def get_briefing(patient_id: str) -> dict:
    patient = journeys.get_patient(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    conflicts = journeys.active_conflicts(patient)
    briefing = summaries.build_briefing(patient, conflicts)
    guardrail = guardrails.evaluate(action="generate_briefing", content=briefing)
    return {
        "patient_id": patient.id,
        "briefing": briefing,
        "conflicts": [conflict.model_dump() for conflict in conflicts],
        "guardrail": guardrail.model_dump(),
        "disclaimer": SAFETY_DISCLAIMER,
    }


@app.get("/patients/{patient_id}/discharge-summary")
def get_discharge_summary(patient_id: str) -> dict:
    patient = journeys.get_patient(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    conflicts = journeys.active_conflicts(patient)
    summary = summaries.build_discharge_summary(patient, conflicts)
    guardrail = guardrails.evaluate(action="generate_discharge_summary", content=summary)
    return {
        "patient_id": patient.id,
        "summary": summary,
        "guardrail": guardrail.model_dump(),
        "disclaimer": SAFETY_DISCLAIMER,
    }


@app.get("/memory/status")
def memory_status() -> dict:
    return memory_router.status().model_dump()


@app.post("/memory/protocols/{protocol_id}")
def remember_protocol_memory(protocol_id: str, payload: ProtocolMemoryInput) -> dict:
    record = memory_router.remember_protocol(
        protocol_id,
        payload.content,
        metadata={"source": payload.source},
    )
    return {
        "protocol_id": protocol_id,
        "scope": "cloud_protocol",
        "record": record.model_dump(),
    }


@app.post("/patients/{patient_id}/memory/improve")
def improve_patient_memory(patient_id: str) -> dict:
    patient = journeys.get_patient(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    record = memory_router.improve_patient_memory(patient_id)
    return {
        "patient_id": patient_id,
        "scope": "local_patient",
        "record": record.model_dump(),
        "disclaimer": SAFETY_DISCLAIMER,
    }


@app.delete("/patients/{patient_id}/memory")
def forget_patient_memory(patient_id: str) -> dict:
    patient = journeys.get_patient(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    deleted_records = memory_router.forget_patient(patient_id)
    return {
        "patient_id": patient_id,
        "scope": "local_patient",
        "deleted_records": deleted_records,
        "disclaimer": SAFETY_DISCLAIMER,
    }


@app.delete("/memory/protocols/{protocol_id}")
def forget_protocol_memory(protocol_id: str) -> dict:
    deleted_records = memory_router.forget_protocol(protocol_id)
    return {
        "protocol_id": protocol_id,
        "scope": "cloud_protocol",
        "deleted_records": deleted_records,
    }


@app.post("/memory/protocols/{protocol_id}/improve")
def improve_protocol_memory(protocol_id: str) -> dict:
    record = memory_router.improve_protocol_memory(protocol_id)
    return {
        "protocol_id": protocol_id,
        "scope": "cloud_protocol",
        "record": record.model_dump(),
    }


@app.get("/guardrails/audit")
def guardrail_audit() -> list[dict]:
    return [entry.model_dump() for entry in guardrails.audit_log]
