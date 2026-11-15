from __future__ import annotations

import ctypes
import json
import os
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MODEL_SPECS = (
    {
        "name": "qwen3:4b",
        "ram_requirement_gb": 3.5,
        "description": "Lightweight local instruct model; recommended starting point.",
    },
    {
        "name": "qwen3:8b",
        "ram_requirement_gb": 6.0,
        "description": "Higher-capacity local instruct model; allow additional runtime memory.",
    },
    {
        "name": "qwen2.5:3b",
        "ram_requirement_gb": 3.0,
        "description": "Lightweight alternative if already installed.",
    },
    {
        "name": "qwen2.5:7b",
        "ram_requirement_gb": 6.0,
        "description": "Local instruct alternative; allow additional runtime memory.",
    },
    {
        "name": "llama3.2:3b",
        "ram_requirement_gb": 3.0,
        "description": "Lightweight local instruct alternative.",
    },
    {
        "name": "mistral:7b",
        "ram_requirement_gb": 6.0,
        "description": "Local instruct alternative; allow additional runtime memory.",
    },
)


class OllamaError(RuntimeError):
    """A local Ollama request failed for a reason other than connectivity."""


class OllamaUnavailable(OllamaError):
    """The local Ollama service or requested model is unavailable."""


def _total_memory_gb() -> float | None:
    if sys.platform == "win32":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.ullTotalPhys / (1024**3)
        return None

    if hasattr(os, "sysconf"):
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
        except (OSError, ValueError):
            return None
        if isinstance(pages, int) and isinstance(page_size, int) and pages > 0 and page_size > 0:
            return pages * page_size / (1024**3)
    return None


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        health_timeout: float = 2.0,
        generation_timeout: float = 45.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")
        self.health_timeout = health_timeout
        self.generation_timeout = generation_timeout

    def _request(
        self,
        path: str,
        payload: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"content-type": "application/json"} if data is not None else {},
            method="POST" if data is not None else "GET",
        )
        try:
            with urlopen(request, timeout=timeout or self.health_timeout) as response:
                body = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            if exc.code in (404, 503):
                raise OllamaUnavailable(f"Ollama endpoint {path} is unavailable: {detail or exc.reason}") from exc
            raise OllamaError(f"Ollama request failed ({exc.code}): {detail or exc.reason}") from exc
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise OllamaUnavailable(f"Local Ollama is unavailable at {self.base_url}: {exc}") from exc

        try:
            result = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OllamaError(f"Ollama returned invalid JSON from {path}.") from exc
        if not isinstance(result, dict):
            raise OllamaError(f"Ollama returned an unexpected response from {path}.")
        return result

    def list_models(self) -> list[str]:
        response = self._request("/api/tags", timeout=self.health_timeout)
        models = response.get("models", [])
        if not isinstance(models, list):
            raise OllamaError("Ollama /api/tags response has an invalid models field.")
        return sorted(
            {
                name
                for item in models
                if isinstance(item, dict)
                and isinstance((name := item.get("name")), str)
                and name
            }
        )

    @staticmethod
    def _installed_match(preferred: str, installed: list[str]) -> str | None:
        preferred_base = preferred.split(":", 1)[0].lower()
        for model in installed:
            if model.lower() == preferred.lower() or model.lower().startswith(f"{preferred_base}:"):
                return model
        return None

    def status(self) -> dict[str, Any]:
        total_memory = _total_memory_gb()
        try:
            models = self.list_models()
        except OllamaUnavailable as exc:
            return {
                "online": False,
                "base_url": self.base_url,
                "available_models": [],
                "selected_model": None,
                "recommended_models": self._recommendations([], total_memory),
                "total_memory_gb": round(total_memory, 1) if total_memory is not None else None,
                "status_message": str(exc),
            }

        chat_models = [
            model for model in models
            if not any(marker in model.lower() for marker in ("embed", "vision", "whisper"))
        ]
        selected = next(
            (
                match
                for candidate in MODEL_SPECS
                if (match := self._installed_match(candidate["name"], chat_models))
            ),
            chat_models[0] if chat_models else None,
        )
        if not models:
            message = "Ollama is online, but no local model is installed. Run `ollama run qwen3:4b` to add one."
        elif not chat_models:
            message = "Ollama is online, but no local chat/instruct model was detected. Run `ollama run qwen3:4b` to add one."
        else:
            message = "Ollama is online. Inference stays on this local service."
        return {
            "online": True,
            "base_url": self.base_url,
            "available_models": models,
            "selected_model": selected,
            "recommended_models": self._recommendations(models, total_memory),
            "total_memory_gb": round(total_memory, 1) if total_memory is not None else None,
            "status_message": message,
        }

    def _recommendations(self, installed: list[str], total_memory: float | None) -> list[dict[str, Any]]:
        recommendations: list[dict[str, Any]] = []
        for spec in MODEL_SPECS:
            match = self._installed_match(spec["name"], installed)
            memory_ok = total_memory is None or total_memory >= spec["ram_requirement_gb"] + 1.0
            recommendations.append(
                {
                    **spec,
                    "installed": match is not None,
                    "installed_name": match,
                    "recommended": bool(memory_ok and spec["name"] == "qwen3:4b")
                    or bool(memory_ok and spec["name"] == "qwen3:8b" and total_memory is not None and total_memory >= 10.0),
                    "memory_available": memory_ok,
                }
            )
        installed_instruct = [
            model for model in installed
            if any(model.lower().startswith(f"{spec['name'].split(':', 1)[0]}:") for spec in MODEL_SPECS)
        ]
        if installed and not installed_instruct:
            recommendations.insert(
                0,
                {
                    "name": installed[0],
                    "ram_requirement_gb": None,
                    "description": "Installed local model; hardware requirements are model-specific.",
                    "installed": True,
                    "installed_name": installed[0],
                    "recommended": True,
                    "memory_available": None,
                },
            )
        return recommendations

    def chat(self, model: str, messages: list[dict[str, str]]) -> tuple[str, int]:
        started = time.monotonic()
        response = self._request(
            "/api/chat",
            {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.15},
            },
            timeout=self.generation_timeout,
        )
        message = response.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise OllamaError("Ollama /api/chat response did not contain message.content.")
        return content.strip(), round((time.monotonic() - started) * 1000)

    def embed(self, model: str, inputs: list[str]) -> list[list[float]]:
        if not inputs:
            return []
        response = self._request(
            "/api/embed",
            {"model": model, "input": inputs},
            timeout=self.generation_timeout,
        )
        embeddings = response.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(inputs):
            raise OllamaError("Ollama /api/embed response did not match the input count.")
        vectors: list[list[float]] = []
        for vector in embeddings:
            if not isinstance(vector, list) or not all(isinstance(value, (int, float)) for value in vector):
                raise OllamaError("Ollama /api/embed returned an invalid embedding vector.")
            vectors.append([float(value) for value in vector])
        return vectors
