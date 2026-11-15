export type Ranged = [number, number];

export type Factor = { factor: string; status: string; explanation: string; score: number | null };

export type Investigation = {
  psi_id: string;
  name: string;
  short_name: string;
  doi: string;
  doi_url: string;
  source_url: string;
  research_area: string;
  subresearch_area: string;
  pillars: string[];
  objective: string;
  source_objective_verbatim: string;
  source_findings: string;
  fuel_or_sample: string;
  hardware: string;
  platform: string;
  gravity_level: string;
  oxygen_recorded: string;
  oxygen_comparison: Record<string, unknown> | null;
  pressure_recorded: string;
  pressure_range_atm: Ranged | null;
  airflow_recorded: string;
  airflow_range_cm_s: Ranged | null;
  airflow_max_cm_s?: number | null;
  sensors_variables: string;
  outcomes: string;
  license: string;
  raw_data_availability: string;
  local_data_status: string;
  conditions_evidence: string;
  tags: string[];
  hardware_rack: string;
  fuel_phase: string;
  o2_range_pct: Ranged | null;
  pressure_range_psi: Ranged | null;
  airflow_range_cms: Ranged | null;
  gravity_regimes: string[];
  predictive_variables: string[];
  earth_spinoff: {
    title: string;
    nasa_origin: string;
    terrestrial_application: string;
    impact_metric: string;
  };
  historical_incident_links: string[];
  verification_status: string;
};

export type Run = {
  run_id: string;
  first_cycle: number;
  last_cycle: number;
  classified_cycles: number;
  phase_exceptions: number;
  mixed_band_cycles: number;
  duplicate_cycle_numbers: number;
};

export type Habitat = {
  id: string;
  name: string;
  o2_pct: number;
  pressure_psi: number;
  pressure_atm: number;
  po2_psi: number;
  airflow_range_cm_s: Ranged;
  gravity_g: number;
  gravity_regime: string;
  key_risk: string;
  rationale: string;
  evidence_status: string;
};

export type Scenario = {
  mission: string;
  gravity: string;
  gravity_g: number;
  oxygen_pct: number;
  pressure_psi: number;
  airflow_cms: number;
  material: string;
  pillar: string;
};

export type RankItem = Investigation & {
  match_score: number;
  evidence_coverage: number;
  ranking_factors: Factor[];
  physics_proximity?: {
    oxygen_overlap: number | null;
    pressure_overlap: number | null;
    airflow_overlap: number | null;
    mean_overlap: number | null;
    basis: string;
  };
};

export type GravityPoint = {
  gravity_g: number;
  moc_pct: number;
  buoyant_flow_cms: number;
  effective_velocity_cms: number;
  oxygen_supply_index: number;
  cooling_penalty_pct: number;
  gravity_enhancement_pct: number;
  flame_spread_rate_mms: number;
  regime: string;
};

export type EnvelopePoint = {
  pressure_psi: number;
  o2_pct: number;
  po2_psi: number;
  boundary_o2_pct: number;
  screening_side_of_boundary: string;
};

export type BoundaryPoint = { pressure_psi: number; boundary_o2_pct: number };

export type HabitatMarker = {
  id: string;
  label: string;
  o2_pct: number;
  pressure_psi: number;
  gravity_g: number;
  screening_side_of_boundary: string;
};

export type Simulation = {
  model: {
    name: string;
    version: string;
    validated: boolean;
    limitations: string;
    evidence_basis?: string[];
  };
  inputs: {
    o2_pct: number;
    pressure_psi: number;
    airflow_cms: number;
    gravity_g: number;
    fuel_type: string;
  };
  metrics: {
    po2_psi: number;
    earth_sea_level_po2_psi: number;
    normoxic_equivalent_o2_pct_at_14_7_psi: number;
    buoyant_velocity_cms: number;
    effective_velocity_cms: number;
    oxygen_supply_index: number;
    estimated_moc_pct: number;
    flammability_index: number;
    regime_classification: string;
    peak_hazard_gravity_g: number;
  };
  gravity_curve: GravityPoint[];
  o2_pressure_envelope: EnvelopePoint[];
  boundary_curve: BoundaryPoint[];
  habitat_markers: HabitatMarker[];
  partial_gravity_bounding: {
    bounding_anchors: { regime: string; gravity_g: number; evidence: string[] }[];
    hazard_peak: { gravity_g: number; moc_pct: number; flame_spread_rate_mms: number };
    hypothesis: string;
    status: string;
  };
  efield_equivalence: {
    available: boolean;
    method: string;
    target_gravity_g: number;
    equivalent_voltage_kv: number;
    electrode_gap_cm: number;
    estimated_equivalent_kv_cm: number;
    ion_velocity_match_cms: number;
    evidence_requirement: string;
  };
};

export type Spinoff = {
  psi_id: string;
  title: string;
  nasa_origin: string;
  terrestrial_application: string;
  impact_metric: string;
};

export type Synthesis = {
  selected_ids: string[];
  commonalities: {
    hardware_racks: string[];
    fuel_phases: string[];
    pillars: string[];
    shared_predictive_variables: string[];
    o2_envelope_intersection_pct: Ranged | null;
    pressure_envelope_intersection_psi: Ranged | null;
    airflow_envelope_intersection_cm_s: Ranged | null;
  }[];
  deltas: Record<string, unknown>[];
  sections: {
    prevention: string[];
    detection: string[];
    suppression: string[];
    partial_gravity: string[];
    earth_spinoffs: Spinoff[];
    historical_incidents: string[];
  };
  insights: { domain: string; statement: string; evidence_status: string }[];
  limitations: string[];
};

export type RepositoryScope = {
  title: string;
  total_investigations: number;
  deeply_indexed_count: number;
  associated_count: number;
  aggregate_telemetry_tb: number;
  aggregate_telemetry_label: string;
  summary: string;
  id_reconciliation: string;
  tier1: { psi_id: string; short_name: string; focus: string; depth: string }[];
  tier2: { key: string; name: string; focus: string; scope_status: string }[];
  upcoming_missions: { key: string; name: string; status: string; bounding: string }[];
  bounding_statement: string;
  limitations: string[];
};

export type SimResponse = {
  scenario: Record<string, unknown>;
  simulation: Simulation;
  ranked_investigations: RankItem[];
  synthesis: Synthesis;
  repository_scope?: RepositoryScope;
  interpretation: string;
};

export type CompareResponse = {
  psi_ids: string[];
  matrix: Record<string, unknown>[];
  deltas: Record<string, unknown>[];
  synthesis: Synthesis;
  interpretation: string;
};

export type PhaseSummary = {
  FirstCycle?: string;
  LastCycle?: string;
  ClassifiedCycles?: string;
  ExceptionCycles?: string;
  MixedBandCycles?: string;
  DuplicateCycleNumbers?: string;
  MissingCycleNumbers?: string;
  GapEvents?: string;
  Phase0CycleCount?: string;
  Phase1CycleCount?: string;
  Phase0DominantBand?: string;
  Phase1DominantBand?: string;
};

export type RunMetrics = {
  FirstEligibleCycle?: string;
  LastEligibleCycle?: string;
  MissingCycleNumbers?: string;
  GapEvents?: string;
  ExceptionBlocks?: string;
  ExceptionLengthMean?: string;
  ExceptionLengthMedian?: string;
  ExceptionLengthMin?: string;
  ExceptionLengthMax?: string;
  ExceptionLengthSD?: string;
  ExceptionRate?: string;
  EligibleCycleRecords?: string;
};

export type LagRow = { Lag?: string; ValidCyclePairs?: string; Autocorrelation?: string };
export type ModelRow = {
  ModelType?: string;
  Period?: string;
  MismatchWidth?: string;
  PhaseOffset?: string;
  Accuracy?: string;
  Precision?: string;
  Recall?: string;
  F1?: string;
  BaselineAccuracy?: string;
  EvaluationWindow?: string;
  Interpretation?: string;
};
export type BlockEvent = { EventType?: string; StartCycle?: string; EndCycle?: string; BlockLength?: string };

export type RunSummary = {
  phase_summary?: PhaseSummary;
  periodicity_metrics?: RunMetrics;
  exception_cycles?: number[];
  mixed_cycle_ids?: number[];
  lag_correlations?: LagRow[];
  candidate_models?: ModelRow[];
  block_events?: BlockEvent[];
  processing_status?: string;
  cycle_count?: number;
};

export type RunValidation = {
  run_id: string;
  status: string;
  raw_replay_performed: boolean;
  checks: Record<string, boolean | string>;
  processing_status: string;
};

export type AiTaskType =
  | "project_overview"
  | "catalogue_search"
  | "retrieve_documents"
  | "explain_terminology"
  | "explain_partial_gravity"
  | "interpret_simulation"
  | "explain_ml_predictions"
  | "compare_investigations"
  | "identify_evidence_gaps"
  | "generate_summary"
  | "generate_proposal"
  | "generate_report"
  | "qa_with_citations";

export type AiCitation = {
  chunk_id: string;
  psi_id: string | null;
  title: string;
  doi: string | null;
  source_path_or_url: string;
  relevance_score: number;
  excerpt: string;
  epistemic_tier: string;
};

export type AiResponse = {
  task_type: AiTaskType;
  answer_markdown: string;
  epistemic_breakdown: {
    verified_nasa_findings: string[];
    project_calculations: string[];
    scientific_hypotheses: string[];
    generated_suggestions: string[];
  };
  citations: AiCitation[];
  ollama_status: {
    online: boolean;
    selected_model: string | null;
    generation_mode: string;
    latency_ms: number;
    status_message: string;
  };
  safety_disclaimer: string;
  session_id?: string | null;
};

export type AiStatus = {
  online: boolean;
  base_url: string;
  available_models: string[];
  selected_model: string | null;
  recommended_models: {
    name: string;
    ram_requirement_gb: number | null;
    description: string;
    installed: boolean;
    installed_name: string | null;
    recommended: boolean;
    memory_available: boolean | null;
  }[];
  total_memory_gb: number | null;
  status_message: string;
  rag_index: {
    total_chunks: number;
    sources_covered: number;
    tier1_records_expected: number;
    tier2_scope_records_expected: number;
    archive_runs: number;
    embedding_status: string;
    corpus_policy: string;
  };
};

export type AiRetrievedChunk = AiCitation & {
  text: string;
  source_type: string;
  pillar: string;
};

export type MlMetricSet = {
  sample_count: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number | null;
  confusion_matrix: {
    labels: string[];
    matrix: number[][];
  };
  roc_curve: { false_positive_rate: number; true_positive_rate: number }[];
  calibration: {
    status: string;
    brier_score: number | null;
    expected_calibration_error: number | null;
    confidence_interpretation: string;
  };
};

export type MlFeatureImportance = {
  feature: string;
  label?: string;
  unit: string;
  importance: number;
  importance_basis?: string;
};

export type MlShapSummary = {
  feature: string;
  label: string;
  unit: string;
  mean_abs_shap: number;
  mean_shap: number;
  rank: number;
};

export type MlModel = {
  model_id: string;
  version: string;
  display_name: string;
  algorithm: string;
  dataset: string;
  dataset_id: string;
  target_name: string;
  target_interpretation: string;
  training_metadata: {
    training_performed: boolean;
    record_count: number;
    class_distribution: Record<string, number>;
    run_group_count: number;
    raw_feature_data_local_only: boolean;
    disclaimer: string;
  };
  validation_metrics: MlMetricSet;
  grouped_majority_baseline: MlMetricSet;
  accuracy_delta_vs_grouped_majority_baseline: number;
  grouped_evaluation: {
    method: string;
    group_column: string;
    run_ids: string[];
    leakage_check_passed: boolean;
    out_of_fold_prediction_count: number;
  };
  feature_importance: MlFeatureImportance[];
  explainability: {
    method: string;
    data_scope: string;
    global_feature_importance: MlFeatureImportance[];
    shap_summary: MlShapSummary[];
  };
  safety_disclaimer: string;
};

export type MlModelRegistry = {
  task_id: string;
  task_name: string;
  target_interpretation: string;
  training_performed: boolean;
  record_count: number;
  run_ids: string[];
  grouped_evaluation_method: string;
  runid_leakage_check_passed: boolean;
  model_artifacts_local_only: boolean;
  safety_disclaimer: string;
  models: MlModel[];
};

export type MlPrediction = {
  model_id: string;
  model_version: string;
  dataset_id: string;
  target_name: string;
  target_interpretation: string;
  prediction: {
    predicted_class: string;
    predicted_class_id: number;
    class_probabilities: Record<string, number>;
    confidence: number;
    confidence_pct: number;
    predictive_entropy_bits: number;
    uncertainty_interpretation: string;
    imputed_features: string[];
    target_interpretation: string;
    safety_disclaimer: string;
  };
  grouped_evaluation_method: string;
  runid_leakage_check_passed: boolean;
  safety_disclaimer: string;
};

export type TelemetryMode = "synthetic" | "replay" | "upload";
export type TelemetryScenario =
  | "nominal_operations"
  | "gradual_overheat"
  | "sudden_temperature_spike"
  | "abnormal_oxygen"
  | "airflow_failure"
  | "sensor_noise_spike"
  | "communication_interruption";
export type TelemetrySourceMode = "SYNTHETIC" | "REPLAY" | "REAL";
export type TelemetrySeverity = "CAUTION" | "CRITICAL";

export type TelemetryFrame = {
  frame_id: number;
  timestamp: string;
  O2_pct: number | null;
  PO2_psi: number | null;
  pressure_psi: number | null;
  temp_c: number | null;
  airflow_cms: number | null;
  smoke_mg_m3: number | null;
  gravity_g: number | null;
  sensor_noise_profile: string;
  source_mode: TelemetrySourceMode;
  scenario: TelemetryScenario | null;
  source_timestamp: string | null;
  source_elapsed_s: number | null;
  source_fields_available?: string[];
  source_measurements: Record<string, number | null>;
};

export type TelemetryAlert = {
  alert_id: string;
  timestamp: string;
  what_changed: string;
  trigger_variables: string[];
  severity: TelemetrySeverity;
  supporting_observations: string[];
  source_mode: TelemetrySourceMode;
};

export type TelemetrySnapshot = {
  mode: TelemetryMode | null;
  scenario: TelemetryScenario | null;
  run_id: string | null;
  status: "stopped" | "running" | "complete";
  data_label: string;
  sampling_interval_seconds: 1;
  latest_frame: TelemetryFrame | null;
  history: TelemetryFrame[];
  active_anomalies: TelemetryAlert[];
  source_metadata: {
    source: string | null;
    run_id?: string | null;
    source_columns?: string[];
    recorded_fields: string[];
    unavailable_fields: string[];
    interpretation: string;
  };
  units: Record<string, string>;
  safety_disclaimer: string;
};

export type DigitalTwinPoint = {
  time: number;
  temp_k: number | null;
  flame_volume: number | null;
  o2_pct: number;
  pressure_psi: number;
  airflow_cms: number;
  gravity_g: number;
};

export type DigitalTwinResponse = {
  model: {
    name: string;
    version: string;
    validated: boolean;
    calibrated: boolean;
    interpretation: string;
  };
  baseline_trajectory: DigitalTwinPoint[];
  intervention_trajectory: DigitalTwinPoint[];
  assumptions_and_uncertainty: string[];
  scientific_references: string[];
  safety_disclaimer: string;
};

export type DecisionRelevance = {
  psi_id: string;
  name: string;
  match_score: number;
  evidence_coverage: number;
  source_url: string;
  doi: string | null;
  local_data_status: string | null;
  interpretation: string;
};

export type ExecutiveResearchBrief = {
  summary: string;
  active_scenario_context: Record<string, unknown>;
  relevance_ranking: DecisionRelevance[];
  anomaly_analysis: {
    status: string;
    source_mode: string | null;
    alerts: TelemetryAlert[];
    alert_count: number;
    interpretation: string;
  };
  ml_insights: {
    status: string;
    prediction: Record<string, unknown> | null;
    validation_metrics: Record<string, unknown> | null;
    models: MlModel[];
    training_performed: boolean | null;
    runid_leakage_check_passed: boolean | null;
    model_id: string | null;
    provenance: string;
  };
  intervention_comparison: {
    status: string;
    baseline_trajectory: DigitalTwinPoint[];
    intervention_trajectory: DigitalTwinPoint[];
    assumptions_and_uncertainty?: string[];
    safety_disclaimer?: string | null;
    interpretation: string;
  };
  evidence_gaps: { psi_id: string | null; gap: string; source_url: string | null }[];
  supporting_citations: AiCitation[];
  epistemic_separation: {
    measured_data: Record<string, unknown>;
    calculated_surrogates: {
      catalogue_relevance: DecisionRelevance[];
      physics: {
        status: string;
        validated?: boolean;
        estimated_moc_pct?: number;
        flammability_index?: number;
        regime_classification?: string;
        interpretation: string;
      } | null;
      interpretation: string;
    };
    generated_llm_suggestions: { status: string; items: string[]; reason: string };
  };
  integration_warnings: string[];
  safety_disclaimer: string;
};

export type AiWorkspaceMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: AiResponse;
  createdAt: string;
};

export type TabId = "simulator" | "matrix" | "synthesis" | "samer" | "executive" | "ai" | "ml" | "telemetry" | "digital-twin" | "decision-support";

export const TABS: { id: TabId; label: string; short: string }[] = [
  { id: "simulator", label: "Mission & Habitat Simulator", short: "SIM" },
  { id: "matrix", label: "Catalogue & Comparison Matrix", short: "CAT" },
  { id: "synthesis", label: "SI Fire-Safety Synthesis", short: "SYN" },
  { id: "samer", label: "PSI-101 SAME-R Telemetry & Lineage", short: "SAME-R" },
  { id: "executive", label: "All-in-One Executive View", short: "EXEC" },
  { id: "ai", label: "AI · SCIENTIFIC RESEARCH ASSISTANT", short: "AI" },
  { id: "ml", label: "ML · FIRE RESEARCH LAB", short: "ML" },
  { id: "telemetry", label: "VIRTUAL SPACECRAFT MONITORING", short: "TELEMETRY" },
  { id: "digital-twin", label: "FIRE SUPPRESSION DIGITAL TWIN", short: "TWIN" },
  { id: "decision-support", label: "SCIENTIFIC DECISION SUPPORT", short: "DECISION" },
];

export const DEFAULT_COMPARE_IDS = ["PSI-25", "PSI-20", "PSI-22", "PSI-69"];

export const PRESET_MATERIAL: Record<string, string> = {
  iss_usos: "Pyrell",
  artemis_lunar_base: "Sibal cotton fiberglass",
  mars_transit_habitat: "PMMA",
  eva_spacesuit: "Nomex",
  high_o2_testbed: "Methane",
};

export const PRESET_PILLAR: Record<string, string> = {
  iss_usos: "Detection",
  artemis_lunar_base: "Prevention",
  mars_transit_habitat: "Prevention",
  eva_spacesuit: "Prevention",
  high_o2_testbed: "Prevention",
};

export const HABITAT_COLORS: Record<string, string> = {
  iss_usos: "#22d3ee",
  artemis_lunar_base: "#f59e0b",
  mars_transit_habitat: "#a78bfa",
  eva_spacesuit: "#ef4444",
  high_o2_testbed: "#f97316",
  user_scenario: "#10b981",
};

export const HABITAT_SHORT: Record<string, string> = {
  iss_usos: "ISS",
  artemis_lunar_base: "ARTEMIS",
  mars_transit_habitat: "MARS",
  eva_spacesuit: "EVA",
  high_o2_testbed: "CFI-G 85%",
  user_scenario: "ACTIVE",
};

export const FACTOR_COLORS: Record<string, string> = {
  "Research pillar": "#06b6d4",
  "Material / fuel": "#a78bfa",
  "Oxygen concentration": "#10b981",
  Pressure: "#f59e0b",
  Airflow: "#38bdf8",
  "Gravity regime": "#f97316",
};

export const INCIDENT_NOTES: Record<string, string> = {
  Apollo: "1967 · 100% O₂ at 16.7 psi. Velcro-and-plug-door configuration turned a ground test into a fatal oxygen-fed fire.",
  Mir: "1997 · Vika/TGK lithium-perchlorate oxygen generator fire aboard Mir; the crew fought it in smoke with hand-held extinguishers.",
  Artemis: "Nuisance smoke-alarm telemetry. The operational case for discriminating pyrolysis smoke from cabin and lunar dust.",
};

export function fmt(value: number | null | undefined, digits = 2): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—";
}

export function asText(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return value.map((item) => asText(item)).join(", ");
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (typeof record.title === "string") return record.title;
    return Object.entries(record)
      .map(([key, item]) => `${key}: ${asText(item)}`)
      .join(" · ");
  }
  return String(value);
}

export function rangeText(value: unknown, unit = ""): string {
  if (!Array.isArray(value) || value.length !== 2) return "—";
  const low = Number(value[0]);
  const high = Number(value[1]);
  if (!Number.isFinite(low) || !Number.isFinite(high)) return "—";
  return low === high ? `${low}${unit}` : `${low}–${high}${unit}`;
}

export function gravityName(g: number, fallback = "Unknown"): string {
  if (g <= 0.001) return "Microgravity";
  if (Math.abs(g - 0.166) < 0.01) return "Lunar partial gravity";
  if (Math.abs(g - 0.376) < 0.01) return "Mars partial gravity";
  if (Math.abs(g - 1) < 0.01) return "Earth gravity";
  return fallback;
}

export function gravityValue(label: string): number {
  if (label === "Microgravity") return 0;
  if (label === "Lunar partial gravity") return 0.166;
  if (label === "Mars partial gravity") return 0.376;
  if (label === "Earth gravity") return 1;
  return 0;
}

export function scenarioFromHabitat(h: Habitat): Scenario {
  const [low, high] = h.airflow_range_cm_s ?? [10, 10];
  return {
    mission: h.name,
    gravity: gravityName(h.gravity_g, h.gravity_regime),
    gravity_g: h.gravity_g,
    oxygen_pct: h.o2_pct,
    pressure_psi: h.pressure_psi,
    airflow_cms: Math.round(((low + high) / 2) * 10) / 10,
    material: PRESET_MATERIAL[h.id] ?? "Pyrell",
    pillar: PRESET_PILLAR[h.id] ?? "Prevention",
  };
}

export function reportScenario(s: Scenario, habitatId = "") {
  return {
    mission: s.mission,
    gravity: s.gravity,
    gravity_g: s.gravity_g,
    oxygen_pct: s.oxygen_pct,
    pressure_atm: Math.round((s.pressure_psi / 14.7) * 10000) / 10000,
    airflow_cm_s: s.airflow_cms,
    material: s.material,
    pillar: s.pillar,
    habitat_id: habitatId,
  };
}

export function clamp(value: number, low: number, high: number): number {
  return Math.max(low, Math.min(high, value));
}

export function scale(value: number, domainMin: number, domainMax: number, outMin: number, outMax: number): number {
  if (domainMax === domainMin) return outMin;
  return outMin + ((clamp(value, domainMin, domainMax) - domainMin) / (domainMax - domainMin)) * (outMax - outMin);
}
