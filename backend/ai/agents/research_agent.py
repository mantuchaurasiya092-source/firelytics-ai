from __future__ import annotations

import re
from typing import Any

from ai.ollama.client import OllamaClient, OllamaUnavailable
from ai.prompts.templates import SYSTEM_PROMPT, build_user_prompt
from ai.rag.chunker import DocumentChunk
from ai.rag.indexer import get_index
from ai.retrieval.retriever import RetrievedChunk, Retriever
from ai.schemas import TaskType


CAPABILITIES: dict[str, str] = {
    "project_overview": "Explain the project architecture, evidence scope, and scientific guardrails.",
    "catalogue_search": "Search NASA PSI catalogue metadata for investigations and documented conditions.",
    "retrieve_documents": "Retrieve relevant approved project and NASA PSI metadata sources.",
    "explain_terminology": "Explain combustion and aerosol terminology using the approved corpus.",
    "explain_partial_gravity": "Explain the bounded partial-gravity evidence and identify missing measurements.",
    "interpret_simulation": "Explain supplied screening outputs without recomputing or validating them.",
    "explain_ml_predictions": "Explain the current model/evaluation status without presenting heuristics as ML.",
    "compare_investigations": "Compare investigations only on retrieved, provenance-linked information.",
    "identify_evidence_gaps": "Identify missing evidence and limitations in the retrieved sources.",
    "generate_summary": "Generate a source-linked technical summary.",
    "generate_proposal": "Draft an exploratory experiment proposal requiring human review.",
    "generate_report": "Generate a structured evidence report with limitations and citations.",
    "qa_with_citations": "Answer a scientific question using the retrieved evidence.",
}

TASK_INSTRUCTIONS: dict[str, str] = {
    "project_overview": "Describe the local application and distinguish current features from planned work.",
    "catalogue_search": "Report matching catalogue metadata and clearly distinguish scope from tested conditions.",
    "retrieve_documents": "Summarize only the retrieved document excerpts and source provenance.",
    "explain_terminology": "Explain the requested term; state when its definition is not present in the retrieved corpus.",
    "explain_partial_gravity": "Separate measured 0g evidence, project screening calculations, and unvalidated hypotheses.",
    "interpret_simulation": "Interpret only the supplied simulator values; do not change, recompute, or validate them.",
    "explain_ml_predictions": "State whether a trained model is present and distinguish exploratory artifacts from inference.",
    "compare_investigations": "Compare only fields explicitly present in retrieved records; preserve unknowns.",
    "identify_evidence_gaps": "List missing measurements or source records without inferring their values.",
    "generate_summary": "Provide a concise technical summary with source-backed claims.",
    "generate_proposal": "Draft a non-operational research proposal; label every novel recommendation as requiring human review.",
    "generate_report": "Use sections: Scope, Evidence, Project Calculations, Hypotheses, Gaps, Suggestions, Limitations.",
    "qa_with_citations": "Answer the question and explicitly state any evidence limitation.",
}
TASK_RETRIEVAL_CONTEXT: dict[str, str] = {
    "project_overview": "FIRELYTICS architecture methodology validation",
    "explain_partial_gravity": "NASA PSI-22 E-FIELD 0.166g lunar partial gravity evidence gap",
    "interpret_simulation": "NASA PSI-22 E-FIELD NASA PSI-25 BASS-II PSI-20 ACME-BRE screening calculation",
    "explain_ml_predictions": "candidate models lag correlation trained machine learning status",
    "identify_evidence_gaps": "NASA PSI-22 E-FIELD LUCI FM2 direct lunar measurement evidence gap",
}

SAFETY_DISCLAIMER = (
    "Research support only. Interpretations require human scientific review; this platform is not "
    "NASA-approved or flight-certified and does not issue spacecraft-control or fire-suppression commands."
)
DOI_PATTERN = re.compile(r"(?:https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/[A-Za-z0-9._;()/:+-]+)", re.IGNORECASE)
PSI_CITATION_PATTERN = re.compile(r"\[(PSI-\d+)\]", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"(?<![\w.])[-+]?\d+(?:\.\d+)?(?![\w])")


class ResearchAgent:
    def __init__(self, client: OllamaClient | None = None, retriever: Retriever | None = None) -> None:
        self.client = client or OllamaClient()
        self.retriever = retriever or Retriever(get_index())

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        psi_ids: list[str] | None = None,
        pillar: str | None = None,
        epistemic_tier: str | None = None,
    ) -> list[RetrievedChunk]:
        return self.retriever.retrieve(query, top_k, psi_ids, pillar, epistemic_tier)

    @staticmethod
    def _citation_marker(chunk: DocumentChunk) -> str:
        return f"[{chunk.psi_id}]" if chunk.psi_id else "[Doc]"

    @staticmethod
    def _safe_llm_citations(
        answer: str,
        retrieved: list[RetrievedChunk],
        message: str,
        scenario_context: dict[str, Any] | None,
    ) -> str:
        known_psi = {item.chunk.psi_id.upper() for item in retrieved if item.chunk.psi_id}
        known_dois = {item.chunk.doi.lower() for item in retrieved if item.chunk.doi and item.chunk.doi.startswith("10.")}
        evidence_text = " ".join(
            [message, str(scenario_context or "")]
            + [item.chunk.text for item in retrieved]
            + [item.chunk.doi for item in retrieved if item.chunk.doi and item.chunk.doi.startswith("10.")]
        )
        known_numbers = {
            ResearchAgent._normalize_number(match.group(0))
            for match in NUMBER_PATTERN.finditer(evidence_text)
        }

        def replace_psi(match: re.Match[str]) -> str:
            return match.group(0) if match.group(1).upper() in known_psi else "[unsupported citation removed]"

        answer = PSI_CITATION_PATTERN.sub(replace_psi, answer)

        def replace_doi(match: re.Match[str]) -> str:
            doi = match.group(1).rstrip(".,;:)")
            if doi.lower() in known_dois:
                return match.group(0)
            return "[unverified DOI removed]"

        answer = DOI_PATTERN.sub(replace_doi, answer)

        def replace_number(match: re.Match[str]) -> str:
            line_start = answer.rfind("\n", 0, match.start()) + 1
            prefix = answer[line_start:match.start()]
            if not prefix.strip() and re.match(r"\.\s", answer[match.end():]):
                return match.group(0)
            if ResearchAgent._normalize_number(match.group(0)) in known_numbers:
                return match.group(0)
            return "[unverified value removed]"

        return NUMBER_PATTERN.sub(replace_number, answer)

    @staticmethod
    def _normalize_number(value: str) -> str:
        try:
            return format(float(value), ".12g")
        except ValueError:
            return value

    @staticmethod
    def _breakdown(
        retrieved: list[RetrievedChunk],
        scenario_context: dict[str, Any] | None,
        task_type: str,
    ) -> dict[str, list[str]]:
        breakdown: dict[str, list[str]] = {
            "verified_nasa_findings": [],
            "project_calculations": [],
            "scientific_hypotheses": [],
            "generated_suggestions": [],
        }
        category = {
            "verified_nasa_finding": "verified_nasa_findings",
            "project_calculation": "project_calculations",
            "scientific_hypothesis": "scientific_hypotheses",
            "generated_suggestion": "generated_suggestions",
        }
        for item in retrieved:
            target = category[item.chunk.epistemic_tier]
            statement = f"{item.chunk.source_title}: {item.chunk.text[:360].strip()}"
            if statement not in breakdown[target]:
                breakdown[target].append(statement)

        if scenario_context:
            simulation = scenario_context.get("simulation_outputs") or scenario_context.get("simulation")
            if isinstance(simulation, dict):
                metrics = simulation.get("metrics") if isinstance(simulation.get("metrics"), dict) else simulation
                breakdown["project_calculations"].append(
                    f"Supplied existing simulator output (not recomputed): {metrics}"
                )
        if task_type in {"generate_proposal", "generate_report"}:
            breakdown["generated_suggestions"].append(
                "Any proposed next step requires human scientific review and primary-source verification."
            )
        return breakdown

    def _offline_answer(
        self,
        message: str,
        task_type: str,
        retrieved: list[RetrievedChunk],
        status_message: str,
    ) -> str:
        if not retrieved:
            return (
                f"**Deterministic retrieval mode.** {status_message}\n\n"
                f"**Question:** {message}\n\n"
                "No matching evidence was found in the approved local corpus. I cannot support a scientific "
                "conclusion without a source."
            )
        lines = [
            f"**Deterministic retrieval mode.** {status_message}",
            f"\n**Question:** {message}",
            f"\n**Task:** {TASK_INSTRUCTIONS[task_type]}",
            "\n**Retrieved evidence (excerpts, not new findings):**",
        ]
        for item in retrieved[:3]:
            snippet = " ".join(item.chunk.text.split())
            if len(snippet) > 540:
                snippet = f"{snippet[:537].rstrip()}..."
            lines.append(f"- **{item.chunk.source_title}** {self._citation_marker(item.chunk)} — {snippet}")
        lines.append(
            "\nNo additional measurement or conclusion is inferred from these excerpts. "
            "Check the cited source and its limitations before interpretation."
        )
        if task_type == "generate_report":
            return "\n".join(
                [
                    f"**Deterministic retrieval mode.** {status_message}",
                    f"\n## Scope\n{message}",
                    "\n## Evidence\n" + "\n".join(lines[3:-1]),
                    "\n## Project calculations\nNo new calculation was performed.",
                    "\n## Scientific hypotheses\nAny unvalidated interpretation must remain explicitly bounded.",
                    "\n## Evidence gaps\nOnly gaps stated in the retrieved sources are reported.",
                    "\n## Suggestions\nHuman scientific review and primary-source verification are required.",
                    "\n## Limitations\nNo new NASA measurement, validated prediction, or operational decision is produced.",
                ]
            )
        if task_type == "generate_proposal":
            return "\n".join(
                [
                    f"**Deterministic retrieval mode.** {status_message}",
                    f"\n## Research question\n{message}",
                    "\n## Retrieved background\n" + "\n".join(lines[3:-1]),
                    "\n## Proposed next steps\nA domain expert should define an experiment using rights-cleared primary data, explicit units, controls, and independent validation.",
                    "\n## Human review\nThis generated research suggestion is not an operational instruction and requires scientific review.",
                ]
            )
        return "\n".join(lines)

    def answer(
        self,
        *,
        message: str,
        task_type: TaskType = "qa_with_citations",
        model: str | None = None,
        scenario_context: dict[str, Any] | None = None,
        psi_ids: list[str] | None = None,
        pillar: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        status = self.client.status()
        query_parts = [message, task_type.replace("_", " "), TASK_RETRIEVAL_CONTEXT.get(task_type, "")]
        if scenario_context:
            query_parts.append(str(scenario_context))
        retrieved = self.retrieve(" ".join(query_parts), top_k=5, psi_ids=psi_ids, pillar=pillar)
        citations = [item.citation() for item in retrieved]
        selected_model = model or status["selected_model"]
        generation_mode = "offline_rag_deterministic"
        latency_ms = 0
        status_message = status["status_message"]
        answer = ""

        if status["online"] and selected_model:
            installed = status["available_models"]
            if selected_model not in installed:
                status_message = f"Requested model {selected_model!r} is not installed locally; using deterministic retrieval."
            else:
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                for turn in (history or [])[-8:]:
                    if turn.get("role") in {"user", "assistant"} and isinstance(turn.get("content"), str):
                        messages.append({"role": turn["role"], "content": turn["content"][:4000]})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Task mode: {task_type}. {TASK_INSTRUCTIONS[task_type]}\n\n"
                            + build_user_prompt(message, [item.chunk for item in retrieved], scenario_context)
                        ),
                    }
                )
                try:
                    answer, latency_ms = self.client.chat(selected_model, messages)
                    if answer:
                        answer = self._safe_llm_citations(answer, retrieved, message, scenario_context)
                        generation_mode = "local_ollama_rag"
                    else:
                        status_message = "Ollama returned an empty answer; deterministic retrieval is shown instead."
                except OllamaUnavailable as exc:
                    status_message = f"{exc}; deterministic local retrieval remains available."

        if generation_mode == "offline_rag_deterministic":
            answer = self._offline_answer(message, task_type, retrieved, status_message)
        answer = f"{answer}\n\n> {SAFETY_DISCLAIMER}"
        return {
            "task_type": task_type,
            "answer_markdown": answer,
            "epistemic_breakdown": self._breakdown(retrieved, scenario_context, task_type),
            "citations": citations,
            "ollama_status": {
                "online": status["online"],
                "selected_model": selected_model,
                "generation_mode": generation_mode,
                "latency_ms": latency_ms,
                "status_message": status_message,
            },
            "safety_disclaimer": SAFETY_DISCLAIMER,
        }
