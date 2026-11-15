"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  AiCitation,
  AiResponse,
  AiRetrievedChunk,
  AiStatus,
  AiTaskType,
  AiWorkspaceMessage,
  Investigation,
  Scenario,
  SimResponse,
} from "./model";

type Props = {
  catalogue: Investigation[];
  scenario: Scenario;
  simulation: SimResponse | null;
  compareIds: string[];
};

type ApiError = { detail?: string | { msg?: string }[] };

const TASK_OPTIONS: { id: AiTaskType; label: string }[] = [
  { id: "project_overview", label: "Project overview" },
  { id: "catalogue_search", label: "Catalogue search" },
  { id: "retrieve_documents", label: "Retrieve documents" },
  { id: "explain_terminology", label: "Explain terminology" },
  { id: "explain_partial_gravity", label: "Explain partial gravity" },
  { id: "interpret_simulation", label: "Interpret simulation" },
  { id: "explain_ml_predictions", label: "Explain ML status" },
  { id: "compare_investigations", label: "Compare investigations" },
  { id: "identify_evidence_gaps", label: "Identify evidence gaps" },
  { id: "generate_summary", label: "Generate summary" },
  { id: "generate_proposal", label: "Generate proposal" },
  { id: "generate_report", label: "Generate report" },
  { id: "qa_with_citations", label: "Research Q&A with citations" },
];

const LOCAL_HISTORY_KEY = "firelytics-ai-research-history-v1";
const SESSION_KEY = "firelytics-ai-research-session-v1";

function presentEngineStatus(value: string): string {
  return value.replace(/ollama/gi, "AI engine").replace(/locally/gi, "within this project").replace(/local/gi, "project");
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/backend/${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      ...(init?.headers ?? {}),
      ...(init?.body ? { "content-type": "application/json" } : {}),
    },
  });
  if (!response.ok) {
    const info = await response.json().catch(() => ({})) as ApiError;
    const detail = Array.isArray(info.detail)
      ? info.detail.map((item) => item.msg ?? "Invalid input").join("; ")
      : info.detail;
    throw new Error(typeof detail === "string" ? detail : `Research request failed (${response.status}).`);
  }
  if (!response.headers.get("content-type")?.includes("application/json")) {
    throw new Error("The research endpoint returned an unexpected response format.");
  }
  return await response.json() as T;
}

function newId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function CitationCard({ citation }: { citation: AiCitation }) {
  const hasDoi = typeof citation.doi === "string" && citation.doi.startsWith("10.");
  return (
    <article className="ai-citation">
      <div className="ai-citation-head">
        <span className="ai-citation-psi">{citation.psi_id ?? "PROJECT DOC"}</span>
        <span className="ai-score">{Math.round(citation.relevance_score * 100)}% match</span>
      </div>
      <h4>{presentEngineStatus(citation.title)}</h4>
      <div className="ai-citation-meta">
        {hasDoi ? (
          <a href={`https://doi.org/${citation.doi}`} target="_blank" rel="noreferrer">Verified DOI ↗</a>
        ) : citation.doi === "psi_record_verified_doi_pending" ? (
          <span>Verified DOI pending</span>
        ) : (
          <span>No DOI stated</span>
        )}
        <span className="ai-tier">{citation.epistemic_tier.replace(/_/g, " ")}</span>
      </div>
      <p>{presentEngineStatus(citation.excerpt)}</p>
      {citation.source_path_or_url.startsWith("https://") ? (
        <a className="ai-source-link" href={citation.source_path_or_url} target="_blank" rel="noreferrer">
          Open source ↗
        </a>
      ) : (
        <span className="ai-source-path">{citation.source_path_or_url}</span>
      )}
    </article>
  );
}

function EpistemicInspector({ response }: { response: AiResponse }) {
  const cards: { key: keyof AiResponse["epistemic_breakdown"]; title: string }[] = [
    { key: "verified_nasa_findings", title: "Verified NASA Findings" },
    { key: "project_calculations", title: "Project Calculations" },
    { key: "scientific_hypotheses", title: "Scientific Hypotheses" },
    { key: "generated_suggestions", title: "Generated Suggestions · Human Review Required" },
  ];
  return (
    <div className="ai-epistemic-grid">
      {cards.map(({ key, title }) => (
        <section className="ai-epistemic-card" key={key}>
          <h4>{title}</h4>
          {response.epistemic_breakdown[key].length ? (
            <ul>{response.epistemic_breakdown[key].map((item, index) => <li key={`${key}-${index}`}>{item}</li>)}</ul>
          ) : <p>No claims in this category were returned.</p>}
        </section>
      ))}
    </div>
  );
}

export function AiResearchAssistant({ catalogue, scenario, simulation, compareIds }: Props) {
  const [status, setStatus] = useState<AiStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [statusError, setStatusError] = useState("");
  const [selectedModel, setSelectedModel] = useState("qwen3:4b");
  const [taskType, setTaskType] = useState<AiTaskType>("qa_with_citations");
  const [pillarFilter, setPillarFilter] = useState("");
  const [psiFilter, setPsiFilter] = useState("");
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<AiWorkspaceMessage[]>([]);
  const [sessionId, setSessionId] = useState("");
  const [historyReady, setHistoryReady] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [chatError, setChatError] = useState("");
  const [retrievalQuery, setRetrievalQuery] = useState("");
  const [retrieved, setRetrieved] = useState<AiRetrievedChunk[]>([]);
  const [retrievalBusy, setRetrievalBusy] = useState(false);
  const [retrievalError, setRetrievalError] = useState("");

  const refreshStatus = useCallback(async () => {
    setStatusLoading(true);
    setStatusError("");
    try {
      const current = await requestJson<AiStatus>("ai/status");
      setStatus(current);
      setSelectedModel(current.selected_model ?? "qwen3:4b");
    } catch (error) {
      setStatusError((error as Error).message);
    } finally {
      setStatusLoading(false);
    }
  }, []);

  useEffect(() => { void refreshStatus(); }, [refreshStatus]);

  useEffect(() => {
    const storedSession = localStorage.getItem(SESSION_KEY) || newId();
    localStorage.setItem(SESSION_KEY, storedSession);
    setSessionId(storedSession);

    let localMessages: AiWorkspaceMessage[] = [];
    try {
      const raw = localStorage.getItem(LOCAL_HISTORY_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as unknown;
        if (Array.isArray(parsed)) {
          localMessages = parsed.filter((item): item is AiWorkspaceMessage => {
            if (!item || typeof item !== "object") return false;
            const record = item as Record<string, unknown>;
            return typeof record.id === "string"
              && (record.role === "user" || record.role === "assistant")
              && typeof record.content === "string"
              && typeof record.createdAt === "string";
          }).slice(-60);
        }
      }
    } catch {
      localMessages = [];
    }
    setMessages(localMessages);

    let active = true;
    requestJson<{ messages: { role: "user" | "assistant"; content: string; created_at?: string }[] }>(
      `ai/history?session_id=${encodeURIComponent(storedSession)}`,
    ).then((history) => {
      if (active && localMessages.length === 0 && history.messages.length) {
        setMessages(history.messages.map((item) => ({
          id: newId(),
          role: item.role,
          content: item.content,
          createdAt: item.created_at ?? new Date().toISOString(),
        })));
      }
    }).catch((error) => {
      if (active) setHistoryError((error as Error).message);
    }).finally(() => {
      if (active) setHistoryReady(true);
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!historyReady) return;
    localStorage.setItem(LOCAL_HISTORY_KEY, JSON.stringify(messages.slice(-60)));
  }, [historyReady, messages]);

  const installedModelOptions = useMemo(() => {
    const options = new Set(["qwen3:4b", "qwen3:8b", "qwen2.5:3b", "qwen2.5:7b", "llama3.2:3b", "mistral:7b"]);
    for (const model of status?.available_models ?? []) options.add(model);
    return [...options];
  }, [status]);

  const scenarioContext = useMemo(() => ({
    scenario,
    simulation_inputs: simulation?.simulation.inputs ?? null,
    simulation_outputs: simulation?.simulation ?? null,
    simulation_interpretation: simulation?.interpretation ?? null,
  }), [scenario, simulation]);

  const appendResponse = useCallback((question: string, response: AiResponse) => {
    const createdAt = new Date().toISOString();
    const userMessage: AiWorkspaceMessage = { id: newId(), role: "user", content: question, createdAt };
    const assistantMessage: AiWorkspaceMessage = {
      id: newId(),
      role: "assistant",
      content: response.answer_markdown,
      response,
      createdAt,
    };
    setMessages((current) => [...current, userMessage, assistantMessage].slice(-60));
  }, []);

  const submitTask = useCallback(async (
    message: string,
    selectedTask: AiTaskType,
    endpoint = "ai/chat",
    extra: Record<string, unknown> = {},
  ) => {
    if (chatBusy || !sessionId) return;
    setChatBusy(true);
    setChatError("");
    try {
      const history = messages.slice(-8).map(({ role, content }) => ({ role, content }));
      const body = endpoint === "ai/chat"
        ? {
          message,
          task_type: selectedTask,
          model: selectedModel || undefined,
          scenario_context: scenarioContext,
          psi_ids: psiFilter ? [psiFilter] : undefined,
          pillar: pillarFilter || undefined,
          history,
          session_id: sessionId,
          ...extra,
        }
        : { ...extra, message, model: selectedModel || undefined, session_id: sessionId };
      const response = await requestJson<AiResponse>(endpoint, { method: "POST", body: JSON.stringify(body) });
      appendResponse(message, response);
    } catch (error) {
      setChatError((error as Error).message);
    } finally {
      setChatBusy(false);
    }
  }, [appendResponse, chatBusy, messages, pillarFilter, psiFilter, scenarioContext, selectedModel, sessionId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();
    if (!message) return;
    setDraft("");
    await submitTask(message, taskType);
  }

  async function searchCorpus(query = retrievalQuery) {
    const cleaned = query.trim();
    if (!cleaned) {
      setRetrievalError("Enter a query to search the approved evidence corpus.");
      return;
    }
    setRetrievalBusy(true);
    setRetrievalError("");
    try {
      const result = await requestJson<{ items: AiRetrievedChunk[] }>("ai/retrieve", {
        method: "POST",
        body: JSON.stringify({
          query: cleaned,
          top_k: 5,
          psi_ids: psiFilter ? [psiFilter] : undefined,
          pillar: pillarFilter || undefined,
        }),
      });
      setRetrieved(result.items);
    } catch (error) {
      setRetrievalError((error as Error).message);
    } finally {
      setRetrievalBusy(false);
    }
  }

  async function quickAction(action: "simulation" | "gaps" | "compare" | "proposal" | "report" | "search") {
    if (action === "simulation") {
      if (!simulation) return;
      const message = "Explain the active simulator result, its inputs, and its limitations.";
      await submitTask(message, "interpret_simulation", "ai/explain-simulation", {
        simulation_inputs: simulation.simulation.inputs,
        simulation_outputs: simulation.simulation,
        scenario_context: { scenario },
      });
      return;
    }
    if (action === "gaps") {
      await submitTask(
        "Identify partial-gravity evidence gaps for the 0.166g Lunar case. Distinguish direct measurements from the PSI-22 analogue and state what remains unmeasured.",
        "identify_evidence_gaps",
      );
      return;
    }
    if (action === "compare") {
      const ids = compareIds.length ? compareIds : ["PSI-25", "PSI-20"];
      await submitTask(
        `Compare selected investigations ${ids.join(", ")} using only retrieved record fields.`,
        "compare_investigations",
        "ai/chat",
        { psi_ids: ids },
      );
      return;
    }
    if (action === "proposal" || action === "report") {
      const reportType = action === "proposal" ? "proposal" : "report";
      const ids = compareIds.length ? compareIds : ["PSI-22", "PSI-20", "PSI-25"];
      const message = action === "proposal"
        ? "Draft a non-operational lunar partial-gravity combustion experiment proposal. Identify evidence needs and human-review gates."
        : "Generate a structured research report for the active scenario and selected investigations.";
      await submitTask(message, action === "proposal" ? "generate_proposal" : "generate_report", "ai/generate-report", {
        report_type: reportType,
        scenario_context: scenarioContext,
        selected_psi_ids: ids,
      });
      return;
    }
    await searchCorpus(retrievalQuery || draft || "NASA PSI fire safety research");
  }

  async function clearHistory() {
    setMessages([]);
    localStorage.removeItem(LOCAL_HISTORY_KEY);
    setHistoryError("");
    if (!sessionId) return;
    try {
      await requestJson(`ai/history?session_id=${encodeURIComponent(sessionId)}`, { method: "DELETE" });
    } catch (error) {
      setHistoryError((error as Error).message);
    }
  }

  const statusLabel = status?.online
    ? "AI ENGINE ONLINE · RESEARCH MODE"
    : "AI ENGINE OFFLINE · CITED RETRIEVAL AVAILABLE";

  return (
    <section className="ai-workspace">
      <div className="ai-workspace-heading">
        <div>
          <p className="eyebrow">AI ASSISTANT · EVIDENCE-GROUNDED RESEARCH</p>
          <h1>AI Scientific Research Assistant</h1>
          <p>Explore approved NASA PSI metadata and project evidence. LLM explanations never replace measurements or calculations.</p>
        </div>
      </div>

      <section className="ai-status-panel" aria-label="AI engine and corpus status">
        <div className={`ai-status-badge ${status?.online ? "online" : "offline"}`} role="status">
          <span aria-hidden="true" />
          {status ? statusLabel : "CHECKING AI ENGINE"}
        </div>
        <label className="ai-model-control">
          <span>Model</span>
          <select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)} aria-label="Select AI model">
            {installedModelOptions.map((model) => {
              const recommendation = status?.recommended_models.find((item) => item.name === model);
              const label = model === "qwen3:4b"
                ? "qwen3:4b (Recommended · ~3.5GB RAM)"
                : model === "qwen3:8b"
                  ? "qwen3:8b (~6.0GB RAM)"
                  : recommendation
                    ? `${model} (~${recommendation.ram_requirement_gb ?? "?"}GB RAM)`
                    : `${model}${status?.available_models.includes(model) ? " · installed" : ""}`;
              return <option key={model} value={model}>{label}</option>;
            })}
          </select>
        </label>
        <button className="button ghost ai-recheck" type="button" onClick={() => void refreshStatus()} disabled={statusLoading}>
          {statusLoading ? "Checking…" : "Recheck AI engine"}
        </button>
        <div className="ai-corpus-badge">
          <b>Indexed Chunks: {status?.rag_index.total_chunks ?? "—"}</b>
          <span>14 Tier-1 PSI Records + SAME-R Archive + Methodology Docs</span>
        </div>
      </section>
      {(statusError || historyError) && <div className="error" role="alert">{presentEngineStatus(statusError || historyError)}</div>}
      {status?.rag_index.embedding_status && <p className="ai-index-note">{status.rag_index.embedding_status}</p>}

      <section className="ai-quick-actions" aria-label="Research quick actions">
        <div className="ai-section-heading">
          <div><p className="eyebrow">RESEARCH SHORTCUTS</p><h2>Start with a bounded question</h2></div>
          <span className="pill">NO CONTROL COMMANDS</span>
        </div>
        <div className="ai-action-grid">
          <button type="button" className="button ghost" onClick={() => void quickAction("simulation")} disabled={!simulation || chatBusy}>Explain Active Simulation Result</button>
          <button type="button" className="button ghost" onClick={() => void quickAction("gaps")} disabled={chatBusy}>Identify Partial-Gravity Evidence Gaps</button>
          <button type="button" className="button ghost" onClick={() => void quickAction("compare")} disabled={chatBusy}>Compare Selected Investigations</button>
          <button type="button" className="button ghost" onClick={() => void quickAction("proposal")} disabled={chatBusy}>Generate Lunar Experiment Proposal</button>
          <button type="button" className="button ghost" onClick={() => void quickAction("report")} disabled={chatBusy}>Generate Structured Research Report</button>
          <button type="button" className="button ghost" onClick={() => void quickAction("search")} disabled={retrievalBusy}>Search NASA PSI Corpus</button>
        </div>
      </section>

      <div className="ai-main-grid">
        <section className="ai-chat-panel">
          <div className="ai-section-heading">
            <div><p className="eyebrow">SCIENTIFIC CHAT</p><h2>Ask from the evidence</h2></div>
            <button type="button" className="button ghost ai-clear-button" onClick={() => void clearHistory()}>Clear History</button>
          </div>
          <div className="ai-chat-controls">
            <label>
              <span>Task mode</span>
              <select value={taskType} onChange={(event) => setTaskType(event.target.value as AiTaskType)}>
                {TASK_OPTIONS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              </select>
            </label>
            <label>
              <span>Pillar filter</span>
              <select value={pillarFilter} onChange={(event) => setPillarFilter(event.target.value)}>
                <option value="">All pillars</option>
                {["Prevention", "Detection", "Suppression", "Partial-Gravity", "Methodology"].map((item) => <option key={item}>{item}</option>)}
              </select>
            </label>
            <label>
              <span>PSI filter</span>
              <select value={psiFilter} onChange={(event) => setPsiFilter(event.target.value)}>
                <option value="">All records</option>
                {catalogue.map((item) => <option key={item.psi_id} value={item.psi_id}>{item.psi_id} · {item.short_name}</option>)}
              </select>
            </label>
          </div>

          <div className="ai-message-list" aria-live="polite">
            {!messages.length && (
              <div className="ai-welcome">
                <b>Evidence first. Unknowns stay unknown.</b>
                <p>Responses separate NASA record metadata, project calculations, hypotheses, and human-reviewed suggestions. Cited retrieval remains available when the AI engine is offline.</p>
              </div>
            )}
            {messages.map((item) => (
              <article className={`ai-message ${item.role}`} key={item.id}>
                <div className="ai-message-role">{item.role === "user" ? "RESEARCH QUESTION" : "RESEARCH ASSISTANT"}</div>
                <div className="ai-answer-text">{presentEngineStatus(item.content)}</div>
                {item.response && (
                  <>
                    <div className="ai-generation-meta">
                      <span>{presentEngineStatus(item.response.ollama_status.generation_mode.replace(/_/g, " "))}</span>
                      <span>{item.response.ollama_status.online ? "AI engine online" : "AI engine offline"}</span>
                      {item.response.ollama_status.selected_model && <span>{item.response.ollama_status.selected_model}</span>}
                    </div>
                    <EpistemicInspector response={item.response} />
                    <div className="ai-citations">
                      <h3>Retrieved source citations</h3>
                      {item.response.citations.length
                        ? item.response.citations.map((citation) => <CitationCard citation={citation} key={citation.chunk_id} />)
                        : <p>No source matched this question.</p>}
                    </div>
                  </>
                )}
              </article>
            ))}
            {chatBusy && <div className="ai-loading" role="status">Retrieving evidence and preparing a bounded response…</div>}
          </div>
          {chatError && <div className="error" role="alert">{presentEngineStatus(chatError)}</div>}
          <form className="ai-chat-form" onSubmit={(event) => void handleSubmit(event)}>
            <label className="sr-only" htmlFor="ai-chat-input">Research question</label>
            <textarea
              id="ai-chat-input"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask a source-grounded question about NASA PSI records or the active scenario…"
              maxLength={4000}
              rows={3}
              disabled={chatBusy}
            />
            <div className="ai-chat-form-footer">
              <span>Cited evidence retrieval remains available when the AI engine is offline.</span>
              <button className="button primary" type="submit" disabled={chatBusy || !draft.trim()}>
                {chatBusy ? "Researching…" : "Ask Research Assistant"}
              </button>
            </div>
          </form>
        </section>

        <aside className="ai-retriever-panel">
          <div className="ai-section-heading">
            <div><p className="eyebrow">DIRECT DOCUMENT RETRIEVER</p><h2>Inspect the corpus</h2></div>
          </div>
          <form className="ai-retriever-form" onSubmit={(event) => { event.preventDefault(); void searchCorpus(); }}>
            <label className="sr-only" htmlFor="ai-retrieval-query">Search query</label>
            <input
              id="ai-retrieval-query"
              value={retrievalQuery}
              onChange={(event) => setRetrievalQuery(event.target.value)}
              placeholder="e.g. FLEX cool flames or lunar E-FIELD"
              maxLength={2000}
            />
            <button type="submit" className="button primary" disabled={retrievalBusy}>{retrievalBusy ? "Searching…" : "Retrieve"}</button>
          </form>
          {retrievalError && <div className="error" role="alert">{presentEngineStatus(retrievalError)}</div>}
          <div className="ai-retrieved-list" aria-live="polite">
            {retrieved.length ? retrieved.map((item) => (
              <article className="ai-retrieved-chunk" key={item.chunk_id}>
                <div className="ai-citation-head"><span className="ai-citation-psi">{item.psi_id ?? "PROJECT DOC"}</span><span className="ai-score">{Math.round(item.relevance_score * 100)}%</span></div>
                <h3>{presentEngineStatus(item.title)}</h3>
                <p>{presentEngineStatus(item.excerpt)}</p>
                <span className="ai-tier">{item.epistemic_tier.replace(/_/g, " ")}</span>
              </article>
            )) : <p className="ai-empty-state">Retrieved chunks and exact source excerpts will appear here.</p>}
          </div>
        </aside>
      </div>
      <p className="ai-safety-note">{status ? presentEngineStatus(status.status_message) : "AI engine status has not been checked."} {status ? `· ${status.rag_index.sources_covered} approved source groups indexed.` : ""}</p>
    </section>
  );
}
