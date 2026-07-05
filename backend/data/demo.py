from __future__ import annotations

from datetime import datetime, timezone

from backend.models.clinical import Allergy, ClinicalEvent, Condition, LabResult, Medication, Patient


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def get_demo_patients() -> list[Patient]:
    johnson = Patient(
        id="patient-johnson",
        display_name="Robert Johnson",
        age=58,
        sex="M",
        synthetic=True,
        mrn="SYN-28847291",
        allergies=[
            Allergy(
                substance="Penicillin",
                severity="critical",
                reaction="Synthetic record notes prior anaphylaxis.",
                drug_class="beta-lactam",
            ),
            Allergy(
                substance="Sulfa drugs",
                severity="medium",
                reaction="Synthetic record notes moderate rash.",
            ),
        ],
        conditions=[
            Condition(
                name="Atrial fibrillation",
                evidence=["Long-term anticoagulation noted in synthetic intake record."],
            ),
            Condition(
                name="Type 2 diabetes",
                evidence=["Uses metformin in synthetic medication list."],
            ),
            Condition(
                name="Chronic kidney disease stage 3a",
                evidence=["Latest synthetic eGFR is 52 mL/min/1.73m2."],
            ),
        ],
        current_medications=[
            Medication(
                name="Warfarin",
                dose="5 mg daily",
                medication_class="anticoagulant",
                reason="Atrial fibrillation",
            ),
            Medication(
                name="Metformin",
                dose="500 mg twice daily",
                medication_class="biguanide",
                reason="Type 2 diabetes",
            ),
        ],
        events=[
            ClinicalEvent(
                id="event-er-intake",
                event_type="admission",
                title="ER intake for chest pain",
                department="Emergency",
                clinician="Dr. Sarah Kim",
                timestamp=_dt("2026-06-29T14:32:00"),
                notes=(
                    "Synthetic patient reports chest pain radiating to left arm. "
                    "Clinician records active warfarin use, metformin use, penicillin allergy, "
                    "and CKD stage 3a context."
                ),
                tests_ordered=["Troponin I", "ECG", "Chest X-ray", "Basic metabolic panel"],
                labs=[
                    LabResult(
                        name="eGFR",
                        value="52",
                        unit="mL/min/1.73m2",
                        flag="reduced",
                        collected_at=_dt("2026-06-29T15:05:00"),
                    ),
                    LabResult(
                        name="Troponin I",
                        value="0.8",
                        unit="ng/mL",
                        flag="elevated",
                        collected_at=_dt("2026-06-29T15:25:00"),
                    ),
                ],
                diagnoses=["Chest pain workup: possible acute coronary syndrome context"],
            ),
            ClinicalEvent(
                id="event-cardiology-handoff",
                event_type="handoff",
                title="Cardiology handoff",
                department="Cardiology",
                clinician="Dr. Anita Patel",
                timestamp=_dt("2026-06-29T16:45:00"),
                notes=(
                    "Cardiology receives ER context. Synthetic handoff highlights elevated "
                    "troponin, ST-segment changes in the ECG note, active warfarin, and reduced eGFR."
                ),
                tests_ordered=["Echocardiogram"],
                labs=[
                    LabResult(
                        name="Troponin I",
                        value="0.4",
                        unit="ng/mL",
                        flag="improving",
                        collected_at=_dt("2026-06-30T08:00:00"),
                    )
                ],
            ),
            ClinicalEvent(
                id="event-pharmacy-review",
                event_type="review",
                title="Pharmacy medication review",
                department="Pharmacy",
                clinician="Dr. Michael Chen",
                timestamp=_dt("2026-06-29T18:00:00"),
                notes=(
                    "Synthetic pharmacist review asks clinicians to verify anticoagulation plan, "
                    "renal monitoring, and discharge medication reconciliation."
                ),
            ),
        ],
    )
    return [johnson]


def get_cloud_protocols() -> list[str]:
    return [
        "Protocol memory: allergy context flags should surface related drug-class allergies for clinician review.",
        "Protocol memory: anticoagulant overlap should be marked as a high-priority medication context flag.",
        "Protocol memory: reduced eGFR should surface renal context before contrast imaging or renal-cleared medication decisions.",
        "Protocol memory: repeated tests inside a short stay should surface duplicate-order context, not hard-stop clinical care.",
    ]
