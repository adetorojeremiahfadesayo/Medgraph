from backend.services.guardrails import GuardrailService


def test_guardrail_blocks_diagnosis_and_prescription_language():
    service = GuardrailService()

    decision = service.evaluate(
        action="generate_patient_advice",
        content="Diagnose NSTEMI and prescribe heparin immediately.",
    )

    assert decision.allowed is False
    assert decision.severity == "blocked"
    assert "diagnosis" in decision.reasons
    assert "prescription" in decision.reasons
    assert len(service.audit_log) == 1
    assert service.audit_log[0].allowed is False


def test_guardrail_allows_context_flags_with_required_safety_framing():
    service = GuardrailService()

    decision = service.evaluate(
        action="generate_briefing",
        content="Summarize patient context and surface possible flags for clinician review using synthetic demo data.",
    )

    assert decision.allowed is True
    assert decision.severity == "allowed"
    assert decision.required_disclaimer == (
        "Synthetic demo data only. Context flags are for clinician review and are not medical advice."
    )
    assert len(service.audit_log) == 1
    assert service.audit_log[0].action == "generate_briefing"
