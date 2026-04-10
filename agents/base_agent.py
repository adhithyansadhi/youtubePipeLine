"""
Base Agent -- all agents inherit from this class.
Provides:
  - OpenRouter LLM call helper with retry logic
  - Structured JSON output enforcement
  - Mock mode support
  - Fallback model support (NEW)
"""

import os
import json
import time
import re
import warnings
import requests
from abc import ABC, abstractmethod

warnings.filterwarnings("ignore", category=FutureWarning)

from rich.console import Console
console = Console()

# ── ENV CONFIG ─────────────────────────────────────────────
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

HF_MODEL_DEFAULT = os.getenv("HF_MODEL", "Qwen/Qwen2.5-72B-Instruct")
FALLBACK_MODEL = os.getenv("HF_FALLBACK_MODEL", "mistralai/Mistral-Nemo-Instruct-2407")


class BaseAgent(ABC):
    """Abstract base class for all pipeline agents using Hugging Face."""

    name: str = "BaseAgent"
    MAX_RETRIES: int = 5
    RETRY_DELAY: float = 2.0

    # ── PUBLIC EXECUTION ───────────────────────────────────
    def run(self, input_data: dict) -> dict:
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return self._execute(input_data)

            except Exception as exc:
                console.print(
                    f"[yellow] [{self.name}] attempt {attempt}/{self.MAX_RETRIES} failed: {exc}[/yellow]"
                )

                if attempt < self.MAX_RETRIES:
                    delay = self._extract_retry_delay(exc)
                    console.print(f"[dim] [{self.name}] retrying in {delay}s...[/dim]")
                    time.sleep(delay)
                else:
                    console.print(f"[red] [{self.name}] failed after retries[/red]")
                    raise

    # ── RETRY DELAY HANDLER ────────────────────────────────
    @staticmethod
    def _extract_retry_delay(exc: Exception) -> float:
        msg = str(exc).lower()

        if "429" in msg or "rate limit" in msg:
            match = re.search(r"(\d+(?:\.\d+)?)s", msg)
            if match:
                return min(float(match.group(1)) + 1, 60)
            return 20.0

        return 2.0

    @abstractmethod
    def _execute(self, input_data: dict) -> dict:
        pass

    # ── LLM CALL (SAFE + FALLBACK) ─────────────────────────
    def _call_llm(self, prompt: str, model: str | None = None, mock_response: dict | None = None) -> dict:

        if MOCK_MODE:
            return mock_response if mock_response else {}

        if not HUGGINGFACE_API_KEY:
            raise EnvironmentError("HUGGINGFACE_API_KEY not set")

        primary_model = model if model else HF_MODEL_DEFAULT

        # 🔥 Try primary → fallback
        for current_model in [primary_model, FALLBACK_MODEL]:

            try:
                payload = {
                    "model": current_model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1000   # 🔥 FIXED HERE
                }

                headers = {
                    "Authorization": f"Bearer {HUGGINGFACE_API_KEY.strip()}",
                    "Content-Type": "application/json"
                }

                response = requests.post(
                    "https://router.huggingface.co/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )

                response.raise_for_status()
                data = response.json()

                # 🔥 SAFE RESPONSE CHECK
                if "choices" not in data:
                    raise Exception(f"Invalid response format: {data}")

                content = data["choices"][0]["message"]["content"].strip()

                # Robust JSON extraction: Find the first '{' and last '}'
                try:
                    start_idx = content.find('{')
                    end_idx = content.rfind('}')
                    if start_idx != -1 and end_idx != -1:
                        content = content[start_idx:end_idx+1]
                except:
                    pass

                return json.loads(content, strict=False)

            except requests.exceptions.HTTPError as err:
                console.print(f"[yellow] [{self.name}] {current_model} failed: {err}[/yellow]")

                # 🔥 Switch on payment / rate issues
                if err.response.status_code in [402, 429]:
                    continue

            except Exception as e:
                console.print(f"[red] [{self.name}] error: {e}[/red]")
                continue

        # If all models fail
        raise Exception(f"{self.name}: All models failed")

    # ── TEXT CALL (NO JSON) ────────────────────────────────
    def _call_llm_text(self, prompt: str, model: str | None = None) -> str:

        if MOCK_MODE:
            return "[MOCK TEXT]"

        target_model = model if model else HF_MODEL_DEFAULT

        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY.strip()}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": target_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500
        }

        response = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"].strip()

    # ── RERANK (SAFE FALLBACK) ────────────────────────────
    def _call_rerank(self, query: str, documents: list[str]) -> list[dict]:
        """
        Stubbed out reranker since Hugging Face Serverless does not support the 
        Cohere-style rerank endpoint natively. Returns all documents safely.
        """
        console.print("[dim] Skipping rerank (Hugging Face endpoint active)[/dim]")
        return [{"index": i, "document": {"text": doc}, "relevance_score": 0.99} for i, doc in enumerate(documents)]