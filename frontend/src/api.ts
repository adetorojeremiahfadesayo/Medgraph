import type {
  BriefingResponse,
  CheckActionResponse,
  DischargeSummaryResponse,
  ForgetMemoryResponse,
  GuardrailAuditEntry,
  HealthResponse,
  ImproveMemoryResponse,
  MemoryStatus,
  Patient,
  ProtocolMemoryPayload,
  ProtocolMemoryResponse,
  ProposedActionPayload,
} from "./types";

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "https://medgraph-production.up.railway.app"
).replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function getPatients(): Promise<Patient[]> {
  return request<Patient[]>("/patients");
}

export function getPatient(patientId: string): Promise<Patient> {
  return request<Patient>(`/patients/${patientId}`);
}

export function getMemoryStatus(): Promise<MemoryStatus> {
  return request<MemoryStatus>("/memory/status");
}

export function getBriefing(patientId: string): Promise<BriefingResponse> {
  return request<BriefingResponse>(`/patients/${patientId}/briefing`);
}

export function getDischargeSummary(patientId: string): Promise<DischargeSummaryResponse> {
  return request<DischargeSummaryResponse>(`/patients/${patientId}/discharge-summary`);
}

export function checkAction(patientId: string, payload: ProposedActionPayload): Promise<CheckActionResponse> {
  return request<CheckActionResponse>(`/patients/${patientId}/check-action`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function rememberProtocol(protocolId: string, payload: ProtocolMemoryPayload): Promise<ProtocolMemoryResponse> {
  return request<ProtocolMemoryResponse>(`/memory/protocols/${protocolId}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function improvePatientMemory(patientId: string): Promise<ImproveMemoryResponse> {
  return request<ImproveMemoryResponse>(`/patients/${patientId}/memory/improve`, {
    method: "POST",
  });
}

export function forgetPatientMemory(patientId: string): Promise<ForgetMemoryResponse> {
  return request<ForgetMemoryResponse>(`/patients/${patientId}/memory`, {
    method: "DELETE",
  });
}

export function forgetProtocolMemory(protocolId: string): Promise<ForgetMemoryResponse> {
  return request<ForgetMemoryResponse>(`/memory/protocols/${protocolId}`, {
    method: "DELETE",
  });
}

export function improveProtocolMemory(protocolId: string): Promise<ImproveMemoryResponse> {
  return request<ImproveMemoryResponse>(`/memory/protocols/${protocolId}/improve`, {
    method: "POST",
  });
}

export function getGuardrailAudit(): Promise<GuardrailAuditEntry[]> {
  return request<GuardrailAuditEntry[]>("/guardrails/audit");
}
