from __future__ import annotations

from backend.models.clinical import ConflictFlag, Patient, ProposedAction


class ConflictDetectionService:
    """Deterministic clinical context checks for the synthetic demo."""

    penicillin_family = {"amoxicillin", "ampicillin", "penicillin"}
    anticoagulants = {"heparin", "warfarin", "apixaban", "rivaroxaban", "enoxaparin"}
    contrast_terms = {"contrast", "angiography", "ct angiography"}

    def check_action(self, patient: Patient, action: ProposedAction) -> list[ConflictFlag]:
        conflicts: list[ConflictFlag] = []
        name = action.name.lower()

        if action.action_type == "medication":
            conflicts.extend(self._check_allergy(patient, name))
            conflicts.extend(self._check_anticoagulant_context(patient, name))
            conflicts.extend(self._check_metformin_renal_context(patient, name))

        if action.action_type == "test":
            conflicts.extend(self._check_renal_contrast_context(patient, name))
            conflicts.extend(self._check_duplicate_test_context(patient, name))

        return conflicts

    def _check_allergy(self, patient: Patient, action_name: str) -> list[ConflictFlag]:
        has_penicillin_allergy = any(
            allergy.substance.lower() == "penicillin" for allergy in patient.allergies
        )
        if has_penicillin_allergy and any(term in action_name for term in self.penicillin_family):
            return [
                ConflictFlag(
                    kind="allergy",
                    severity="critical",
                    title="Possible allergy context flag",
                    evidence="Synthetic patient record lists penicillin anaphylaxis context.",
                    recommendation=(
                        "Clinician review required before beta-lactam medication decisions. "
                        "This is not medical advice."
                    ),
                )
            ]
        return []

    def _check_anticoagulant_context(self, patient: Patient, action_name: str) -> list[ConflictFlag]:
        proposed_is_anticoagulant = any(term in action_name for term in self.anticoagulants)
        active_anticoagulants = [
            med.name
            for med in patient.current_medications
            if (med.medication_class or "").lower() == "anticoagulant" and med.status == "active"
        ]

        if proposed_is_anticoagulant and active_anticoagulants:
            return [
                ConflictFlag(
                    kind="medication_context",
                    severity="high",
                    title="Possible anticoagulant overlap context",
                    evidence=f"Active medication list includes {', '.join(active_anticoagulants)}.",
                    recommendation=(
                        "Surface anticoagulation context, recent labs, and clinician notes for review."
                    ),
                )
            ]
        return []

    def _check_metformin_renal_context(self, patient: Patient, action_name: str) -> list[ConflictFlag]:
        if "metformin" not in action_name:
            return []
        egfr = self._latest_numeric_lab(patient, "egfr")
        if egfr is not None and egfr < 60:
            return [
                ConflictFlag(
                    kind="renal_medication_context",
                    severity="medium",
                    title="Renal monitoring context for metformin",
                    evidence=f"Latest synthetic eGFR is {egfr:g} mL/min/1.73m2.",
                    recommendation="Clinician review of renal monitoring and medication reconciliation.",
                )
            ]
        return []

    def _check_renal_contrast_context(self, patient: Patient, action_name: str) -> list[ConflictFlag]:
        if not any(term in action_name for term in self.contrast_terms):
            return []
        egfr = self._latest_numeric_lab(patient, "egfr")
        if egfr is not None and egfr < 60:
            return [
                ConflictFlag(
                    kind="renal_context",
                    severity="high",
                    title="Reduced kidney function context before contrast imaging",
                    evidence=f"Latest synthetic eGFR is {egfr:g} mL/min/1.73m2.",
                    recommendation=(
                        "Surface renal context and alternative-imaging discussion points for clinician review."
                    ),
                )
            ]
        return []

    def _check_duplicate_test_context(self, patient: Patient, action_name: str) -> list[ConflictFlag]:
        ordered_tests = {
            test.lower()
            for event in patient.events
            for test in event.tests_ordered
        }
        existing_lab_names = {
            lab.name.lower()
            for event in patient.events
            for lab in event.labs
        }
        if action_name in ordered_tests or action_name in existing_lab_names:
            return [
                ConflictFlag(
                    kind="duplicate_test",
                    severity="low",
                    title="Recent test context",
                    evidence=f"{action_name.title()} appears in the synthetic patient timeline.",
                    recommendation="Show recent order/result timeline before repeating the test.",
                )
            ]
        return []

    def _latest_numeric_lab(self, patient: Patient, lab_name: str) -> float | None:
        matching = [
            lab
            for event in patient.events
            for lab in event.labs
            if lab.name.lower() == lab_name.lower()
        ]
        if not matching:
            return None
        latest = max(matching, key=lambda lab: lab.collected_at)
        try:
            return float(latest.value)
        except ValueError:
            return None
