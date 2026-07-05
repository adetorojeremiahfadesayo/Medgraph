export type Severity = "critical" | "high" | "medium" | "low" | "info";

export interface Allergy {
  substance: string;
  severity: Severity;
  reaction: string;
  drug_class?: string | null;
}

export interface Condition {
  name: string;
  status: string;
  evidence: string[];
}

export interface Medication {
  name: string;
  dose: string;
  status: string;
  medication_class?: string | null;
  reason?: string | null;
}

export interface LabResult {
  name: string;
  value: string;
  unit?: string | null;
  flag?: string | null;
  collected_at: string;
}

export interface ClinicalEvent {
  id: string;
  event_type: "admission" | "test" | "medication" | "handoff" | "review" | "rounds" | "discharge" | "note";
  title: string;
  department: string;
  clinician: string;
  timestamp: string;
  notes: string;
  tests_ordered: string[];
  medications: Medication[];
  labs: LabResult[];
  diagnoses: string[];
}

export interface Patient {
  id: string;
  display_name: string;
  age: number;
  sex: string;
  synthetic: boolean;
  mrn: string;
  allergies: Allergy[];
  conditions: Condition[];
  current_medications: Medication[];
  events: ClinicalEvent[];
}

export interface MemoryStatus {
  local_mode: string;
  cloud_mode: string;
  cloud_configured: boolean;
  local_backend: string;
  cloud_backend: string;
  local_records: number;
  cloud_records: number;
  note: string;
}

export interface HealthResponse {
  status: string;
  guardrails: string;
  memory: MemoryStatus;
}

export interface GuardrailDecision {
  allowed: boolean;
  severity: "allowed" | "needs_review" | "blocked";
  reasons: string[];
  required_disclaimer: string;
}

export interface ConflictFlag {
  id: string;
  kind: string;
  severity: Severity;
  title: string;
  evidence: string;
  recommendation: string;
  requires_clinician_review: boolean;
  source: "local_patient_brain" | "cloud_protocol_brain" | "hybrid";
}

export interface BriefingResponse {
  patient_id: string;
  briefing: string;
  conflicts: ConflictFlag[];
  guardrail: GuardrailDecision;
  disclaimer: string;
}

export interface DischargeSummaryResponse {
  patient_id: string;
  summary: string;
  guardrail: GuardrailDecision;
  disclaimer: string;
}

export interface ProposedActionPayload {
  action_type: "medication" | "test" | "diagnosis" | "note" | "handoff";
  name: string;
  requested_by: string;
  notes: string;
}

export interface CheckActionResponse {
  guardrail: GuardrailDecision;
  conflicts: ConflictFlag[];
  disclaimer: string;
}

export interface ProtocolMemoryPayload {
  content: string;
  source: string;
}

export interface MemoryRecord {
  id: string;
  scope: "local_patient" | "cloud_protocol";
  dataset_id: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ProtocolMemoryResponse {
  protocol_id: string;
  scope: "cloud_protocol";
  record: MemoryRecord;
}

export interface ImproveMemoryResponse {
  patient_id?: string;
  protocol_id?: string;
  scope: "local_patient" | "cloud_protocol";
  record: MemoryRecord;
  disclaimer?: string;
}

export interface ForgetMemoryResponse {
  patient_id?: string;
  protocol_id?: string;
  scope: "local_patient" | "cloud_protocol";
  deleted_records: number;
  disclaimer?: string;
}

export interface GuardrailAuditEntry {
  id: string;
  timestamp: string;
  action: string;
  allowed: boolean;
  severity: string;
  reasons: string[];
  content_preview: string;
}
