from fastapi.testclient import TestClient

from backend.app import app


client = TestClient(app)


def test_health_reports_guardrails_and_memory_modes():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["guardrails"] == "enabled"
    assert body["memory"]["local_mode"] == "open_source_cognee"
    assert body["memory"]["cloud_mode"] == "cognee_cloud"


def test_lists_seeded_demo_patient():
    response = client.get("/patients")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == "patient-johnson"
    assert body[0]["synthetic"] is True


def test_check_action_returns_conflicts_and_guardrail_decision():
    response = client.post(
        "/patients/patient-johnson/check-action",
        json={
            "action_type": "medication",
            "name": "Heparin",
            "requested_by": "Dr. Kim",
            "notes": "Possible anticoagulant bridge therapy context flag for clinician review.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["guardrail"]["allowed"] is True
    assert any(conflict["kind"] == "medication_context" for conflict in body["conflicts"])


def test_briefing_uses_safety_framing():
    response = client.get("/patients/patient-johnson/briefing")

    assert response.status_code == 200
    body = response.json()
    assert body["guardrail"]["allowed"] is True
    assert "Synthetic demo data only" in body["disclaimer"]
    assert "clinician review" in body["briefing"].lower()


def test_guardrail_audit_records_ai_facing_actions():
    client.get("/patients/patient-johnson/briefing")
    response = client.get("/guardrails/audit")

    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert body[-1]["action"] == "generate_briefing"


def test_can_improve_patient_memory_for_cognee_demo():
    response = client.post("/patients/patient-johnson/memory/improve")

    assert response.status_code == 200
    body = response.json()
    assert body["record"]["scope"] == "local_patient"
    assert body["record"]["metadata"]["operation"] == "improve"


def test_can_forget_patient_memory_for_cognee_demo():
    response = client.delete("/patients/patient-johnson/memory")

    assert response.status_code == 200
    body = response.json()
    assert body["patient_id"] == "patient-johnson"
    assert body["scope"] == "local_patient"
    assert body["deleted_records"] >= 0


def test_can_forget_protocol_memory_for_cloud_demo():
    client.post(
        "/memory/protocols/protocol-reset-test",
        json={
            "content": "Temporary protocol memory for reset endpoint coverage.",
            "source": "pytest",
        },
    )

    response = client.delete("/memory/protocols/protocol-reset-test")

    assert response.status_code == 200
    body = response.json()
    assert body["protocol_id"] == "protocol-reset-test"
    assert body["scope"] == "cloud_protocol"
    assert body["deleted_records"] >= 1


def test_can_improve_protocol_memory_for_cloud_demo():
    response = client.post("/memory/protocols/protocol-1/improve")

    assert response.status_code == 200
    body = response.json()
    assert body["record"]["scope"] == "cloud_protocol"
    assert body["record"]["metadata"]["operation"] == "improve"


def test_can_remember_protocol_memory_for_cloud_demo():
    response = client.post(
        "/memory/protocols/protocol-test",
        json={
            "content": "Protocol context flag for clinician review using synthetic demo data.",
            "source": "pytest",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["record"]["scope"] == "cloud_protocol"
    assert body["record"]["metadata"]["source"] == "pytest"
