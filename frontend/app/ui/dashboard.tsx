"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  asText,
  CompareResponse,
  DEFAULT_COMPARE_IDS,
  fmt,
  gravityName,
  gravityValue,
  HABITAT_SHORT,
  Habitat,
  INCIDENT_NOTES,
  Investigation,
  RankItem,
  rangeText,
  reportScenario,
  RepositoryScope,
  Run,
  RunSummary,
  RunValidation,
  Scenario,
  scenarioFromHabitat,
  SimResponse,
  Synthesis,
  TABS,
  TabId,
} from "./model";
import { AiResearchAssistant } from "./ai-research-assistant";
import { FireSuppressionDigitalTwin } from "./fire-suppression-digital-twin";
import { MlFireResearchLab } from "./ml-fire-research-lab";
import { ScientificDecisionSupport } from "./scientific-decision-support";
import { VirtualSpacecraftMonitoring } from "./virtual-spacecraft-monitoring";
import {
  DustDiscriminationPanel,
  EvidenceBarChart,
  O2PressureEnvelopeChart,
  PartialGravityBoundingChart,
  SamerTelemetryVisual,
} from "./charts";

type ApiError = { detail?: string | { msg?: string }[] };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/backend/${path}`, {
    ...init,
    cache: "no-store",
    headers: { ...(init?.headers ?? {}), ...(init?.body ? { "content-type": "application/json" } : {}) },
  });
  if (!response.ok) {
    const info = await response.json().catch(() => ({})) as ApiError;
    const detail = Array.isArray(info.detail) ? info.detail.map((item) => item.msg ?? "Invalid input").join("; ") : info.detail;
    throw new Error(typeof detail === "string" ? detail : `Backend request failed (${response.status}).`);
  }
  if (!response.headers.get("content-type")?.includes("application/json")) {
    throw new Error("The backend proxy returned an unexpected response format.");
  }
  return await response.json() as T;
}

const MATRIX_ROWS: [string, string][] = [
  ["objective", "Objective"],
  ["hardware_rack", "Hardware rack"],
  ["fuel_phase", "Fuel phase"],
  ["fuel_or_sample", "Fuel / sample"],
  ["o2_range_pct", "O₂ envelope"],
  ["pressure_range_psi", "Pressure envelope"],
  ["airflow_range_cm_s", "Airflow envelope"],
  ["gravity_regimes", "Gravity regimes"],
  ["sensors_variables", "Sensors"],
  ["predictive_variables", "Predictive variables"],
  ["local_data_status", "Evidence availability"],
  ["doi", "DOI"],
];

function ErrorBox({ message }: { message: string }) {
  return <div className="error" role="alert"><b>Request could not be completed.</b><br />{message}</div>;
}

function RepositoryScopePanel({ scope }: { scope: RepositoryScope | null }) {
  if (!scope) return null;
  return (
    <details className="scope-panel">
      <summary>
        <span className="scope-badge">PSI REPOSITORY COVERAGE &amp; SCOPE</span>
        <b>{scope.total_investigations} investigations</b>
        <span>{scope.aggregate_telemetry_label} aggregate</span>
        <span>{scope.deeply_indexed_count} deeply indexed + {scope.associated_count} associated</span>
        <span className="scope-open">Scope matrix →</span>
      </summary>
      <div className="scope-body">
        <p className="scope-summary">{scope.summary}</p>
        <p className="small-caution">{scope.id_reconciliation}</p>
        <div className="scope-tiers">
          <div>
            <h3>Tier 1 · {scope.deeply_indexed_count} deeply indexed</h3>
            <ul className="scope-list">
              {scope.tier1.map((item) => (
                <li key={item.psi_id}><b>{item.psi_id}</b> <span>{item.short_name}</span><p>{item.focus}</p></li>
              ))}
            </ul>
          </div>
          <div>
            <h3>Tier 2 · {scope.associated_count} associated</h3>
            <ul className="scope-list">
              {scope.tier2.map((item) => (
                <li key={item.key}><b>{item.key}</b> <span>{item.name}</span><p>{item.focus}</p></li>
              ))}
            </ul>
          </div>
        </div>
        <div className="scope-upcoming">
          <h3>Upcoming partial-gravity missions</h3>
          {scope.upcoming_missions.map((mission) => (
            <div key={mission.key}><b>{mission.key}</b> <span>{mission.name}</span><p>{mission.bounding}</p></div>
          ))}
        </div>
        <p className="small-caution">{scope.bounding_statement}</p>
        <ul className="scope-limits">{scope.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
      </div>
    </details>
  );
}

function Kpi({ label, value, sub, tone }: { label: string; value: string; sub: string; tone?: "good" | "warn" | "hazard" }) {
  return <div className={`kpi ${tone ?? ""}`}><span>{label}</span><strong>{value}</strong><small>{sub}</small></div>;
}

function NumberField({
  label, value, min, max, step, hint, onChange,
}: {
  label: string; value: number; min: number; max: number; step: number; hint: string; onChange: (value: number) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="number" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
      <small>{hint}</small>
    </label>
  );
}

function StatementList({ items, empty }: { items: string[]; empty: string }) {
  if (!items.length) return <p className="muted">{empty}</p>;
  return <ul>{items.map((item, index) => <li key={index}>{item}</li>)}</ul>;
}

function MatrixCell({ field, study }: { field: string; study: Record<string, unknown> }) {
  if (field === "doi") {
    return <a href={String(study.doi_url ?? "#")} target="_blank" rel="noreferrer">{String(study.doi ?? "—")}</a>;
  }
  if (field === "o2_range_pct") return <>{rangeText(study[field], "%")}</>;
  if (field === "pressure_range_psi") return <>{rangeText(study[field], " psi")}</>;
  if (field === "airflow_range_cm_s") {
    const text = rangeText(study[field], " cm/s");
    return <>{text === "—" ? (study.airflow_max_cm_s ? `${study.airflow_max_cm_s} cm/s max capability` : "—") : text}</>;
  }
  if (field === "predictive_variables" || field === "gravity_regimes") {
    const value = study[field];
    return <>{Array.isArray(value) ? value.join(" · ") : "—"}</>;
  }
  return <>{asText(study[field])}</>;
}

function ArchivedPatternTables({ summary }: { summary: RunSummary }) {
  const lags = summary.lag_correlations ?? [];
  const models = summary.candidate_models ?? [];
  return (
    <article className="panel">
      <div className="panel-head">
        <div><p className="eyebrow">ARCHIVED PERIODICITY OUTPUTS</p><h3>Lag correlations and candidate fits</h3></div>
        <span className="pill">{lags.length} lag rows · {models.length} models</span>
      </div>
      <p className="muted">Loaded from the validated 2026-11-14 archived analysis. Descriptive archive outputs, not recomputed in this deployment.</p>
      <details>
        <summary>Inspect {lags.length} lag-correlation rows</summary>
        <div className="table-scroll-wrapper">
          <table>
            <thead><tr><th>Lag (cycles)</th><th>Valid cycle pairs</th><th>Autocorrelation</th></tr></thead>
            <tbody>{lags.map((row, index) => <tr key={`${row.Lag}-${index}`}><td>{row.Lag}</td><td>{row.ValidCyclePairs}</td><td>{row.Autocorrelation}</td></tr>)}</tbody>
          </table>
        </div>
      </details>
      <details>
        <summary>Inspect {models.length} candidate model rows</summary>
        <div className="table-scroll-wrapper">
          <table>
            <thead><tr><th>Model</th><th>Period</th><th>Mismatch</th><th>Phase</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>F1</th><th>Baseline</th><th>Window</th><th>Interpretation</th></tr></thead>
            <tbody>{models.map((row, index) => (
              <tr key={`${row.ModelType}-${row.Period}-${index}`}>
                <td>{row.ModelType}</td><td>{row.Period}</td><td>{row.MismatchWidth}</td><td>{row.PhaseOffset}</td>
                <td>{row.Accuracy}</td><td>{row.Precision}</td><td>{row.Recall}</td><td>{row.F1}</td>
                <td>{row.BaselineAccuracy}</td><td>{row.EvaluationWindow}</td><td>{row.Interpretation}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </details>
    </article>
  );
}

type Theme = "light" | "dark";

type TeamMember = {
  name: string;
  department: string;
  designation: string;
  github?: string;
  linkedin?: string;
  responsibilities: string[];
  projectLead?: boolean;
};

const TEAM_MEMBERS: TeamMember[] = [
  {
    name: "Chandan Kumar Sah",
    department: "CSE (Artificial Intelligence and Machine Learning)",
    designation: "Project Lead & Backend Engineer",
    github: "https://github.com/Chandan24-cell",
    linkedin: "https://www.linkedin.com/in/chandan-kumar-sah-40156a360/",
    projectLead: true,
    responsibilities: [
      "Overall technical architecture and project direction.",
      "Backend development and REST API implementation.",
      "SI-powered scientific intelligence workflow integration.",
      "System architecture, API contracts and technical coordination.",
      "Integration of frontend, backend and analytical components.",
    ],
  },
  {
    name: "Saurav Shah Teli",
    department: "Computer Science and Engineering",
    designation: "Frontend & Dashboard Visualization",
    github: "https://github.com/Saurav924-sks",
    linkedin: "https://www.linkedin.com/in/saurav-shah-aa1a64357/",
    responsibilities: [
      "Development of the Next.js dashboard interface.",
      "Implementation of reusable frontend components.",
      "Scientific charts, combustion data visualization and interactive analytics.",
      "Responsive dashboard layout and user experience.",
      "Frontend integration with backend APIs.",
    ],
  },
  {
    name: "Mantu Kumar Chaurasiya",
    department: "Artificial Intelligence and Data Science",
    designation: "Data Engineering & Dataset Curation",
    github: "https://github.com/mantuchaurasiya092-source",
    linkedin: "https://www.linkedin.com/in/mantu-kumar-chaurasiya-117594438/",
    responsibilities: [
      "Collection and organization of NASA microgravity combustion datasets.",
      "Dataset preprocessing, normalization and transformation.",
      "Scientific metadata management and data lineage.",
      "Feature preparation and analytics-ready dataset generation.",
      "Supporting the integration of data processing and intelligence pipelines.",
    ],
  },
  {
    name: "Bhola Sah",
    department: "Artificial Intelligence and Data Science",
    designation: "Quality Assurance & Testing",
    github: "https://github.com/bholasah",
    linkedin: "https://www.linkedin.com/in/bhola-sah-90585244b/",
    responsibilities: [
      "Functional testing of dashboard and backend components.",
      "API validation and automated test development.",
      "Verification of scientific data integrity.",
      "Validation of analytical outputs and edge cases.",
      "Regression testing and reproducibility checks.",
    ],
  },
  {
    name: "Digambar Updahaya",
    department: "Biomedical Engineering",
    designation: "Scientific Research & Documentation",
    responsibilities: [
      "Research into microgravity combustion phenomena and flame behavior.",
      "Reviewing relevant NASA experiments and scientific publications.",
      "Interpreting experimental findings in the context of spacecraft fire safety.",
      "Maintaining scientific references, methodologies and research documentation.",
      "Supporting scientific interpretation of analytical results.",
    ],
  },
  {
    name: "Aakash",
    department: "Computer Science and Engineering",
    designation: "Team Member",
    github: "https://github.com/aakashyadav-dev",
    linkedin: "https://www.linkedin.com/in/aakashyadavtech/",
    responsibilities: [
      "Application deployment and platform configuration.",
      "Frontend and backend environment integration.",
      "Build and release workflow automation.",
      "Deployment configuration and environment management.",
      "Application runtime monitoring, logging and service health checks.",
      "Supporting deployment reliability and platform maintenance.",
    ],
  },
];

function DeveloperIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" fill="none">
      <rect x="2.5" y="3" width="15" height="11" rx="1.5" />
      <path d="m6 7 2.2 2L6 11m4.5 0h3M7 17h6m-3-3v3" />
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 .9a11.1 11.1 0 0 0-3.51 21.63c.56.1.76-.24.76-.54v-2.1c-3.1.67-3.76-1.32-3.76-1.32-.5-1.28-1.23-1.62-1.23-1.62-1.01-.69.08-.68.08-.68 1.12.08 1.71 1.15 1.71 1.15 1 .1.15 2.3 2.87 1.62.1-.73.39-1.23.7-1.51-2.47-.28-5.06-1.23-5.06-5.5 0-1.22.44-2.22 1.15-3-.12-.29-.5-1.43.11-2.98 0 0 .94-.3 3.06 1.15a10.6 10.6 0 0 1 5.57 0c2.12-1.45 3.06-1.15 3.06-1.15.61 1.55.23 2.69.11 2.98.72.78 1.15 1.78 1.15 3 0 4.28-2.6 5.22-5.08 5.49.4.34.75 1 .75 2.02v3c0 .3.2.65.77.54A11.1 11.1 0 0 0 12 .9Z" />
    </svg>
  );
}

function LinkedInIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
      <path d="M5 9v10M5 5.5v.1M10 19v-6a4 4 0 0 1 8 0v6M10 10v9" />
      <circle cx="5" cy="5.5" r="1" />
    </svg>
  );
}

function DeveloperTeamModal({ onClose, returnFocus }: { onClose: () => void; returnFocus: HTMLButtonElement | null }) {
  const modalRef = useRef<HTMLElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = modalRef.current?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), a[href], [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable?.length) {
        event.preventDefault();
        closeButtonRef.current?.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || !modalRef.current?.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !modalRef.current?.contains(document.activeElement))) {
        event.preventDefault();
        first.focus();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      returnFocus?.focus();
    };
  }, [onClose, returnFocus]);

  return createPortal(
    <div
      className="developer-modal-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        ref={modalRef}
        className="developer-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="developer-modal-title"
        aria-describedby="developer-modal-subtitle"
      >
        <button
          ref={closeButtonRef}
          className="developer-modal-close"
          type="button"
          aria-label="Close team modal"
          onClick={onClose}
        >
          <svg aria-hidden="true" viewBox="0 0 20 20" fill="none">
            <path d="m5 5 10 10M15 5 5 15" />
          </svg>
        </button>
        <header className="developer-modal-header">
          <p className="developer-modal-eyebrow">MISSION ENGINEERING &amp; SCIENCE TEAM · NASA SPACE APPS 2026</p>
          <h2 id="developer-modal-title">DEVELOPER TEAM</h2>
          <p id="developer-modal-subtitle">Meet the interdisciplinary engineering and science team building intelligent fire-safety insights from microgravity combustion research.</p>
        </header>
        <div className="developer-team-grid">
          {TEAM_MEMBERS.map((member) => (
            <article key={member.name} className={`developer-team-card${member.projectLead ? " project-lead" : ""}`}>
              <h3>
                {member.name}
                {member.projectLead && <span className="project-lead-badge">PROJECT LEAD</span>}
              </h3>
              <p className="developer-team-department">{member.department}</p>
              <p className="developer-team-role">{member.designation}</p>
              <div className="developer-profile-links">
                {member.github && (
                  <a href={member.github} target="_blank" rel="noopener noreferrer">
                    <GitHubIcon /> GitHub
                  </a>
                )}
                {member.linkedin && (
                  <a href={member.linkedin} target="_blank" rel="noopener noreferrer">
                    <LinkedInIcon /> LinkedIn
                  </a>
                )}
              </div>
              <h4>Responsibilities</h4>
              <ul>{member.responsibilities.map((responsibility) => <li key={responsibility}>{responsibility}</li>)}</ul>
            </article>
          ))}
        </div>
      </section>
    </div>,
    document.body,
  );
}

export default function Dashboard() {
  const [theme, setTheme] = useState<Theme>("dark");
  const [isDeveloperModalOpen, setIsDeveloperModalOpen] = useState(false);
  const [catalogue, setCatalogue] = useState<Investigation[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [habitats, setHabitats] = useState<Habitat[]>([]);
  const [repositoryScope, setRepositoryScope] = useState<RepositoryScope | null>(null);
  const [health, setHealth] = useState("Checking private API…");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [activeTab, setActiveTab] = useState<TabId>("simulator");
  const developerButtonRef = useRef<HTMLButtonElement | null>(null);
  const closeDeveloperModal = useCallback(() => setIsDeveloperModalOpen(false), []);

  const [query, setQuery] = useState("");
  const [pillarFilter, setPillarFilter] = useState("All pillars");
  const [rackFilter, setRackFilter] = useState("All racks");
  const [sortBy, setSortBy] = useState("name");
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<Investigation | null>(null);

  const [scenario, setScenario] = useState<Scenario>({
    mission: "ISS USOS standard cabin", gravity: "Microgravity", gravity_g: 0,
    oxygen_pct: 21, pressure_psi: 14.7, airflow_cms: 10, material: "Pyrell", pillar: "Detection",
  });
  const [activeHabitat, setActiveHabitat] = useState("");
  const [sim, setSim] = useState<SimResponse | null>(null);
  const [ranked, setRanked] = useState<RankItem[]>([]);
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState("");
  const [rankLoading, setRankLoading] = useState(false);
  const [rankingError, setRankingError] = useState("");
  const [showAllRanked, setShowAllRanked] = useState(false);
  const simSequence = useRef(0);

  const [compareIds, setCompareIds] = useState<string[]>(DEFAULT_COMPARE_IDS);
  const [compare, setCompare] = useState<CompareResponse | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState("");

  const [selectedRun, setSelectedRun] = useState("");
  const [runSummary, setRunSummary] = useState<RunSummary | null>(null);
  const [runError, setRunError] = useState("");
  const [runValidation, setRunValidation] = useState<RunValidation | null>(null);
  const [validationError, setValidationError] = useState("");
  const [cycleNumber, setCycleNumber] = useState(0);
  const [cycleData, setCycleData] = useState<Record<string, unknown> | null>(null);
  const [cycleError, setCycleError] = useState("");
  const cycleController = useRef<AbortController | null>(null);
  const [downloadMessage, setDownloadMessage] = useState("");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    return () => { document.documentElement.dataset.theme = "dark"; };
  }, [theme]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    Promise.all([
      api<{ items: Investigation[] }>("investigations", { signal: controller.signal }),
      api<{ runs: Run[]; processing_status: string }>("samer/runs", { signal: controller.signal }),
      api<{ status: string; archive_validation: string; raw_source_replay: string }>("health", { signal: controller.signal }),
      api<{ items: Habitat[] }>("habitats", { signal: controller.signal }),
      api<RepositoryScope>("repository/scope", { signal: controller.signal }),
    ]).then(([catalog, runData, status, habitatData, scopeData]) => {
      if (!active) return;
      setCatalogue(catalog.items);
      setRuns(runData.runs);
      setHabitats(habitatData.items);
      setRepositoryScope(scopeData);
      setHealth(`${status.status} · ${status.archive_validation}`);
      setSelectedId(catalog.items[0]?.psi_id ?? "");
      setSelectedRun(runData.runs[0]?.run_id ?? "");
      const first = habitatData.items[0];
      if (first) {
        const next = scenarioFromHabitat(first);
        setScenario(next);
        setActiveHabitat(first.id);
        void runSimulation(next);
      }
    }).catch((error: Error) => {
      if (active) setLoadError(error.message);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; controller.abort(); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController();
    setDetail(null);
    api<Investigation>(`investigations/${encodeURIComponent(selectedId)}`, { signal: controller.signal })
      .then(setDetail)
      .catch((error: Error) => { if (error.name !== "AbortError") setLoadError(error.message); });
    return () => controller.abort();
  }, [selectedId]);

  useEffect(() => {
    if (!selectedRun) return;
    cycleController.current?.abort();
    const controller = new AbortController();
    setRunSummary(null);
    setCycleData(null);
    setRunValidation(null);
    setRunError("");
    setCycleError("");
    setValidationError("");
    api<RunSummary>(`samer/runs/${selectedRun}/summary`, { signal: controller.signal }).then((summary) => {
      setRunSummary(summary);
      setCycleNumber(Number(summary.phase_summary?.FirstCycle ?? 0));
    }).catch((error: Error) => { if (error.name !== "AbortError") setRunError(error.message); });
    api<RunValidation>(`samer/runs/${selectedRun}/validation`, { signal: controller.signal })
      .then(setRunValidation)
      .catch((error: Error) => { if (error.name !== "AbortError") setValidationError(error.message); });
    return () => { controller.abort(); cycleController.current?.abort(); };
  }, [selectedRun]);

  useEffect(() => {
    if (compareIds.length < 2 || compareIds.length > 4) {
      setCompare(null);
      setCompareError("");
      return;
    }
    const controller = new AbortController();
    setCompareLoading(true);
    setCompareError("");
    api<CompareResponse>("compare", { method: "POST", body: JSON.stringify({ psi_ids: compareIds }), signal: controller.signal })
      .then(setCompare)
      .catch((error: Error) => { if (error.name !== "AbortError") { setCompare(null); setCompareError(error.message); } })
      .finally(() => { if (!controller.signal.aborted) setCompareLoading(false); });
    return () => controller.abort();
  }, [compareIds]);

  async function runSimulation(next: Scenario) {
    const sequence = ++simSequence.current;
    setSimLoading(true);
    setSimError("");
    try {
      const result = await api<SimResponse>("simulate", {
        method: "POST",
        body: JSON.stringify({
          mission: next.mission,
          o2_pct: next.oxygen_pct,
          pressure_psi: next.pressure_psi,
          airflow_cms: next.airflow_cms,
          gravity_g: next.gravity_g,
          gravity_regime: next.gravity,
          material: next.material,
          pillar: next.pillar,
        }),
      });
      if (sequence !== simSequence.current) return;
      setSim(result);
      setRanked(result.ranked_investigations ?? []);
      if (result.repository_scope) setRepositoryScope(result.repository_scope);
    } catch (error) {
      if (sequence === simSequence.current) setSimError((error as Error).message);
    } finally {
      if (sequence === simSequence.current) setSimLoading(false);
    }
  }

  function applyHabitat(id: string) {
    const habitat = habitats.find((item) => item.id === id);
    if (!habitat) return;
    const next = scenarioFromHabitat(habitat);
    setScenario(next);
    setActiveHabitat(id);
    void runSimulation(next);
  }

  function updateScenario<K extends keyof Scenario>(key: K, value: Scenario[K]) {
    setScenario((old) => ({ ...old, [key]: value }));
    setActiveHabitat("");
  }

  function submitScenario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActiveHabitat("");
    void runSimulation(scenario);
  }

  async function rankOnly() {
    setRankLoading(true);
    setRankingError("");
    try {
      const result = await api<{ items: RankItem[] }>("scenarios/rank", { method: "POST", body: JSON.stringify(reportScenario(scenario)) });
      setRanked(result.items);
    } catch (error) {
      setRankingError((error as Error).message);
    } finally {
      setRankLoading(false);
    }
  }

  function toggleCompare(id: string) {
    setCompareIds((old) => {
      if (old.includes(id)) return old.filter((item) => item !== id);
      if (old.length >= 4) return old;
      return [...old, id];
    });
  }

  async function inspectCycle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedRun) return;
    setCycleError("");
    setCycleData(null);
    cycleController.current?.abort();
    const controller = new AbortController();
    cycleController.current = controller;
    try {
      setCycleData(await api<Record<string, unknown>>(`samer/runs/${selectedRun}/cycles/${cycleNumber}`, { signal: controller.signal }));
    } catch (error) {
      if ((error as Error).name !== "AbortError") setCycleError((error as Error).message);
    }
  }

  async function download(format: "csv" | "html") {
    setDownloadMessage("");
    try {
      const response = await fetch(`/api/backend/reports/${format}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(reportScenario(scenario, activeHabitat)),
      });
      if (!response.ok) {
        const info = await response.json().catch(() => ({})) as ApiError;
        throw new Error(typeof info.detail === "string" ? info.detail : `Report request failed (${response.status}).`);
      }
      const blob = await response.blob();
      if (!blob.size) throw new Error("The server returned an empty report.");
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `firelytics-scientific-report.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setDownloadMessage(`${format.toUpperCase()} report downloaded (${blob.size.toLocaleString()} bytes).`);
    } catch (error) {
      setDownloadMessage((error as Error).message);
    }
  }

  function switchTab(id: TabId) {
    setActiveTab(id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const visible = useMemo(() => catalogue.filter((item) => {
    const text = [
      item.psi_id, item.name, item.short_name, item.objective, item.fuel_or_sample,
      item.sensors_variables, item.doi, item.hardware_rack, item.fuel_phase,
      ...(item.predictive_variables ?? []), ...(item.tags ?? []),
    ].join(" ").toLowerCase();
    const rackMatch = rackFilter === "All racks" || (item.hardware_rack ?? "").includes(rackFilter);
    return text.includes(query.toLowerCase())
      && (pillarFilter === "All pillars" || item.pillars.includes(pillarFilter))
      && rackMatch;
  }).sort((a, b) => sortBy === "id" ? a.psi_id.localeCompare(b.psi_id) : a.short_name.localeCompare(b.short_name)), [catalogue, query, pillarFilter, rackFilter, sortBy]);

  const activePreset = habitats.find((item) => item.id === activeHabitat);
  const habitatBadge = activePreset
    ? `${activePreset.name.toUpperCase()} · ${fmt(activePreset.o2_pct, 1)}% O₂ · ${fmt(activePreset.pressure_psi, 1)} PSI · ${fmt(activePreset.gravity_g, 3)}g`
    : `CUSTOM · ${fmt(scenario.oxygen_pct, 1)}% O₂ · ${fmt(scenario.pressure_psi, 1)} PSI · ${fmt(scenario.gravity_g, 3)}g`;

  const metrics = sim?.simulation.metrics;
  const synthesis: Synthesis | null = sim?.synthesis ?? compare?.synthesis ?? null;
  const phaseSummary = runSummary?.phase_summary;
  const metricsSummary = runSummary?.periodicity_metrics;
  const exceptionCycles = runSummary?.exception_cycles ?? [];
  const blockEvents = runSummary?.block_events ?? [];
  const cycleRecord = cycleData?.cycle as Record<string, unknown> | undefined;
  const sourceRefs = cycleData?.source_row_evidence as Record<string, unknown> | undefined;
  const displayRanked = showAllRanked ? ranked : ranked.slice(0, 6);

  const showSimulator = activeTab === "simulator" || activeTab === "executive";
  const showMatrix = activeTab === "matrix" || activeTab === "executive";
  const showSynthesis = activeTab === "synthesis" || activeTab === "executive";
  const showSamer = activeTab === "samer" || activeTab === "executive";
  const executive = activeTab === "executive";
  const showAiAssistant = activeTab === "ai";
  const showMlLab = activeTab === "ml";
  const showTelemetry = activeTab === "telemetry";
  const showDigitalTwin = activeTab === "digital-twin";
  const showDecisionSupport = activeTab === "decision-support";

  function renderSimulator() {
    return (
      <div className="tab-panel" key="simulator">
        <section className="mission-head shell">
          <div className="mission-intro">
            <div className="mission-kicker">
              <p className="eyebrow">FLAME IN FREEFALL · SCIENTIFIC INTELLIGENCE</p>
              <span className="mission-event-badge">NASA SPACE APPS CHALLENGE 2026</span>
            </div>
            <h1>
              Microgravity Combustion And{" "}
              <span className="mission-title-accent">Fire-Safety Intelligence</span>
            </h1>
            <p className="lead">
              An SI-powered scientific intelligence workspace to explore, compare and interpret NASA microgravity combustion experiments for safer human space exploration.
            </p>
            <p className="mission-secondary">Explore. Compare. Interpret. Discover insights for safer human space exploration.</p>
          </div>
          <div className="mission-meta">
            <div><span>PSI records indexed</span><b>{catalogue.length || "—"}</b></div>
            <div><span>Repository scope</span><b>{repositoryScope ? `${repositoryScope.total_investigations} · ${repositoryScope.aggregate_telemetry_label}` : "—"}</b></div>
            <div><span>SAME-R runs</span><b>{runs.length || "—"}</b></div>
          </div>
        </section>

        <div className="shell"><RepositoryScopePanel scope={repositoryScope} /></div>

        <div className="shell section-grid">
          <section className="panel">
            <div className="panel-head">
              <div><p className="eyebrow">01 · NASA MISSION HABITAT PRESETS</p><h2>One-click validated atmospheres</h2></div>
              <p className="muted">Click a card to load O₂, pressure, ventilation, gravity and material, then immediately POST <span className="mono">/api/backend/simulate</span>.</p>
            </div>
            {habitats.length ? (
              <div className="preset-grid">
                {habitats.map((habitat) => {
                  const active = activeHabitat === habitat.id;
                  return (
                    <button
                      type="button"
                      key={habitat.id}
                      className={`preset-card ${active ? "active" : ""}`}
                      onClick={() => applyHabitat(habitat.id)}
                      aria-pressed={active}
                    >
                      {active && <span className="preset-active">ACTIVE</span>}
                      <span className="preset-id"><span>{habitat.id.replaceAll("_", " ").toUpperCase()}</span><span>P_O2 {fmt(habitat.po2_psi, 2)} psi</span></span>
                      <h3>{habitat.name}</h3>
                      <div className="preset-metrics">
                        <span>{fmt(habitat.o2_pct, 1)}% O₂</span>
                        <span>{fmt(habitat.pressure_psi, 1)} psi</span>
                        <span>{fmt(habitat.gravity_g, 3)} g</span>
                      </div>
                      <span className="preset-risk">{habitat.key_risk}</span>
                    </button>
                  );
                })}
              </div>
            ) : <div className="empty">Habitat presets are unavailable. The scenario builder remains usable.</div>}
          </section>

          <section className="panel">
            <div className="panel-head">
              <div><p className="eyebrow">02 · SCENARIO BUILDER</p><h2>Define the environment under test</h2></div>
              <span className="pill">{simLoading ? "PROPAGATING…" : "READY"}</span>
            </div>
            <form onSubmit={submitScenario}>
              <div className="form-grid">
                <label className="field"><span>Mission name</span><input value={scenario.mission} maxLength={120} required onChange={(event) => updateScenario("mission", event.target.value)} /></label>
                <label className="field">
                  <span>Gravity regime</span>
                  <select value={scenario.gravity} onChange={(event) => {
                    const label = event.target.value;
                    setScenario((old) => ({ ...old, gravity: label, gravity_g: gravityValue(label) }));
                    setActiveHabitat("");
                  }}>
                    <option>Unknown</option><option>Microgravity</option><option>Lunar partial gravity</option><option>Mars partial gravity</option><option>Earth gravity</option>
                  </select>
                </label>
                <label className="field">
                  <span>Research pillar</span>
                  <select value={scenario.pillar} onChange={(event) => updateScenario("pillar", event.target.value)}>
                    <option>Any pillar</option><option>Prevention</option><option>Detection</option><option>Suppression</option>
                  </select>
                </label>
                <label className="field"><span>Material / fuel</span><input value={scenario.material} maxLength={200} onChange={(event) => updateScenario("material", event.target.value)} placeholder="Pyrell, Sibal, methanol…" /></label>
              </div>
              <div className="numeric-grid" style={{ marginTop: 10 }}>
                <NumberField label="Oxygen (vol %)" value={scenario.oxygen_pct} min={0} max={100} step={0.1} hint="Mole fraction in the cabin atmosphere" onChange={(value) => updateScenario("oxygen_pct", value)} />
                <NumberField label="Pressure (psi)" value={scenario.pressure_psi} min={0.1} max={30} step={0.1} hint={`${fmt(scenario.pressure_psi / 14.7, 3)} atm`} onChange={(value) => updateScenario("pressure_psi", value)} />
                <NumberField label="Airflow (cm/s)" value={scenario.airflow_cms} min={0} max={250} step={0.1} hint="Forced ventilation / co-flow" onChange={(value) => updateScenario("airflow_cms", value)} />
              </div>
              <div className="panel-actions" style={{ justifyContent: "flex-start", marginTop: 12 }}>
                <button className="button primary" type="submit" disabled={simLoading}>{simLoading ? "Propagating physics…" : "Run simulation →"}</button>
                <button className="button secondary" type="button" onClick={rankOnly} disabled={rankLoading}>{rankLoading ? "Ranking…" : "Rank catalogue only"}</button>
                <span className="tiny">POST /api/backend/simulate · POST /api/backend/scenarios/rank</span>
              </div>
            </form>
            {simError && <ErrorBox message={simError} />}
            {rankingError && <ErrorBox message={rankingError} />}
          </section>

          <div className="kpi-grid">
            <Kpi label="O₂ partial pressure" value={`${fmt(metrics?.po2_psi)} psi`} sub={`Earth 3.09 psi · ${fmt((metrics?.po2_psi ?? 0) / 3.087 * 100, 0)}% of sea level`} tone={(metrics?.po2_psi ?? 0) > 3.6 ? "hazard" : (metrics?.po2_psi ?? 0) > 3.09 ? "warn" : "good"} />
            <Kpi label="Estimated MOC" value={`${fmt(metrics?.estimated_moc_pct)}%`} sub={metrics?.regime_classification ?? "Awaiting simulation"} tone={(metrics?.regime_classification ?? "").includes("Peak") ? "warn" : "good"} />
            <Kpi label="Flammability index" value={fmt(metrics?.flammability_index, 1)} sub="0–100 screening surrogate · not a prediction" tone={(metrics?.flammability_index ?? 0) >= 70 ? "hazard" : (metrics?.flammability_index ?? 0) >= 45 ? "warn" : "good"} />
            <Kpi label="Buoyant / effective V" value={`${fmt(metrics?.buoyant_velocity_cms, 1)} / ${fmt(metrics?.effective_velocity_cms, 1)}`} sub="cm/s · √(V_forced² + V_buoyant²)" />
            <Kpi label="Peak hazard gravity" value={`${fmt(metrics?.peak_hazard_gravity_g, 3)} g`} sub="Screening curve maximum, not a measured limit" tone="warn" />
            <Kpi label="E-FIELD equivalent" value={`${fmt(sim?.simulation.efield_equivalence.estimated_equivalent_kv_cm, 2)} kV/cm`} sub={`${fmt(sim?.simulation.efield_equivalence.equivalent_voltage_kv, 2)} kV · matches ${fmt(sim?.simulation.efield_equivalence.ion_velocity_match_cms, 1)} cm/s`} />
          </div>
          <p className="small-caution" style={{ marginTop: -4 }}>
            {sim?.simulation.model.limitations ?? "Simulation output is a transparent visualization surrogate anchored to 0 g and 1 g evidence; it is not a NASA measurement, design limit or safety determination."}
          </p>

          <div className="viz-grid">
            <section className="panel">
              <div className="panel-head">
                <div><p className="eyebrow">CHART A · O₂ / PRESSURE ENVELOPE</p><h2>Flammability boundary map</h2></div>
                <span className="pill">BASS-II · SAFFIRE</span>
              </div>
              {sim ? <O2PressureEnvelopeChart simulation={sim.simulation} activeHabitat={activeHabitat} onSelectHabitat={applyHabitat} theme={theme} /> : <div className="empty">Run a simulation to compute the envelope.</div>}
            </section>
            <section className="panel">
              <div className="panel-head">
                <div><p className="eyebrow">CHART B · PARTIAL-GRAVITY BOUNDING</p><h2>Lunar dip &amp; ion-convection analogue</h2></div>
                <span className="pill">0 g → 1 g</span>
              </div>
              {sim ? <PartialGravityBoundingChart curve={sim.simulation.gravity_curve} efield={sim.simulation.efield_equivalence} targetGravity={scenario.gravity_g} theme={theme} /> : <div className="empty">Run a simulation to compute the gravity curve.</div>}
            </section>
          </div>

          <section className="panel">
            <div className="panel-head">
              <div><p className="eyebrow">CHART C · RANKED EVIDENCE BREAKDOWN</p><h2>Which investigation actually bounds this scenario?</h2></div>
              <span className="pill">{ranked.length} ranked records</span>
            </div>
            <EvidenceBarChart ranked={ranked} />
          </section>

          <section className="panel">
            <div className="panel-head">
              <div><p className="eyebrow">03 · RANKED STUDIES</p><h2>Evidence sets &amp; factor-level reasons</h2></div>
              <div className="panel-actions">
                <span className="pill">{habitatBadge}</span>
                {ranked.length > 6 && <button className="button ghost small" type="button" onClick={() => setShowAllRanked((old) => !old)}>{showAllRanked ? "Show top 6" : `Show all ${ranked.length}`}</button>}
              </div>
            </div>
            {displayRanked.length ? (
              <div className="rank-list">
                {displayRanked.map((item, index) => (
                  <article className="rank-card" key={item.psi_id}>
                    <div className="rank-num">{String(index + 1).padStart(2, "0")}</div>
                    <div>
                      <div className="rank-heading">
                        <div><span className="study-code">{item.psi_id} · {item.hardware_rack}</span><h3>{item.short_name}</h3><p>{item.objective}</p></div>
                        <div className="score-pair">
                          <div><b>{fmt(item.match_score, 1)}%</b><small>similarity</small></div>
                          <div><b>{fmt(item.evidence_coverage, 1)}%</b><small>coverage</small></div>
                          <div><b>{fmt(item.physics_proximity?.mean_overlap != null ? item.physics_proximity.mean_overlap * 100 : null, 0)}%</b><small>physics overlap</small></div>
                        </div>
                      </div>
                      <details>
                        <summary>Inspect {item.ranking_factors.length} ranking factors</summary>
                        <div className="factor-list">
                          {item.ranking_factors.map((factor) => (
                            <div className="factor" key={factor.factor}>
                              <span className="factor-score">{factor.score === null ? "—" : factor.score.toFixed(1)}</span>
                              <div><b>{factor.factor} · {factor.status}</b><p>{factor.explanation}</p></div>
                            </div>
                          ))}
                        </div>
                      </details>
                      <div className="source-links">
                        <a href={item.source_url} target="_blank" rel="noreferrer">NASA PSI ↗</a>
                        <a href={item.doi_url} target="_blank" rel="noreferrer">DOI ↗</a>
                        <span>{item.local_data_status.replace(/local/gi, "project")}</span>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            ) : <div className="empty">Submit the scenario to request live rankings.</div>}
          </section>

          <section className="panel report-row">
            <div>
              <p className="eyebrow">04 · REPORT EXPORT</p>
              <h2>Take the evidence with you.</h2>
              <p>Both reports carry the selected habitat parameters (O₂, pressure, P₀₂, gravity, buoyant velocity, MOC and PSI-22 E-FIELD equivalent), the full 14 deeply indexed + 10 associated PSI scope note (~12.4 TB), factor explanations, source citations and the archived SAME-R summary.</p>
            </div>
            <div className="report-actions">
              <button className="button primary" type="button" onClick={() => download("csv")}>Download CSV ↓</button>
              <button className="button secondary" type="button" onClick={() => download("html")}>Download HTML ↓</button>
              {downloadMessage && <p className="download-status" role="status">{downloadMessage}</p>}
            </div>
          </section>
        </div>
      </div>
    );
  }

  function renderMatrix() {
    return (
      <div className="tab-panel" key="matrix">
        <div className="shell section-grid" style={{ paddingTop: 26 }}>
          <section className="panel">
            <div className="panel-head">
              <div><p className="eyebrow">CATALOGUE · 14 VERIFIED PSI RECORDS</p><h2>Hardware, envelopes &amp; provenance</h2></div>
              <span className="pill">{visible.length} visible · {compareIds.length}/4 selected</span>
            </div>
            <div className="filter-grid">
              <label className="field wide"><span>Search records</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Smoke, Pyrell, DAFT, CIR, MOC, DOI…" /></label>
              <label className="field"><span>Pillar</span><select value={pillarFilter} onChange={(event) => setPillarFilter(event.target.value)}><option>All pillars</option><option>Prevention</option><option>Detection</option><option>Suppression</option></select></label>
              <label className="field"><span>Hardware rack</span><select value={rackFilter} onChange={(event) => setRackFilter(event.target.value)}><option>All racks</option><option>CIR</option><option>MSG</option><option>MDCA</option><option>Cygnus</option><option>Cabin</option></select></label>
              <label className="field"><span>Sort</span><select value={sortBy} onChange={(event) => setSortBy(event.target.value)}><option value="name">Short name</option><option value="id">PSI identifier</option></select></label>
              <span className="tiny" style={{ alignSelf: "end", paddingBottom: 8 }}>Compare defaults: BASS-II · BRE · E-FIELD · FLEX</span>
            </div>
            <div className="catalogue-layout" style={{ marginTop: 12 }}>
              <div className="record-list">
                {visible.map((item) => {
                  const checked = compareIds.includes(item.psi_id);
                  const disabled = !checked && compareIds.length >= 4;
                  return (
                    <div key={item.psi_id} className={`record-row ${selectedId === item.psi_id ? "selected" : ""}`}>
                      <input
                        type="checkbox"
                        aria-label={`Compare ${item.short_name}`}
                        checked={checked}
                        disabled={disabled}
                        onChange={() => toggleCompare(item.psi_id)}
                      />
                      <button type="button" className="record-open" onClick={() => setSelectedId(item.psi_id)}>
                        <b>{item.short_name}</b>
                        <small>{item.name}</small>
                      </button>
                      <span className="record-meta"><b>{item.psi_id}</b><span>{rangeText(item.o2_range_pct, "%")}</span><span>{item.hardware_rack}</span></span>
                    </div>
                  );
                })}
                {!visible.length && <div className="empty">No investigation matches the current filters.</div>}
              </div>
              <article className="record-detail">
                {detail ? (
                  <>
                    <div className="detail-top" style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                      <span className="study-code">{detail.psi_id} · {detail.verification_status.replaceAll("_", " ")}</span>
                      <span className="tag">{detail.research_area}</span>
                    </div>
                    <h3>{detail.short_name}</h3>
                    <p className="record-title">{detail.name}</p>
                    <p>{detail.objective}</p>
                    <div className="tag-row">{detail.pillars.map((pillar) => <span className="tag" key={pillar}>{pillar}</span>)}</div>
                    <div className="range-chips">
                      <span className="chip">O₂ {rangeText(detail.o2_range_pct, "%")}</span>
                      <span className="chip">P {rangeText(detail.pressure_range_psi, " psi")}</span>
                      <span className="chip">V {rangeText(detail.airflow_range_cm_s ?? detail.airflow_range_cms, " cm/s")}</span>
                      <span className="chip">{detail.hardware_rack}</span>
                      <span className="chip">{detail.fuel_phase}</span>
                    </div>
                    <dl className="facts">
                      <dt>Fuel / sample</dt><dd>{detail.fuel_or_sample}</dd>
                      <dt>Hardware</dt><dd>{detail.platform} · {detail.hardware}</dd>
                      <dt>Oxygen</dt><dd>{detail.oxygen_recorded}</dd>
                      <dt>Pressure</dt><dd>{detail.pressure_recorded}</dd>
                      <dt>Airflow</dt><dd>{detail.airflow_recorded}</dd>
                      <dt>Gravity</dt><dd>{detail.gravity_level}</dd>
                      <dt>Predictive variables</dt><dd>{detail.predictive_variables.join(" · ")}</dd>
                      <dt>Sensors</dt><dd>{detail.sensors_variables}</dd>
                      <dt>Earth spin-off</dt><dd>{detail.earth_spinoff.title} — {detail.earth_spinoff.terrestrial_application}</dd>
                      <dt>Incident links</dt><dd>{detail.historical_incident_links.length ? detail.historical_incident_links.join(" · ") : "None recorded"}</dd>
                      <dt>Evidence availability</dt><dd>{detail.local_data_status.replace(/local/gi, "project")}</dd>
                    </dl>
                    <div className="source-links">
                      <a href={detail.source_url} target="_blank" rel="noreferrer">NASA PSI ↗</a>
                      <a href={detail.doi_url} target="_blank" rel="noreferrer">DOI {detail.doi} ↗</a>
                      <span>{detail.license}</span>
                    </div>
                  </>
                ) : <div className="empty">Select an investigation to load its full source record.</div>}
              </article>
            </div>
          </section>

          <section className="panel">
            <div className="panel-head">
              <div><p className="eyebrow">05 · CROSS-INVESTIGATION COMPARATOR</p><h2>Side-by-side experimental deltas</h2></div>
              <div className="panel-actions">
                <span className={`compare-counter ${compareIds.length < 2 ? "warn-text" : ""}`}>{compareIds.length}/4 selected</span>
                <button className="button ghost small" type="button" onClick={() => setCompareIds([])}>Clear</button>
              </div>
            </div>
            <div className="badge-row">
              {compareIds.map((id) => (
                <button className="chip" type="button" key={id} onClick={() => toggleCompare(id)} title="Remove from comparison">{id} ×</button>
              ))}
              {!compareIds.length && <span className="muted">Select 2–4 investigations with the checkboxes. Default: PSI-25, PSI-20, PSI-22, PSI-69.</span>}
            </div>
            {compareLoading && <div className="loading" role="status">POST /api/backend/compare · building matrix…</div>}
            {compareError && <ErrorBox message={compareError} />}
            {compareIds.length === 1 && <div className="empty">Select one more investigation to enable comparison.</div>}
            {compare && !compareLoading && (
              <>
                <div className="badge-row">
                  <div className="science-badge">
                    <span>SHARED HARDWARE</span>
                    <b>{compare.synthesis.commonalities[0]?.hardware_racks.join(" · ") || "No shared rack"}</b>
                    <span>{compare.synthesis.commonalities[0]?.shared_predictive_variables.length ?? 0} shared predictive variables</span>
                  </div>
                  <div className="science-badge warn">
                    <span>PRESSURE INTERSECTION</span>
                    <b>{rangeText(compare.synthesis.commonalities[0]?.pressure_envelope_intersection_psi, " psi")}</b>
                    <span>O₂ intersection {rangeText(compare.synthesis.commonalities[0]?.o2_envelope_intersection_pct, "%")}</span>
                  </div>
                  <div className="science-badge">
                    <span>AIRFLOW INTERSECTION</span>
                    <b>{rangeText(compare.synthesis.commonalities[0]?.airflow_envelope_intersection_cm_s, " cm/s")}</b>
                    <span>Documented envelopes only</span>
                  </div>
                </div>
                <div className="table-scroll-wrapper matrix-scroll">
                  <table className="matrix">
                    <thead>
                      <tr><th>Field</th>{compare.matrix.map((study) => <th key={String(study.psi_id)}>{String(study.short_name ?? study.psi_id)}<br /><span className="tiny">{String(study.psi_id)}</span></th>)}</tr>
                    </thead>
                    <tbody>
                      {MATRIX_ROWS.map(([field, label]) => (
                        <tr key={field}>
                          <th>{label}</th>
                          {compare.matrix.map((study) => <td key={`${field}-${String(study.psi_id)}`}><MatrixCell field={field} study={study} /></td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="panel-head" style={{ marginTop: 16 }}>
                  <div><p className="eyebrow">AUTOMATED EXPERIMENTAL DELTAS</p><h3>Where the selected experiments diverge</h3></div>
                  <span className="pill">{compare.deltas.length} records</span>
                </div>
                <p className="small-caution">
                  Hardware lineage: <b>MSG + SPICE fan-driven flow duct</b> links BASS, BASS-II, SPICE and SLICE; <b>CIR</b> links ACME BRE, CFI-G, E-FIELD and the FLEX / MDCA droplet inserts. Shared rack does not mean interchangeable test conditions.
                </p>
                <div className="delta-grid">
                  {compare.deltas.map((delta) => (
                    <div className="delta-card" key={String(delta.psi_id)}>
                      <span className="study-code">{String(delta.psi_id)} · {String(delta.hardware_rack ?? "—")}</span>
                      <h4>{String(delta.short_name ?? "—")}</h4>
                      <p>{String(delta.fuel_phase ?? "—")} · {String(delta.fuel_or_sample ?? "").slice(0, 160)}</p>
                      <div className="delta-spans">
                        <span className="chip">O₂ {rangeText(delta.o2_range_pct, "%")}</span>
                        <span className="chip">P {rangeText(delta.pressure_range_psi, " psi")}</span>
                        <span className="chip">V {rangeText(delta.airflow_range_cm_s, " cm/s")}</span>
                        <span className="chip">{(Array.isArray(delta.gravity_regimes) ? delta.gravity_regimes : []).join(" · ") || "—"}</span>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="small-caution" style={{ marginTop: 10 }}>{compare.interpretation}</p>
              </>
            )}
          </section>
        </div>
      </div>
    );
  }

  function renderSynthesis() {
    return (
      <div className="tab-panel" key="synthesis">
        <div className="shell section-grid" style={{ paddingTop: 26 }}>
          <section className="panel">
            <div className="panel-head">
              <div><p className="eyebrow">SI-POWERED FIRE-SAFETY SYNTHESIS</p><h2>Prevention · Detection · Suppression</h2></div>
              <span className="pill">{synthesis ? `${synthesis.selected_ids.length} investigations synthesised` : "AWAITING SIMULATION"}</span>
            </div>
            {!synthesis ? (
              <div className="empty">Run the mission simulator to generate a structured cross-investigation synthesis.</div>
            ) : (
              <>
                <div className="synthesis-grid">
                  <article className="synthesis-card">
                    <p className="eyebrow">PREVENTION</p>
                    <h3>Material screening rule</h3>
                    <StatementList items={synthesis.sections.prevention} empty="No selected study is classified under prevention." />
                  </article>
                  <article className="synthesis-card">
                    <p className="eyebrow">DETECTION</p>
                    <h3>Smoke vs nuisance dust</h3>
                    <StatementList items={synthesis.sections.detection} empty="Select SAME-R / SAME / DAFT to activate the detector synthesis." />
                  </article>
                  <article className="synthesis-card">
                    <p className="eyebrow">SUPPRESSION</p>
                    <h3>Inerting &amp; cool flames</h3>
                    <StatementList items={synthesis.sections.suppression} empty="Select FLEX or FLEX-2/CFI to activate the suppression synthesis." />
                  </article>
                  <article className="synthesis-card">
                    <p className="eyebrow">PARTIAL GRAVITY</p>
                    <h3>Lunar / Mars bounding</h3>
                    <StatementList items={synthesis.sections.partial_gravity} empty="Select E-FIELD to activate the ion-convection analogue." />
                  </article>
                </div>
                <div className="panel" style={{ marginTop: 12 }}>
                  <div className="panel-head">
                    <div><p className="eyebrow">DETECTION DETAIL</p><h3>SAME / SAME-R vs DAFT</h3></div>
                    <span className="pill">D32 0.1–0.5 µm vs &gt;1.0 µm</span>
                  </div>
                  <DustDiscriminationPanel theme={theme} />
                </div>
                <div className="panel" style={{ marginTop: 12 }}>
                  <div className="panel-head">
                    <div><p className="eyebrow">HISTORICAL INCIDENT LINKS</p><h3>Why the physics matters operationally</h3></div>
                    <span className="pill">{synthesis.sections.historical_incidents.length} linked events</span>
                  </div>
                  <div className="incident-grid">
                    {synthesis.sections.historical_incidents.map((incident) => {
                      const note = Object.entries(INCIDENT_NOTES).find(([key]) => incident.toLowerCase().includes(key.toLowerCase()))?.[1];
                      return <div className="incident-card" key={incident}><b>{incident}</b><span>{note ?? "Linked from the selected catalogue records."}</span></div>;
                    })}
                    {!synthesis.sections.historical_incidents.length && <div className="empty">No incident links are attached to the selected records.</div>}
                  </div>
                </div>
                <div className="panel" style={{ marginTop: 12 }}>
                  <div className="panel-head">
                    <div><p className="eyebrow">EARTH SPIN-OFFS</p><h3>Terrestrial technology transfer</h3></div>
                    <span className="pill">{synthesis.sections.earth_spinoffs.length} transfers</span>
                  </div>
                  <div className="spinoff-grid">
                    {synthesis.sections.earth_spinoffs.map((spinoff) => (
                      <div className="spinoff-card" key={`${spinoff.psi_id}-${spinoff.title}`}>
                        <span className="study-code">{spinoff.psi_id} · {spinoff.nasa_origin}</span>
                        <b>{spinoff.title}</b>
                        <span>{spinoff.terrestrial_application}</span>
                        <span className="tiny">{spinoff.impact_metric}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="panel" style={{ marginTop: 12 }}>
                  <p className="eyebrow">EVIDENCE BOUNDARY</p>
                  <ul className="muted" style={{ margin: "6px 0 0", paddingLeft: 16 }}>
                    {synthesis.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}
                  </ul>
                </div>
              </>
            )}
          </section>
        </div>
      </div>
    );
  }

  function renderSamer() {
    return (
      <div className="tab-panel" key="samer">
        <div className="shell section-grid" style={{ paddingTop: 26 }}>
          <section className="panel">
            <div className="panel-head">
              <div><p className="eyebrow">PSI-101 · SAME-R TELEMETRY &amp; LINEAGE LAB</p><h2>Archived Pyrell cycle evidence</h2></div>
              <span className="pill">6 reconciled runs</span>
            </div>
            <div className="archive-banner">
              <b>Archived-output mode.</b> The deployed service does not contain the original CSVs and does not rerun historical source filters.
              It verifies the archived cycle ledger against phase summaries, exact exception identities, mixed rows, duplicates and run metrics.
              Source row numbers are retained; original row values are not bundled.
            </div>
            <div className="run-picker">
              {runs.map((run) => (
                <button type="button" key={run.run_id} className={`run-chip ${selectedRun === run.run_id ? "active" : ""}`} onClick={() => setSelectedRun(run.run_id)}>
                  RUN {run.run_id} · {run.classified_cycles.toLocaleString()} classified
                </button>
              ))}
            </div>
            {validationError && <ErrorBox message={validationError} />}
            {runValidation && (
              <div className="panel" style={{ marginBottom: 12 }}>
                <div className="panel-head">
                  <div><p className="eyebrow">SELECTED RUN VALIDATION</p><h3>Run {selectedRun} · checkpoint reconciliation</h3></div>
                  <span className="tag">{runValidation.status}</span>
                </div>
                <p className="muted">Archived-output consistency only. This does not replay raw NASA CSVs or constitute independent scientific validation.</p>
                <p className="small-caution">Raw replay performed: <b>{runValidation.raw_replay_performed ? "Yes" : "No"}</b> · {runValidation.processing_status}</p>
                <div className="validation-checks">
                  {Object.entries(runValidation.checks).filter(([key]) => key !== "run_id").map(([key, value]) => (
                    <div className="validation-check" key={key}>
                      <span>{key.replaceAll("_", " ")}</span>
                      <b className={value === true ? "check-pass" : value === false ? "check-fail" : ""}>{value === true ? "PASS" : value === false ? "FAIL" : String(value)}</b>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {runError && <ErrorBox message={runError} />}
            {phaseSummary && metricsSummary && (
              <>
                <div className="kpi-grid archive-stats">
                  <Kpi label="Archived classified cycles" value={Number(phaseSummary.ClassifiedCycles ?? 0).toLocaleString()} sub={`Eligible ${metricsSummary.FirstEligibleCycle}–${metricsSummary.LastEligibleCycle}`} />
                  <Kpi label="Phase exceptions" value={Number(phaseSummary.ExceptionCycles ?? 0).toLocaleString()} sub="Classification mismatch, not a fire" tone="warn" />
                  <Kpi label="Mixed-band cycles" value={Number(phaseSummary.MixedBandCycles ?? 0).toLocaleString()} sub="Excluded from binary classification" />
                  <Kpi label="Duplicate cycles" value={Number(phaseSummary.DuplicateCycleNumbers ?? 0).toLocaleString()} sub={`${metricsSummary.MissingCycleNumbers ?? "—"} missing · ${metricsSummary.GapEvents ?? "—"} gaps`} />
                </div>
                <SamerTelemetryVisual summary={runSummary ?? {}} runId={selectedRun} theme={theme} />
                <div className="panel" style={{ marginTop: 10 }}>
                  <div className="panel-head"><div><p className="eyebrow">DETECTOR DISCRIMINATION</p><h3>Pyrolysis smoke vs lunar / cabin dust</h3></div><span className="pill">Artemis II nuisance-alarm case</span></div>
                  <DustDiscriminationPanel theme={theme} />
                </div>
                <div className="two-col section-grid" style={{ marginTop: 12 }}>
                  <article className="panel">
                    <p className="eyebrow">EXCEPTION CYCLES</p>
                    <h3>{exceptionCycles.length} archived exceptions</h3>
                    <p className="muted">Cycle numbers are classification mismatches retained for lineage. They do not establish a fire, alarm or detector failure.</p>
                    <div className="cycle-tags">{exceptionCycles.map((cycle) => <span key={cycle}>{cycle}</span>)}</div>
                  </article>
                  <article className="panel">
                    <p className="eyebrow">BLOCK EVENTS</p>
                    <h3>{blockEvents.length} mismatch / agreement blocks</h3>
                    {blockEvents.length ? <div className="scroll-list">{blockEvents.map((block, index) => (
                      <div className="block-row" key={`${block.StartCycle}-${index}`}><b>{block.EventType}</b><span>Cycles {block.StartCycle}–{block.EndCycle} · length {block.BlockLength}</span></div>
                    ))}</div> : <p className="muted">No block event rows are listed for this run.</p>}
                  </article>
                </div>
                <form className="cycle-form" onSubmit={inspectCycle}>
                  <label className="field"><span>Cycle number</span><input type="number" required min={Number(phaseSummary.FirstCycle)} max={Number(phaseSummary.LastCycle)} value={cycleNumber} onChange={(event) => setCycleNumber(Number(event.target.value))} /><small>Lookup returns the archived cycle and exact source-row references.</small></label>
                  <button className="button primary" type="submit">Inspect archived cycle →</button>
                </form>
                {cycleError && <ErrorBox message={cycleError} />}
                {cycleRecord && sourceRefs && (
                  <article className="panel">
                    <div className="panel-head">
                      <div><p className="eyebrow">RUN {selectedRun} / CYCLE {String(cycleRecord.Cycle)}</p><h3>{String(cycleRecord.ObservedBand)} <span className="muted">/ expected {String(cycleRecord.ExpectedBand)}</span></h3></div>
                      <span className={`tag ${cycleRecord.ExceptionIndicator === 1 ? "alert-tag" : ""}`}>{cycleRecord.ExceptionIndicator === 1 ? "Phase exception" : cycleRecord.MixedBandIndicator === 1 ? "Mixed band" : "Phase agreement"}</span>
                    </div>
                    <div className="cycle-facts">
                      <span>Phase {String(cycleRecord.RelativeCyclePhase)}</span>
                      <span>Source records {String(cycleRecord.SourceRowCount)}</span>
                      <span>Timestamp {String(cycleRecord.FirstTimestamp)} – {String(cycleRecord.LastTimestamp)}</span>
                      <span>Duplicate cycle {cycleRecord.DuplicateCycleIndicator ? "Yes" : "No"}</span>
                    </div>
                    <p className="muted"><b>Original source-row references:</b> {String((sourceRefs.source_data_rows as number[] | undefined)?.join(", ") || "No source row reference recorded")}; CSV line(s): {String((sourceRefs.csv_line_numbers as number[] | undefined)?.join(", ") || "not recorded")}</p>
                    <p className="small-caution">{String(sourceRefs.message ?? "")}</p>
                  </article>
                )}
                <ArchivedPatternTables summary={runSummary ?? {}} />
              </>
            )}
            {!phaseSummary && !runError && <div className="loading">Loading run archive…</div>}
          </section>
        </div>
      </div>
    );
  }

  function renderMethods() {
    return (
      <section className="panel">
        <div className="panel-head"><div><p className="eyebrow">METHODS · SOURCES · LIMITATIONS</p><h2>Make the boundary of the evidence visible</h2></div><span className="pill">NO NASA ENDORSEMENT CLAIMED</span></div>
        <div className="method-grid">
          <article>
            <h3>Ranking method</h3>
            <p>Match score = 100 × sum of known factor scores / number of known factor scores. Pillar, material, structured O₂ envelope, pressure, airflow and gravity are considered. Match = 1; apparatus capability = 0.5; documented mismatch = 0. Unknown factors leave the denominator.</p>
            <p>Physics proximity is a continuous overlap diagnostic and does not alter the documented match score. Neither is a validated fire model or safety rating.</p>
          </article>
          <article>
            <h3>SAME-R archive</h3>
            <p>The preserved replay uses the historical filters and matches all six archived checkpoints. The deployment bundles only generated cycle sequences and summaries and verifies them against exception identities, mixed rows and duplicate counts.</p>
            <p>Phase exceptions are classification mismatches. They do not establish a fire, detector failure or physical cause.</p>
          </article>
          <article>
            <h3>Applicability limits</h3>
            <p>Fourteen catalogue records are linked to NASA PSI; only PSI-101 has project-analyzed measurements. Partial-gravity curves are screening hypotheses bounded by 0 g data, 1 g screening and the PSI-22 ion-wind analogue — LUCI and FM2 remain the required direct lunar measurements.</p>
            <p>Raw PSI-101 CSVs are not bundled because their redistribution terms are not established. No output is a fire prediction, design limit or operational safety assessment.</p>
          </article>
        </div>
        <div className="references">
          {catalogue.map((item) => <a key={item.psi_id} href={item.source_url} target="_blank" rel="noreferrer">{item.psi_id} · {item.short_name} ↗</a>)}
        </div>
        <p className="final-note">Independent research prototype · Columbia/Glenn PSI metadata · CC0-1.0 record metadata · no NASA endorsement, certification or validated fire prediction.</p>
      </section>
    );
  }

  return (
    <main data-theme={theme}>
      <div className="ambient-bg-layer" aria-hidden="true" />
      <header className="telemetry-bar">
        <div className="telemetry-top">
          <a className="brand" href="#workspace"><span className="brandmark"><img src="/assets/fire-logo.webp" alt="FIRELYTICS flame logo" width={34} height={34} /></span><span>FIRELYTICS <em>AI</em></span></a>
          <div className="status-cluster">
            <span className={`pill provenance-pill ${health.startsWith("ok") ? "live" : ""}`}>{catalogue.length || 0} VERIFIED NASA PSI INVESTIGATIONS · DOI-LINKED PROVENANCE</span>
            <span className="pill habitat" title={activePreset?.key_risk ?? scenario.mission}>{habitatBadge}</span>
          </div>
          <div className="telemetry-actions">
            <span className="tiny">{health}</span>
            <button
              ref={developerButtonRef}
              className="developer-button"
              type="button"
              aria-haspopup="dialog"
              aria-expanded={isDeveloperModalOpen}
              onClick={() => setIsDeveloperModalOpen(true)}
            >
              <DeveloperIcon />
              Developer
            </button>
            <button
              className="theme-toggle"
              type="button"
              onClick={() => setTheme((current) => current === "light" ? "dark" : "light")}
              aria-pressed={theme === "dark"}
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            >
              <span aria-hidden="true">{theme === "light" ? "☀️" : "🌙"}</span>
              {theme === "light" ? "Light Mode" : "Dark Mode"}
            </button>
            <button className="icon-button" type="button" onClick={() => window.location.reload()} aria-label="Refresh catalogue and archive" title="Refresh live catalogue and archive">↻</button>
          </div>
        </div>
        <div className="tabbar" role="tablist" aria-label="Workspace modes">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              className={`tab ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => switchTab(tab.id)}
            >
              {tab.id === "ai" || tab.id === "ml" || tab.id === "telemetry" || tab.id === "digital-twin" || tab.id === "decision-support"
                ? tab.label
                : `${tab.short} · ${tab.label}`}
            </button>
          ))}
        </div>
      </header>

      <div id="workspace">
        {loadError && <div className="shell" style={{ paddingTop: 20 }}><ErrorBox message={loadError} /><button className="button ghost" type="button" onClick={() => window.location.reload()}>Retry connection</button></div>}
        {loading && <div className="shell loading" role="status">Loading NASA catalogue, habitat profiles and archive checkpoints…</div>}
        {!loading && !loadError && (
          <>
            {showSimulator && renderSimulator()}
            {executive && <div className="shell"><div className="exec-divider">02 · CATALOGUE &amp; CROSS-INVESTIGATION MATRIX</div></div>}
            {showMatrix && renderMatrix()}
            {executive && <div className="shell"><div className="exec-divider">03 · SI-POWERED FIRE-SAFETY SYNTHESIS</div></div>}
            {showSynthesis && renderSynthesis()}
            {executive && <div className="shell"><div className="exec-divider">04 · PSI-101 SAME-R TELEMETRY &amp; LINEAGE</div></div>}
            {showSamer && renderSamer()}
            {executive && <div className="shell" style={{ paddingTop: 10 }}>{renderMethods()}</div>}
            {showAiAssistant && (
              <div className="shell">
                <AiResearchAssistant
                  catalogue={catalogue}
                  scenario={scenario}
                  simulation={sim}
                  compareIds={compareIds}
                />
              </div>
            )}
            {showMlLab && (
              <div className="shell">
                <MlFireResearchLab theme={theme} />
              </div>
            )}
            {showTelemetry && (
              <div className="shell">
                <VirtualSpacecraftMonitoring theme={theme} />
              </div>
            )}
            {showDigitalTwin && <FireSuppressionDigitalTwin theme={theme} />}
            {showDecisionSupport && (
              <ScientificDecisionSupport scenario={scenario} theme={theme} />
            )}
          </>
        )}
      </div>

      <footer className="footer">
        <span>FIRELYTICS AI</span>
        <span>Evidence first · limits stated · source linked</span>
        <span>14 NASA PSI records · 6 archived SAME-R runs · 5 habitat presets</span>
        <a href="https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/" target="_blank" rel="noreferrer">NASA Space Apps · Flame in Freefall ↗</a>
      </footer>
      {isDeveloperModalOpen && (
        <DeveloperTeamModal onClose={closeDeveloperModal} returnFocus={developerButtonRef.current} />
      )}
    </main>
  );
}
