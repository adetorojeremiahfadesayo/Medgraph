from __future__ import annotations

from backend.models.clinical import ConflictFlag, Patient


class SummaryService:
    def build_briefing(self, patient: Patient, conflicts: list[ConflictFlag]) -> str:
        latest_events = sorted(patient.events, key=lambda event: event.timestamp)[-3:]
        event_lines = [
            f"{event.department}: {event.title} by {event.clinician}" for event in latest_events
        ]
        conflict_lines = [
            f"{flag.severity.upper()} {flag.kind}: {flag.title}" for flag in conflicts
        ]
        meds = ", ".join(med.name for med in patient.current_medications)
        allergies = ", ".join(allergy.substance for allergy in patient.allergies)

        return (
            f"Synthetic clinician-review briefing for {patient.display_name}. "
            f"Active medication context: {meds}. Allergy context: {allergies}. "
            f"Recent journey: {'; '.join(event_lines)}. "
            f"Possible context flags for clinician review: {'; '.join(conflict_lines) if conflict_lines else 'none active'}."
        )

    def build_discharge_summary(self, patient: Patient, conflicts: list[ConflictFlag]) -> str:
        event_titles = " -> ".join(
            event.title for event in sorted(patient.events, key=lambda event: event.timestamp)
        )
        conflict_titles = ", ".join(flag.title for flag in conflicts) or "No active context flags"
        return (
            f"Synthetic discharge memory summary for {patient.display_name}. "
            f"Journey timeline: {event_titles}. "
            f"Medication reconciliation context: {', '.join(med.name for med in patient.current_medications)}. "
            f"Conflict review trail: {conflict_titles}. "
            "This summary is for clinician review and is not medical advice."
        )
