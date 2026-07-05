# MedGraph Hackathon Submission

## Project Name

MedGraph

## Tagline

Every doctor gets the patient's full journey memory, without sending patient-sensitive memory to the cloud.

## Short Description

MedGraph is a synthetic hospital patient journey agent powered by a hybrid Cognee memory architecture. It tracks a patient from ER intake through handoffs, pharmacy review, safety checks, and discharge. Sensitive patient-scoped memory routes to local open-source Cognee, while non-sensitive protocol memory routes to Cognee Cloud for shared team knowledge.

## What We Built

- A FastAPI backend for synthetic patient journeys, guardrails, summaries, and memory routing.
- A React/Vite clinical dashboard for patient timeline, risk flags, briefing, memory status, and protocol writes.
- A one-click demo flow that proves the full patient journey story.
- A Cognee API usage panel that visibly demonstrates `remember`, `recall`, `improve`, and `forget`.
- A privacy split:
  - Local open-source Cognee: patient-sensitive journey memory.
  - Cognee Cloud: non-sensitive shared protocol memory.

## Cognee Usage

| Cognee operation | Where it appears | Storage scope |
|---|---|---|
| `remember` | proposed action check and protocol memory write | local patient memory + Cognee Cloud protocol memory |
| `recall` | clinician briefing and discharge summary | hybrid patient/protocol context |
| `improve` | local memory and cloud protocol refinement | local Cognee + Cognee Cloud |
| `forget` | patient memory removal | local patient memory |

## Safety Guardrails

MedGraph does not diagnose or prescribe. It surfaces synthetic context flags for clinician review, such as anticoagulant overlap, renal context, medication monitoring, and allergy context. The UI and API responses include a safety disclaimer: synthetic sample data only, not medical advice.

## Demo Script

1. Open the dashboard.
2. Point out Robert Johnson's synthetic journey: ER intake, cardiology handoff, pharmacy medication review.
3. Point out risk flags: anticoagulant overlap, renal context, metformin monitoring.
4. Click `Run workflow`.
5. Show each demo step turning `Done`.
6. Show the Cognee API usage panel proving all four lifecycle operations.
7. Explain the storage split:
   - patient-sensitive memory stayed local,
   - shared protocol memory went to Cognee Cloud,
   - patient local memory can be forgotten.

## 60-Second Pitch

Clinicians often lose context as a patient moves between departments. An ER doctor sees one part of the story, cardiology sees another, pharmacy catches medication issues later, and discharge summaries can miss why decisions were made.

MedGraph gives every clinician the patient's journey memory. In the sample workflow, Robert Johnson arrives with chest pain. The system remembers ER intake, cardiology handoff, medications, allergies, labs, and pharmacy review. When a doctor checks Heparin, MedGraph surfaces anticoagulant context because the patient is already on Warfarin.

The key is our hybrid Cognee architecture. Patient-sensitive memory stays local in open-source Cognee. Non-sensitive protocol knowledge, like anticoagulant review guidance, goes to Cognee Cloud for team-wide reuse. The dashboard visibly proves `remember`, `recall`, `improve`, and `forget`, including the ability to remove patient-scoped local memory.

MedGraph is not medical advice. It is a clinician-review memory layer built to preserve context safely.

## Run URLs

Frontend:

```text
http://127.0.0.1:5174/
```

Backend docs:

```text
http://127.0.0.1:8000/docs
```
