# MedGraph Guided UI Design

## Goal

Personalize MedGraph with Kimi's cinematic patient-journey workflow while keeping our working FastAPI backend, local Cognee memory, Cognee Cloud protocol memory, and guardrail proof intact.

## Direction

The frontend becomes a user-friendly guided workflow instead of only a dense dashboard. The first viewport introduces MedGraph through an animated clinical knowledge graph, a guided helper named Nora, and a step rail for the full patient journey. The graph nodes are inspectable so users can click into patient, visit, clinician, medication, lab, and protocol memory relationships.

## Borrowed From Kimi

- Dark clinical graph stage with connected patient, doctor, lab, medication, condition, and protocol nodes.
- Five-step workflow rhythm: admission, recall, treatment safety, protocol memory, discharge/forget.
- High-contrast medical status styling and motion that helps users follow state changes.

## Preserved From Our Project

- Existing `src/api.ts` backend calls remain the only path to Cognee and guardrail behavior.
- Frontend exposes only `VITE_API_BASE_URL`; no Cognee, Qwen, LLM, or embedding keys are bundled.
- Dashboard panels for patient selection, journey timeline, briefing, action check, protocol write, memory status, API usage, and guardrail audit remain available.

## User Guide Behavior

Nora is a guided workflow companion for the MVP. She does not make independent medical decisions. She explains what each step is proving, highlights which Cognee lifecycle action is active, and offers common user questions about local memory, cloud memory, guardrails, and forgetting. Nora uses clinical workflow-progress language rather than game-like scoring language.

## Implementation Scope

- Modify `frontend/src/App.tsx` to add the hero graph, guide panel, guided workflow rail, and active-step derivation.
- Modify `frontend/src/styles.css` to add the darker first viewport, graph styling, guide states, workflow rail, and responsive behavior.
- Do not add frontend secrets or new required backend endpoints.

## Verification

- Run `npm run build` in `frontend`.
- Run a secret-pattern scan over docs and frontend source.
- Start or confirm the dev server and provide the local URL.
