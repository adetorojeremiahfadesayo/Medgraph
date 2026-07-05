from __future__ import annotations

import re

from backend.models.clinical import GuardrailAuditEntry, GuardrailDecision


SAFETY_DISCLAIMER = (
    "Synthetic demo data only. Context flags are for clinician review and are not medical advice."
)


class GuardrailService:
    """Policy gate for all AI-facing text MedGraph emits or accepts."""

    diagnosis_terms = {
        "diagnose",
        "diagnosis is",
        "confirmed diagnosis",
        "you have",
    }
    prescription_terms = {
        "prescribe",
        "start heparin immediately",
        "take",
        "stop taking",
        "block prescription",
    }
    allowed_context_terms = {
        "possible",
        "context flag",
        "clinician review",
        "synthetic",
        "not medical advice",
    }

    def __init__(self) -> None:
        self.audit_log: list[GuardrailAuditEntry] = []

    def evaluate(self, action: str, content: str) -> GuardrailDecision:
        normalized = content.lower()
        reasons: list[str] = []

        if self._contains_policy_term(normalized, self.diagnosis_terms):
            reasons.append("diagnosis")
        if self._contains_policy_term(normalized, self.prescription_terms):
            reasons.append("prescription")

        allowed = not reasons
        severity = "allowed" if allowed else "blocked"

        if allowed and not any(term in normalized for term in self.allowed_context_terms):
            severity = "needs_review"
            reasons.append("missing_safety_framing")

        decision = GuardrailDecision(
            allowed=allowed,
            severity=severity,
            reasons=reasons,
            required_disclaimer=SAFETY_DISCLAIMER,
        )
        self.audit_log.append(
            GuardrailAuditEntry(
                action=action,
                allowed=decision.allowed,
                severity=decision.severity,
                reasons=decision.reasons,
                content_preview=content[:180],
            )
        )
        return decision

    def _contains_policy_term(self, content: str, terms: set[str]) -> bool:
        for term in terms:
            pattern = r"\b" + re.escape(term).replace(r"\ ", r"\s+") + r"\b"
            if re.search(pattern, content):
                return True
        return False
