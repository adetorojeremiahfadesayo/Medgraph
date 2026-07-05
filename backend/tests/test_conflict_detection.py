from backend.data.demo import get_demo_patients
from backend.models.clinical import ProposedAction
from backend.services.conflict_detection import ConflictDetectionService


def test_detects_allergy_context_flag_for_penicillin_class_drug():
    patient = get_demo_patients()[0]
    service = ConflictDetectionService()

    conflicts = service.check_action(
        patient,
        ProposedAction(action_type="medication", name="Amoxicillin", requested_by="Dr. Kim"),
    )

    assert any(conflict.kind == "allergy" for conflict in conflicts)
    assert conflicts[0].requires_clinician_review is True


def test_detects_anticoagulant_context_flag():
    patient = get_demo_patients()[0]
    service = ConflictDetectionService()

    conflicts = service.check_action(
        patient,
        ProposedAction(action_type="medication", name="Heparin", requested_by="Dr. Kim"),
    )

    assert any(conflict.kind == "medication_context" for conflict in conflicts)
    assert any("warfarin" in conflict.evidence.lower() for conflict in conflicts)


def test_detects_renal_context_flag_for_contrast_imaging():
    patient = get_demo_patients()[0]
    service = ConflictDetectionService()

    conflicts = service.check_action(
        patient,
        ProposedAction(action_type="test", name="Contrast CT angiography", requested_by="Dr. Patel"),
    )

    assert any(conflict.kind == "renal_context" for conflict in conflicts)
    assert any(conflict.severity == "high" for conflict in conflicts)


def test_detects_duplicate_recent_test_context_flag():
    patient = get_demo_patients()[0]
    service = ConflictDetectionService()

    conflicts = service.check_action(
        patient,
        ProposedAction(action_type="test", name="Troponin I", requested_by="Dr. Kim"),
    )

    assert any(conflict.kind == "duplicate_test" for conflict in conflicts)
