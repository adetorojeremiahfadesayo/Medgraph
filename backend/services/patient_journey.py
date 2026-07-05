from __future__ import annotations

import os

from backend.data.demo import get_cloud_protocols, get_demo_patients
from backend.models.clinical import ClinicalEvent, ConflictFlag, Patient, ProposedAction
from backend.services.conflict_detection import ConflictDetectionService
from backend.services.memory import MemoryRouter


class PatientJourneyService:
    def __init__(self, memory: MemoryRouter, conflict_detection: ConflictDetectionService) -> None:
        self.memory = memory
        self.conflict_detection = conflict_detection
        self.patients: dict[str, Patient] = {patient.id: patient for patient in get_demo_patients()}
        self._seed_memory()

    def list_patients(self) -> list[Patient]:
        return list(self.patients.values())

    def get_patient(self, patient_id: str) -> Patient | None:
        return self.patients.get(patient_id)

    def add_event(self, patient_id: str, event: ClinicalEvent) -> Patient | None:
        patient = self.get_patient(patient_id)
        if patient is None:
            return None
        patient.events.append(event)
        self.memory.remember_patient_event(
            patient_id=patient.id,
            content=f"{event.title}: {event.notes}",
            metadata={"event_id": event.id, "department": event.department},
        )
        return patient

    def check_action(self, patient_id: str, action: ProposedAction) -> list[ConflictFlag] | None:
        patient = self.get_patient(patient_id)
        if patient is None:
            return None
        conflicts = self.conflict_detection.check_action(patient, action)
        self.memory.remember_patient_event(
            patient_id=patient.id,
            content=f"Action checked: {action.action_type} {action.name}; conflicts={len(conflicts)}",
            metadata={"requested_by": action.requested_by},
        )
        return conflicts

    def active_conflicts(self, patient: Patient) -> list[ConflictFlag]:
        demo_actions = [
            ProposedAction(action_type="medication", name="Heparin", requested_by="demo"),
            ProposedAction(action_type="test", name="Contrast CT angiography", requested_by="demo"),
            ProposedAction(action_type="medication", name="Metformin", requested_by="demo"),
        ]
        conflicts: list[ConflictFlag] = []
        for action in demo_actions:
            conflicts.extend(self.conflict_detection.check_action(patient, action))
        return conflicts

    def _seed_memory(self) -> None:
        status = self.memory.status()
        real_backend_active = (
            status.local_backend != "json_fallback" or status.cloud_backend != "json_fallback"
        )
        should_seed_real_backends = os.getenv("MEDGRAPH_SEED_MEMORY_ON_START", "false").lower() == "true"
        if real_backend_active and not should_seed_real_backends:
            return

        for patient in self.patients.values():
            self.memory.remember_patient_event(
                patient.id,
                (
                    f"Synthetic patient journey memory for {patient.display_name}: "
                    f"{len(patient.events)} events, {len(patient.current_medications)} medications, "
                    f"{len(patient.allergies)} allergies."
                ),
                metadata={"synthetic": True},
            )
            for event in patient.events:
                self.memory.remember_patient_event(
                    patient.id,
                    f"{event.department} event {event.title}: {event.notes}",
                    metadata={"event_id": event.id},
                )
        for index, protocol in enumerate(get_cloud_protocols(), start=1):
            self.memory.remember_protocol(f"protocol-{index}", protocol)
