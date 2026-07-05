import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  ChevronRight,
  Cloud,
  Download,
  GitBranch,
  History,
  Loader2,
  PencilLine,
  PlayCircle,
  RefreshCw,
  ShieldCheck,
  Trash2,
  XCircle,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  checkAction,
  forgetPatientMemory,
  forgetProtocolMemory,
  getBriefing,
  getDischargeSummary,
  getGuardrailAudit,
  getHealth,
  getMemoryStatus,
  getPatient,
  getPatients,
  improvePatientMemory,
  improveProtocolMemory,
  rememberProtocol,
} from "./api";
import type {
  BriefingResponse,
  CheckActionResponse,
  ClinicalEvent,
  ConflictFlag,
  DischargeSummaryResponse,
  GuardrailAuditEntry,
  HealthResponse,
  MemoryStatus,
  Patient,
  ProtocolMemoryResponse,
  ProposedActionPayload,
  Severity,
} from "./types";

type OperationStatus = "idle" | "running" | "done" | "error";
type OperationId = "remember" | "recall" | "improve" | "forget";
type DemoStepId = "recall" | "safety" | "cloud" | "improve" | "forget";
type DraftStatus = "editing" | "accepted" | "needs_edit" | "rejected";

interface ApiUsageItem {
  id: OperationId;
  label: string;
  route: string;
  scope: string;
  status: OperationStatus;
  detail: string;
}

interface DemoStep {
  id: DemoStepId;
  title: string;
  description: string;
  status: OperationStatus;
}

interface GraphNode {
  id: string;
  label: string;
  type: string;
  x: number;
  y: number;
  r: number;
  tone: string;
  scope: string;
  summary: string;
}

interface DraftHistoryEntry {
  id: string;
  status: DraftStatus;
  label: string;
  at: string;
}

const defaultAction: ProposedActionPayload = {
  action_type: "medication",
  name: "Heparin",
  requested_by: "Dr. Kim",
  notes: "Check anticoagulant overlap before ordering.",
};

const defaultProtocol = {
  id: "medgraph-anticoagulant-review",
  content: "For anticoagulant review, check active meds, INR, renal function, and pharmacy notes.",
  source: "frontend_mvp",
};

function createApiUsageItems(): ApiUsageItem[] {
  return [
    {
      id: "recall",
      label: "recall",
      route: "GET briefing",
      scope: "Patient context",
      status: "idle",
      detail: "Ready",
    },
    {
      id: "remember",
      label: "remember",
      route: "POST action/protocol",
      scope: "Patient + protocol",
      status: "idle",
      detail: "Ready",
    },
    {
      id: "improve",
      label: "improve",
      route: "POST memory improve",
      scope: "Local + cloud",
      status: "idle",
      detail: "Ready",
    },
    {
      id: "forget",
      label: "forget",
      route: "DELETE memory",
      scope: "Patient or protocol",
      status: "idle",
      detail: "Ready",
    },
  ];
}

function createDemoSteps(): DemoStep[] {
  return [
    { id: "recall", title: "Open case", description: "Load timeline", status: "idle" },
    { id: "safety", title: "Check action", description: "Review Heparin", status: "idle" },
    { id: "cloud", title: "Save protocol", description: "Cloud guidance", status: "idle" },
    { id: "improve", title: "Improve memory", description: "Refine records", status: "idle" },
    { id: "forget", title: "Reset demo", description: "Clear memory", status: "idle" },
  ];
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function severityRank(severity: Severity | string): number {
  const order: Record<string, number> = { critical: 5, high: 4, medium: 3, low: 2, info: 1 };
  return order[severity] ?? 0;
}

function statusTone(status: OperationStatus): "good" | "warn" | "danger" | "neutral" {
  if (status === "done") return "good";
  if (status === "running") return "warn";
  if (status === "error") return "danger";
  return "neutral";
}

function statusLabel(status: OperationStatus): string {
  return status === "idle" ? "ready" : status;
}

function activeStepLabel(steps: DemoStep[]): string {
  const running = steps.find((step) => step.status === "running");
  if (running) return running.title;
  const lastDone = [...steps].reverse().find((step) => step.status === "done");
  return lastDone?.title ?? "Ready";
}

function draftStatusLabel(status: DraftStatus): string {
  if (status === "needs_edit") return "needs edit";
  return status;
}

function draftStatusTone(status: DraftStatus): "good" | "warn" | "danger" | "neutral" {
  if (status === "accepted") return "good";
  if (status === "needs_edit") return "warn";
  if (status === "rejected") return "danger";
  return "neutral";
}

function StatusPill({
  label,
  tone = "neutral",
}: {
  label: string;
  tone?: "good" | "warn" | "danger" | "neutral";
}) {
  return <span className={`status-pill ${tone}`}>{label}</span>;
}

function SectionHeader({
  eyebrow,
  title,
  summary,
  action,
}: {
  eyebrow: string;
  title: string;
  summary?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="section-header">
      <div>
        <p className="section-label">{eyebrow}</p>
        <h2>{title}</h2>
        {summary ? <p>{summary}</p> : null}
      </div>
      {action ? <div className="section-action">{action}</div> : null}
    </div>
  );
}

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function ContinueButton({ target, label }: { target: string; label: string }) {
  return (
    <div className="page-continue">
      <button type="button" className="secondary-button" onClick={() => scrollToSection(target)}>
        {label}
        <ChevronRight size={16} />
      </button>
    </div>
  );
}

function ReadableText({ text }: { text: string }) {
  const paragraphs = text
    .split(/(?<=\.)\s+/)
    .map((part) => part.trim())
    .filter(Boolean);

  return (
    <div className="readable-copy">
      {paragraphs.map((paragraph, index) => (
        <p key={`${paragraph.slice(0, 18)}-${index}`}>{paragraph}</p>
      ))}
    </div>
  );
}

function DischargeDraftEditor({ summary }: { summary: string | null }) {
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState<DraftStatus>("editing");
  const [history, setHistory] = useState<DraftHistoryEntry[]>([]);

  useEffect(() => {
    setDraft(summary ?? "");
    setStatus("editing");
    setHistory([]);
  }, [summary]);

  function recordStatus(nextStatus: DraftStatus, label: string) {
    setStatus(nextStatus);
    setHistory((items) => [
      {
        id: `${nextStatus}-${Date.now()}`,
        status: nextStatus,
        label,
        at: new Intl.DateTimeFormat("en", { hour: "numeric", minute: "2-digit" }).format(new Date()),
      },
      ...items,
    ]);
  }

  function handleDraftChange(value: string) {
    setDraft(value);
    if (status !== "editing") {
      setStatus("editing");
    }
  }

  function downloadDraft() {
    const blob = new Blob([draft], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "medgraph-discharge-draft.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <article className="discharge-editor">
      <div className="document-toolbar">
        <div>
          <label htmlFor="discharge-draft">Discharge draft</label>
          <StatusPill label={draftStatusLabel(status)} tone={draftStatusTone(status)} />
        </div>
        <button type="button" className="icon-button soft" onClick={downloadDraft} aria-label="Download discharge draft">
          <Download size={16} />
        </button>
      </div>

      <textarea
        id="discharge-draft"
        value={draft}
        onChange={(event) => handleDraftChange(event.target.value)}
        aria-label="Editable discharge draft"
      />

      <div className="document-actions" aria-label="Discharge draft review actions">
        <button type="button" className="secondary-button" onClick={() => recordStatus("accepted", "Accepted for review")}>
          <CheckCircle2 size={16} />
          Accept
        </button>
        <button type="button" className="secondary-button" onClick={() => recordStatus("needs_edit", "Marked for edits")}>
          <PencilLine size={16} />
          Needs edit
        </button>
        <button type="button" className="danger-button" onClick={() => recordStatus("rejected", "Rejected draft")}>
          <XCircle size={16} />
          Reject
        </button>
      </div>

      <div className="document-history">
        <h4>
          <History size={15} />
          Change history
        </h4>
        {history.length === 0 ? (
          <p>No review action yet.</p>
        ) : (
          <ul>
            {history.map((item) => (
              <li key={item.id}>
                <StatusPill label={draftStatusLabel(item.status)} tone={draftStatusTone(item.status)} />
                <span>{item.label}</span>
                <small>{item.at}</small>
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  );
}

function JourneyRail({ steps }: { steps: DemoStep[] }) {
  return (
    <aside className="journey-rail" aria-label="Journey status">
      <div className="brand">
        <span className="brand-mark">
          <MedGraphMark />
        </span>
        <div>
          <strong>MedGraph</strong>
          <span>Case journey</span>
        </div>
      </div>
      <div className="rail-steps">
        {steps.map((step, index) => (
          <article key={step.id} className={`rail-step ${step.status}`}>
            <span>{index + 1}</span>
            <div>
              <strong>{step.title}</strong>
              <small>{statusLabel(step.status)}</small>
            </div>
          </article>
        ))}
      </div>
    </aside>
  );
}

function MedGraphMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 32 32" width="24" height="24" fill="none">
      <path d="M7 18.5C7 12.7 10.8 8 15.8 8c3.9 0 7.1 2.8 8.2 6.8" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M8.2 18.5h4l2.1-4.8 3.2 8.8 2.1-4h4.2" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M23.8 18.5c-.8 3.3-3.7 5.5-8 5.5-2.8 0-5.7-1.4-7.6-4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

function MiniKnowledgeGraph({
  patient,
  memory,
  conflicts,
}: {
  patient: Patient | null;
  memory: MemoryStatus | null;
  conflicts: ConflictFlag[];
}) {
  const [selectedNodeId, setSelectedNodeId] = useState("patient");
  const erEvent = patient?.events.find((event) => event.department.toLowerCase().includes("emergency")) ?? patient?.events[0];
  const cardioEvent = patient?.events.find((event) => event.department.toLowerCase().includes("cardio"));
  const warfarin = patient?.current_medications.find((medication) => medication.name.toLowerCase().includes("warfarin"));
  const lab = patient?.events.flatMap((event) => event.labs).find((item) => item.flag);

  const graphNodes: GraphNode[] = [
    {
      id: "patient",
      label: patient?.display_name ?? "Case",
      type: "Patient",
      x: 50,
      y: 44,
      r: 9,
      tone: "cyan",
      scope: "Local",
      summary: patient ? `${patient.age} years / ${patient.sex} / ${patient.mrn}` : "Waiting for case context.",
    },
    {
      id: "er",
      label: "ER",
      type: "Visit",
      x: 24,
      y: 26,
      r: 6,
      tone: "blue",
      scope: "Local",
      summary: erEvent?.notes ?? "Admission context",
    },
    {
      id: "cardio",
      label: "Cardiology",
      type: "Handoff",
      x: 73,
      y: 27,
      r: 6,
      tone: "violet",
      scope: "Local",
      summary: cardioEvent?.notes ?? "Specialist handoff",
    },
    {
      id: "warfarin",
      label: "Warfarin",
      type: "Medication",
      x: 27,
      y: 63,
      r: 5,
      tone: "green",
      scope: "Local",
      summary: warfarin ? `${warfarin.name} ${warfarin.dose}` : "Medication history",
    },
    {
      id: "lab",
      label: lab?.name ?? "Labs",
      type: "Evidence",
      x: 56,
      y: 68,
      r: 5,
      tone: "amber",
      scope: "Local",
      summary: lab ? `${lab.value} ${lab.unit ?? ""}`.trim() : "Lab evidence",
    },
    {
      id: "protocol",
      label: "Protocol",
      type: "Cloud",
      x: 81,
      y: 62,
      r: 7,
      tone: "white",
      scope: "Cloud",
      summary: memory?.cloud_configured ? `${memory.cloud_records} protocol records` : "Cloud not configured",
    },
  ];

  const selectedNode = graphNodes.find((node) => node.id === selectedNodeId) ?? graphNodes[0];
  const links = [
    ["patient", "er"],
    ["patient", "cardio"],
    ["patient", "warfarin"],
    ["patient", "lab"],
    ["patient", "protocol"],
    ["cardio", "protocol"],
    ["warfarin", "lab"],
  ];
  const colorByTone: Record<string, string> = {
    cyan: "#28d7ff",
    blue: "#4598ff",
    violet: "#9a7cff",
    green: "#35d07f",
    amber: "#ffb84c",
    white: "#f7fbff",
  };

  return (
    <section className="command-map" aria-label="MedGraph patient memory graph">
      <div className="map-chrome">
        <span>
          <GitBranch size={16} />
        </span>
        <div>
          <strong>Memory graph</strong>
          <small>Local case + cloud protocol</small>
        </div>
      </div>

      <svg className="graph-svg" viewBox="0 0 100 100" role="img" aria-label="Connected patient memory nodes">
        {links.map(([source, target], index) => {
          const sourceNode = graphNodes.find((node) => node.id === source);
          const targetNode = graphNodes.find((node) => node.id === target);
          if (!sourceNode || !targetNode) return null;
          return (
            <line
              key={`${source}-${target}`}
              className={`graph-link ${source === selectedNode.id || target === selectedNode.id ? "active" : ""}`}
              x1={sourceNode.x}
              y1={sourceNode.y}
              x2={targetNode.x}
              y2={targetNode.y}
              style={{ animationDelay: `${index * 180}ms` }}
            />
          );
        })}
        {graphNodes.map((node, index) => (
          <g
            key={node.id}
            className={`graph-node ${selectedNode.id === node.id ? "selected" : ""}`}
            style={{ animationDelay: `${index * 120}ms` }}
            role="button"
            tabIndex={0}
            aria-label={`Inspect ${node.label}`}
            onClick={() => setSelectedNodeId(node.id)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                setSelectedNodeId(node.id);
              }
            }}
          >
            <circle cx={node.x} cy={node.y} r={node.r + 3} fill={colorByTone[node.tone]} opacity="0.11" />
            <circle cx={node.x} cy={node.y} r={node.r} fill={colorByTone[node.tone]} />
            <circle cx={node.x} cy={node.y} r={node.r + 1.4} fill="none" stroke={colorByTone[node.tone]} opacity="0.55" />
            <text x={node.x} y={node.y + node.r + 5} textAnchor="middle" className="graph-node-label">
              {node.label}
            </text>
          </g>
        ))}
      </svg>

      <aside key={selectedNode.id} className="map-inspector">
        <span>{selectedNode.scope} / {selectedNode.type}</span>
        <strong>{selectedNode.label}</strong>
        <p>{selectedNode.summary}</p>
      </aside>

      <div className="map-metrics">
        <div>
          <strong>{patient?.events.length ?? 0}</strong>
          <span>events</span>
        </div>
        <div>
          <strong>{conflicts.length}</strong>
          <span>flags</span>
        </div>
        <div>
          <strong>{memory?.cloud_configured ? "on" : "off"}</strong>
          <span>cloud</span>
        </div>
      </div>
    </section>
  );
}

function TopBar({ health, onRefresh, refreshing }: { health: HealthResponse | null; onRefresh: () => void; refreshing: boolean }) {
  return (
    <header className="topbar">
      <div>
        <p className="section-label">Live workspace</p>
        <h1>Case operations</h1>
      </div>
      <div className="topbar-actions">
        <StatusPill label={`API ${health?.status ?? "checking"}`} tone={health?.status === "ok" ? "good" : "warn"} />
        <StatusPill label={`Guardrails ${health?.guardrails ?? "unknown"}`} tone="good" />
        <button type="button" className="icon-button" onClick={onRefresh} aria-label="Refresh dashboard">
          <RefreshCw size={18} className={refreshing ? "spin" : ""} />
        </button>
      </div>
    </header>
  );
}

function CommandOverview({
  patient,
  memory,
  conflicts,
  running,
  onRun,
  journeyStarted,
  ready,
  loading,
  error,
}: {
  patient: Patient | null;
  memory: MemoryStatus | null;
  conflicts: ConflictFlag[];
  running: boolean;
  onRun: () => void;
  journeyStarted: boolean;
  ready: boolean;
  loading: boolean;
  error: string | null;
}) {
  const buttonLabel = loading ? "Loading case" : error ? "Backend offline" : journeyStarted ? "Run again" : "Start journey";

  return (
    <section className={journeyStarted ? "landing-command compact" : "landing-command"}>
      <div className="landing-copy">
        <p className="section-label">MedGraph</p>
        <h2>Know where to start.</h2>
        <p>
          <strong>{patient?.display_name ?? "Selected case"}</strong> / recall, review, check, save, reset.
        </p>
        <div className="landing-actions">
          <button type="button" className="primary-button" onClick={onRun} disabled={running || loading || !ready}>
            {running || loading ? <Loader2 size={18} className="spin" /> : <PlayCircle size={18} />}
            {running ? "Running" : buttonLabel}
          </button>
          {journeyStarted ? <StatusPill label={running ? "Running" : "Journey open"} tone={running ? "warn" : "good"} /> : null}
        </div>
      </div>

      {journeyStarted ? (
        <div className="command-board">
          <MiniKnowledgeGraph patient={patient} memory={memory} conflicts={conflicts} />
        </div>
      ) : null}
    </section>
  );
}

function PatientSelector({
  patients,
  selectedId,
  onSelect,
}: {
  patients: Patient[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="panel patient-list">
      <SectionHeader eyebrow="Cases" title="Patient queue" />
      {patients.length === 0 ? (
        <EmptyPanel title="No case loaded" detail="Start the backend, then refresh the dashboard." />
      ) : (
        <div className="patient-buttons">
          {patients.map((patient) => (
            <button
              type="button"
              key={patient.id}
              className={selectedId === patient.id ? "patient-button selected" : "patient-button"}
              onClick={() => onSelect(patient.id)}
            >
              <span>
                <strong>{patient.display_name}</strong>
                <small>
                  {patient.age} years / {patient.sex} / {patient.mrn}
                </small>
              </span>
              <ChevronRight size={17} />
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function PatientSnapshot({ patient }: { patient: Patient | null }) {
  if (!patient) return <EmptyPanel title="Patient snapshot unavailable" detail="The patient record has not loaded yet." />;

  return (
    <section className="panel patient-snapshot">
      <div className="patient-hero">
        <div>
          <p className="section-label">Selected case</p>
          <h2>{patient.display_name}</h2>
          <p>{patient.age} years / {patient.sex} / {patient.mrn}</p>
        </div>
        <StatusPill label={patient.synthetic ? "Synthetic" : "Live"} tone="good" />
      </div>

      <div className="snapshot-columns">
        <InfoList title="Conditions" items={patient.conditions.map((item) => [item.name, item.status])} />
        <InfoList title="Active meds" items={patient.current_medications.map((item) => [item.name, item.dose])} />
        <InfoList title="Allergies" items={patient.allergies.map((item) => [item.substance, item.severity])} />
      </div>
    </section>
  );
}

function InfoList({ title, items }: { title: string; items: Array<[string, string]> }) {
  return (
    <div className="info-list">
      <h3>{title}</h3>
      <ul>
        {items.map(([label, value]) => (
          <li key={`${title}-${label}-${value}`}>
            <span>{label}</span>
            <small>{value}</small>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CollapsibleGuardrails({ conflicts }: { conflicts: ConflictFlag[] }) {
  const sorted = useMemo(() => [...conflicts].sort((a, b) => severityRank(b.severity) - severityRank(a.severity)), [conflicts]);

  return (
    <details className="guardrail-drawer">
      <summary title="Open to review context flags surfaced by the safety checks.">
        <span>
          <ShieldCheck size={16} />
          Guardrail flags
        </span>
        <StatusPill label={`${sorted.length} flag(s)`} tone={sorted.length > 0 ? "warn" : "good"} />
      </summary>
      <div className="guardrail-list">
        {sorted.length === 0 ? <p className="muted">No active flags.</p> : null}
        {sorted.map((conflict) => (
          <article key={conflict.id} className={`risk-card ${conflict.severity}`}>
            <div className="risk-card-header">
              <StatusPill label={conflict.severity} tone={conflict.severity === "high" || conflict.severity === "critical" ? "danger" : "warn"} />
              <StatusPill label={conflict.source.replaceAll("_", " ")} tone="neutral" />
            </div>
            <h3>{conflict.title}</h3>
            <dl className="evidence-list">
              <div>
                <dt>Evidence</dt>
                <dd>{conflict.evidence}</dd>
              </div>
              <div>
                <dt>Check next</dt>
                <dd>{conflict.recommendation}</dd>
              </div>
              <div>
                <dt>Review</dt>
                <dd>{conflict.requires_clinician_review ? "Clinician review required." : "Informational context."}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </details>
  );
}

function JourneyTimeline({ events }: { events: ClinicalEvent[] }) {
  return (
    <section className="workspace-band page-section" id="hospital-journey">
      <SectionHeader eyebrow="Timeline" title="Hospital journey" />
      <div className="timeline">
        {events.map((event) => (
          <article key={event.id} className="timeline-item">
            <div className="timeline-stamp">
              <strong>{event.department}</strong>
              <span>{formatDate(event.timestamp)}</span>
            </div>
            <div className="timeline-body">
              <h3>{event.title}</h3>
              <p>{event.notes}</p>
              <div className="tag-row">
                <span>{event.clinician}</span>
                {event.tests_ordered.slice(0, 4).map((test) => <span key={test}>{test}</span>)}
              </div>
            </div>
          </article>
        ))}
      </div>
      <ContinueButton target="proposed-action" label="Continue to action check" />
    </section>
  );
}

function BriefingPanel({
  briefing,
  discharge,
}: {
  briefing: BriefingResponse | null;
  discharge: DischargeSummaryResponse | null;
}) {
  return (
    <section className="panel briefing-panel">
      <SectionHeader eyebrow="Recall" title="Clinician briefing" />
      <div className="briefing-stack">
        <article className="briefing-reading-card">
          <h3>Shift briefing</h3>
          <ReadableText text={briefing?.briefing ?? "Loading patient briefing."} />
        </article>
        <DischargeDraftEditor summary={discharge?.summary ?? null} />
      </div>
      <p className="disclaimer">{briefing?.disclaimer ?? discharge?.disclaimer}</p>
    </section>
  );
}

function ClinicalReview({
  briefing,
  discharge,
  conflicts,
}: {
  briefing: BriefingResponse | null;
  discharge: DischargeSummaryResponse | null;
  conflicts: ConflictFlag[];
}) {
  return (
    <section className="workspace-band page-section clinical-review" id="clinical-review">
      <CollapsibleGuardrails conflicts={conflicts} />
      <SectionHeader eyebrow="Recall and review" title="Briefing and flags" />
      <BriefingPanel briefing={briefing} discharge={discharge} />
      <ContinueButton target="hospital-journey" label="Continue to hospital journey" />
    </section>
  );
}

function ActionChecker({
  patientId,
  result,
  onResult,
  onAfterWrite,
  onOperation,
}: {
  patientId: string | null;
  result: CheckActionResponse | null;
  onResult: (result: CheckActionResponse) => void;
  onAfterWrite: () => void | Promise<void>;
  onOperation: (id: OperationId, status: OperationStatus, detail: string) => void;
}) {
  const [form, setForm] = useState<ProposedActionPayload>(defaultAction);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!patientId) return;
    setBusy(true);
    setError(null);
    try {
      onOperation("remember", "running", "Checking action.");
      const response = await checkAction(patientId, form);
      onResult(response);
      onOperation("remember", "done", `${response.conflicts.length} flag(s) returned.`);
      await onAfterWrite();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not check action";
      onOperation("remember", "error", message);
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="workspace-band page-section" id="proposed-action">
      <SectionHeader eyebrow="Safety" title="Proposed action check" />
      <div className="action-layout">
        <form onSubmit={handleSubmit} className="panel stacked-form">
          <label>
            <span>Action type</span>
            <select value={form.action_type} onChange={(event) => setForm({ ...form, action_type: event.target.value as ProposedActionPayload["action_type"] })}>
              <option value="medication">Medication</option>
              <option value="test">Test</option>
              <option value="diagnosis">Diagnosis</option>
              <option value="note">Note</option>
              <option value="handoff">Handoff</option>
            </select>
          </label>
          <label>
            <span>Name</span>
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
          </label>
          <label>
            <span>Requested by</span>
            <input value={form.requested_by} onChange={(event) => setForm({ ...form, requested_by: event.target.value })} />
          </label>
          <label>
            <span>Notes</span>
            <textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
          </label>
          <button type="submit" className="primary-button" disabled={busy || !patientId}>
            {busy ? <Loader2 size={16} className="spin" /> : <CheckCircle2 size={16} />}
            Check action
          </button>
          {error ? <p className="error-text">{error}</p> : null}
        </form>

        <aside className="panel decision-panel">
          <div>
            <p className="section-label">Decision support</p>
            <h3>{result ? `${result.conflicts.length} context flag(s)` : "No check run"}</h3>
          </div>
          {result ? (
            <>
              <StatusPill label={result.guardrail.severity} tone={result.guardrail.allowed ? "good" : "danger"} />
              <p>{result.guardrail.required_disclaimer}</p>
            </>
          ) : (
            <p className="muted">Run the action check to populate this panel.</p>
          )}
        </aside>
      </div>
      <ContinueButton target="protocol-memory" label="Continue to protocol memory" />
    </section>
  );
}

function ProtocolMemoryForm({
  memory,
  onAfterWrite,
  onOperation,
}: {
  memory: MemoryStatus | null;
  onAfterWrite: () => void | Promise<void>;
  onOperation: (id: OperationId, status: OperationStatus, detail: string) => void;
}) {
  const [protocolId, setProtocolId] = useState(defaultProtocol.id);
  const [content, setContent] = useState(defaultProtocol.content);
  const [source, setSource] = useState(defaultProtocol.source);
  const [busy, setBusy] = useState(false);
  const [improving, setImproving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [result, setResult] = useState<ProtocolMemoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onOperation("remember", "running", "Saving protocol.");
      const response = await rememberProtocol(protocolId, { content, source });
      setResult(response);
      onOperation("remember", "done", "Protocol saved.");
      await onAfterWrite();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not write protocol memory";
      onOperation("remember", "error", message);
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  async function handleImprove() {
    setImproving(true);
    setError(null);
    try {
      onOperation("improve", "running", "Improving protocol.");
      await improveProtocolMemory(protocolId);
      onOperation("improve", "done", "Protocol improved.");
      await onAfterWrite();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not improve protocol memory";
      onOperation("improve", "error", message);
      setError(message);
    } finally {
      setImproving(false);
    }
  }

  async function handleForget() {
    setDeleting(true);
    setError(null);
    try {
      onOperation("forget", "running", "Resetting protocol.");
      const response = await forgetProtocolMemory(protocolId);
      setResult(null);
      onOperation("forget", "done", `${response.deleted_records} protocol record(s) reset.`);
      await onAfterWrite();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not reset protocol memory";
      onOperation("forget", "error", message);
      setError(message);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <section className="workspace-band page-section" id="protocol-memory">
      <SectionHeader eyebrow="Protocol memory" title="Cloud protocol control" />
      <div className="protocol-layout">
        <form onSubmit={handleSubmit} className="panel protocol-form">
          <div className="form-grid">
            <label>
              <span>Protocol ID</span>
              <input value={protocolId} onChange={(event) => setProtocolId(event.target.value)} />
            </label>
            <label>
              <span>Source</span>
              <input value={source} onChange={(event) => setSource(event.target.value)} />
            </label>
            <label className="wide">
              <span>Protocol memory</span>
              <textarea value={content} onChange={(event) => setContent(event.target.value)} />
            </label>
          </div>
          <div className="button-row">
            <button type="submit" className="primary-button" disabled={busy}>
              {busy ? <Loader2 size={16} className="spin" /> : <Cloud size={16} />}
              Save
            </button>
            <button type="button" className="secondary-button" onClick={handleImprove} disabled={improving}>
              {improving ? <Loader2 size={16} className="spin" /> : <Brain size={16} />}
              Improve
            </button>
            <button type="button" className="danger-button" onClick={handleForget} disabled={deleting}>
              {deleting ? <Loader2 size={16} className="spin" /> : <Trash2 size={16} />}
              Reset protocol
            </button>
          </div>
          {error ? <p className="error-text">{error}</p> : null}
          {result ? (
            <div className="result-box">
              <StatusPill label="saved" tone="good" />
              <strong>{result.record.id}</strong>
            </div>
          ) : null}
        </form>
        <MemoryTransparency memory={memory} />
      </div>
      <ContinueButton target="audit-log" label="Continue to audit log" />
    </section>
  );
}

function MemoryTransparency({ memory }: { memory: MemoryStatus | null }) {
  return (
    <aside className="panel memory-transparency" aria-label="Memory routing transparency">
      <SectionHeader eyebrow="Memory routing" title="What goes where" />
      <div className="routing-lanes">
        <article>
          <DatabaseIcon />
          <span>Patient context</span>
          <strong>Local only</strong>
          <p>{memory?.local_records ?? 0} patient record(s). Timeline, meds, labs, and identifiers stay in local memory.</p>
        </article>
        <article>
          <Cloud size={20} />
          <span>Protocol guidance</span>
          <strong>Cloud protocol</strong>
          <p>{memory?.cloud_records ?? 0} protocol record(s). Non-identifying review guidance can be reused.</p>
        </article>
        <article>
          <ShieldCheck size={20} />
          <span>Excluded</span>
          <strong>Not stored</strong>
          <p>UI state, draft edits, and clinician decisions are not sent to cloud protocol memory.</p>
        </article>
      </div>
    </aside>
  );
}

function DatabaseIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" width="20" height="20" fill="none">
      <path d="M5 7c0-1.7 3.1-3 7-3s7 1.3 7 3-3.1 3-7 3-7-1.3-7-3Z" stroke="currentColor" strokeWidth="1.8" />
      <path d="M5 7v5c0 1.7 3.1 3 7 3s7-1.3 7-3V7M5 12v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function AuditPanel({ audit }: { audit: GuardrailAuditEntry[] }) {
  return (
    <section className="workspace-band page-section" id="audit-log">
      <SectionHeader eyebrow="Audit" title="Guardrail log" />
      <div className="audit-table">
        <div className="audit-head">
          <span>Time</span>
          <span>Action</span>
          <span>Severity</span>
          <span>Allowed</span>
        </div>
        {audit.slice(0, 8).map((entry) => (
          <article key={entry.id} className="audit-row">
            <span>{formatDate(entry.timestamp)}</span>
            <strong>{entry.action}</strong>
            <span>{entry.severity}</span>
            <StatusPill label={entry.allowed ? "yes" : "review"} tone={entry.allowed ? "good" : "warn"} />
          </article>
        ))}
        {audit.length === 0 ? <p className="muted">No guardrail events yet.</p> : null}
      </div>
    </section>
  );
}

function LoadingPanel({ title }: { title: string }) {
  return (
    <section className="panel loading-panel">
      <Loader2 className="spin" />
      <span>{title}</span>
    </section>
  );
}

function EmptyPanel({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="empty-panel">
      <AlertTriangle size={17} />
      <div>
        <strong>{title}</strong>
        <p>{detail}</p>
      </div>
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [memory, setMemory] = useState<MemoryStatus | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [briefing, setBriefing] = useState<BriefingResponse | null>(null);
  const [discharge, setDischarge] = useState<DischargeSummaryResponse | null>(null);
  const [audit, setAudit] = useState<GuardrailAuditEntry[]>([]);
  const [checkResult, setCheckResult] = useState<CheckActionResponse | null>(null);
  const [apiUsage, setApiUsage] = useState<ApiUsageItem[]>(createApiUsageItems);
  const [demoSteps, setDemoSteps] = useState<DemoStep[]>(createDemoSteps);
  const [demoRunning, setDemoRunning] = useState(false);
  const [journeyStarted, setJourneyStarted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeConflicts = checkResult?.conflicts ?? briefing?.conflicts ?? [];
  const hasCaseContext = Boolean(selectedId && patient && patients.length > 0);
  const canStartJourney = !loading && !refreshing && !error && hasCaseContext;

  const updateApiUsage = useCallback((id: OperationId, status: OperationStatus, detail: string) => {
    setApiUsage((items) => items.map((item) => (item.id === id ? { ...item, status, detail } : item)));
  }, []);

  const updateDemoStep = useCallback((id: DemoStepId, status: OperationStatus) => {
    setDemoSteps((steps) => steps.map((step) => (step.id === id ? { ...step, status } : step)));
  }, []);

  const markRunningAsError = useCallback((message: string) => {
    setApiUsage((items) => items.map((item) => (item.status === "running" ? { ...item, status: "error", detail: message } : item)));
    setDemoSteps((steps) => steps.map((step) => (step.status === "running" ? { ...step, status: "error" } : step)));
  }, []);

  const refreshStatus = useCallback(async () => {
    const [healthResponse, memoryResponse, auditResponse] = await Promise.all([
      getHealth(),
      getMemoryStatus(),
      getGuardrailAudit(),
    ]);
    setHealth(healthResponse);
    setMemory(memoryResponse);
    setAudit(auditResponse);
  }, []);

  const loadPatientContext = useCallback(async (patientId: string) => {
    updateApiUsage("recall", "running", "Loading case.");
    try {
      const [patientResponse, briefingResponse, dischargeResponse] = await Promise.all([
        getPatient(patientId),
        getBriefing(patientId),
        getDischargeSummary(patientId),
      ]);
      setPatient(patientResponse);
      setBriefing(briefingResponse);
      setDischarge(dischargeResponse);
      updateApiUsage("recall", "done", "Case loaded.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not load patient context";
      updateApiUsage("recall", "error", message);
      throw err;
    }
  }, [updateApiUsage]);

  const refreshAll = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const [patientsResponse] = await Promise.all([getPatients(), refreshStatus()]);
      setPatients(patientsResponse);
      const nextPatientId = selectedId ?? patientsResponse[0]?.id ?? null;
      setSelectedId(nextPatientId);
      if (nextPatientId) await loadPatientContext(nextPatientId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load MedGraph");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [loadPatientContext, refreshStatus, selectedId]);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  useEffect(() => {
    if (!selectedId) return;
    setPatient(null);
    setBriefing(null);
    setDischarge(null);
    void loadPatientContext(selectedId).catch((err) => {
      setError(err instanceof Error ? err.message : "Could not load patient");
    });
  }, [loadPatientContext, selectedId]);

  useEffect(() => {
    if (!journeyStarted || loading) return;
    window.setTimeout(() => scrollToSection("patient-detail"), 80);
  }, [journeyStarted, loading]);

  async function handleRefresh() {
    await refreshAll();
  }

  async function handleAfterWrite() {
    await refreshStatus();
  }

  async function handleRunDemo() {
    if (!selectedId) return;

    const protocolId = `${defaultProtocol.id}-workflow`;
    setDemoRunning(true);
    setError(null);
    setApiUsage(createApiUsageItems());
    setDemoSteps(createDemoSteps());
    setCheckResult(null);

    try {
      updateDemoStep("recall", "running");
      updateApiUsage("recall", "running", "Loading case.");
      const [patientResponse, briefingResponse, dischargeResponse] = await Promise.all([
        getPatient(selectedId),
        getBriefing(selectedId),
        getDischargeSummary(selectedId),
      ]);
      setPatient(patientResponse);
      setBriefing(briefingResponse);
      setDischarge(dischargeResponse);
      updateApiUsage("recall", "done", "Case loaded.");
      updateDemoStep("recall", "done");

      updateDemoStep("safety", "running");
      updateApiUsage("remember", "running", "Checking Heparin.");
      const actionResponse = await checkAction(selectedId, defaultAction);
      setCheckResult(actionResponse);
      updateApiUsage("remember", "done", `${actionResponse.conflicts.length} flag(s) returned.`);
      updateDemoStep("safety", "done");

      updateDemoStep("cloud", "running");
      updateApiUsage("remember", "running", "Saving protocol.");
      await rememberProtocol(protocolId, {
        content: `${defaultProtocol.content} Workflow run timestamp: ${new Date().toISOString()}.`,
        source: "run_workflow",
      });
      updateApiUsage("remember", "done", "Protocol saved.");
      updateDemoStep("cloud", "done");

      updateDemoStep("improve", "running");
      updateApiUsage("improve", "running", "Improving memory.");
      await Promise.all([improvePatientMemory(selectedId), improveProtocolMemory(protocolId)]);
      updateApiUsage("improve", "done", "Memory improved.");
      updateDemoStep("improve", "done");

      updateDemoStep("forget", "running");
      updateApiUsage("forget", "running", "Resetting demo.");
      const [patientForgetResponse, protocolForgetResponse] = await Promise.all([
        forgetPatientMemory(selectedId),
        forgetProtocolMemory(protocolId),
      ]);
      updateApiUsage("forget", "done", `${patientForgetResponse.deleted_records + protocolForgetResponse.deleted_records} record(s) reset.`);
      updateDemoStep("forget", "done");

      await refreshStatus();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Run workflow failed";
      markRunningAsError(message);
      setError(message);
    } finally {
      setDemoRunning(false);
    }
  }

  async function handleStartJourney() {
    if (demoRunning || loading || error) return;
    if (!hasCaseContext) {
      await refreshAll();
      if (!selectedId) return;
    }
    setJourneyStarted(true);
  }

  return (
    <div className={journeyStarted ? "app-shell journey-open" : "landing-shell"}>
      {journeyStarted ? <JourneyRail steps={demoSteps} /> : null}
      <main className="main-shell">
        {journeyStarted ? <TopBar health={health} onRefresh={handleRefresh} refreshing={refreshing} /> : null}

        <CommandOverview
          patient={patient}
          memory={memory}
          conflicts={activeConflicts}
          running={demoRunning}
          onRun={handleStartJourney}
          journeyStarted={journeyStarted}
          ready={canStartJourney}
          loading={loading || refreshing}
          error={error}
        />

        {error ? (
          <div className="error-banner">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        ) : null}

        {journeyStarted && loading ? (
          <LoadingPanel title="Loading MedGraph" />
        ) : null}

        {journeyStarted && !loading && hasCaseContext ? (
          <>
            <section className="workspace-band page-section" id="patient-detail">
              <SectionHeader eyebrow="Cases" title="Patient detail" />
              <div className="case-layout">
                <PatientSelector patients={patients} selectedId={selectedId} onSelect={setSelectedId} />
                <PatientSnapshot patient={patient} />
              </div>
              <ContinueButton target="clinical-review" label="Continue to briefing" />
            </section>

            <ClinicalReview briefing={briefing} discharge={discharge} conflicts={activeConflicts} />

            <JourneyTimeline events={patient?.events ?? []} />

            <ActionChecker
              patientId={selectedId}
              result={checkResult}
              onResult={setCheckResult}
              onAfterWrite={handleAfterWrite}
              onOperation={updateApiUsage}
            />

            <ProtocolMemoryForm memory={memory} onAfterWrite={handleAfterWrite} onOperation={updateApiUsage} />

            <AuditPanel audit={audit} />
          </>
        ) : null}
      </main>
    </div>
  );
}
