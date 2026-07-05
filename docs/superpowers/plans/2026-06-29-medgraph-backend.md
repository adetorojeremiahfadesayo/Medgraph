# MedGraph Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the MedGraph backend first: synthetic patient journey APIs, dual Cognee memory routing, conflict checks, safety guardrails, and audit logs.

**Architecture:** FastAPI exposes patient, event, action-check, briefing, discharge, memory-status, and guardrail-audit endpoints. Services stay small: `MemoryRouter` owns local/cloud routing, `ConflictDetectionService` owns deterministic clinical context flags, `GuardrailService` blocks unsafe system behavior, and `PatientJourneyService` coordinates demo data.

**Tech Stack:** Python, FastAPI, Pydantic, pytest, optional Cognee SDK integration with a JSON fallback for local testing.

---

### Task 1: Backend Test Skeleton

**Files:**
- Create: `backend/tests/test_guardrails.py`
- Create: `backend/tests/test_conflict_detection.py`
- Create: `backend/tests/test_api.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Write failing tests**

Create tests that assert:
- diagnosis/prescription language is blocked by guardrails
- safe context-summary language is allowed and audited
- allergy, anticoagulant, renal-risk, and duplicate-test conflicts are detected
- core API endpoints return the seeded synthetic patient and safety metadata

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest backend/tests -q`
Expected: FAIL because `backend.app`, service modules, and models do not exist yet.

### Task 2: Domain Models And Demo Data

**Files:**
- Create: `backend/models/clinical.py`
- Create: `backend/data/demo.py`

- [ ] **Step 1: Implement Pydantic models**

Define patient, event, proposed action, conflict, guardrail, and memory record models.

- [ ] **Step 2: Implement synthetic sample data**

Seed one patient journey with corrected, synthetic medical examples and non-diagnostic wording.

- [ ] **Step 3: Run tests**

Run: `python -m pytest backend/tests -q`
Expected: Tests still fail until services and API are wired.

### Task 3: Guardrail And Conflict Services

**Files:**
- Create: `backend/services/guardrails.py`
- Create: `backend/services/conflict_detection.py`
- Create: `backend/services/summaries.py`

- [ ] **Step 1: Implement guardrail policy**

Block diagnosis/prescription imperatives, require synthetic-data disclaimers, and log every system-facing action.

- [ ] **Step 2: Implement deterministic conflict checks**

Detect possible allergy, anticoagulant, kidney/contrast, metformin/eGFR, and duplicate-test context flags.

- [ ] **Step 3: Implement doctor briefing and discharge summaries**

Return clinician-review language grounded in patient events and conflict state.

- [ ] **Step 4: Run tests**

Run: `python -m pytest backend/tests/test_guardrails.py backend/tests/test_conflict_detection.py -q`
Expected: PASS.

### Task 4: Memory Router

**Files:**
- Create: `backend/services/memory.py`
- Modify: `backend/config.py`

- [ ] **Step 1: Implement dual-memory routing**

Route private patient events to local open-source memory and shared protocols to cloud memory. Provide JSON fallback so the backend works without API keys.

- [ ] **Step 2: Expose memory status**

Show local enabled, cloud configured/not configured, and counts of patient/protocol memories.

- [ ] **Step 3: Run tests**

Run: `python -m pytest backend/tests -q`
Expected: API tests may still fail until FastAPI is wired.

### Task 5: FastAPI App

**Files:**
- Create: `backend/app.py`
- Create: `backend/__init__.py`
- Create: `backend/services/patient_journey.py`

- [ ] **Step 1: Wire services into API endpoints**

Implement:
- `GET /health`
- `GET /patients`
- `GET /patients/{patient_id}`
- `POST /patients/{patient_id}/events`
- `POST /patients/{patient_id}/check-action`
- `GET /patients/{patient_id}/briefing`
- `GET /patients/{patient_id}/discharge-summary`
- `GET /memory/status`
- `GET /guardrails/audit`

- [ ] **Step 2: Run all tests**

Run: `python -m pytest backend/tests -q`
Expected: PASS.

- [ ] **Step 3: Smoke test server**

Run: `python -m uvicorn backend.app:app --reload --port 8000`
Expected: server starts and `/docs` is available.
