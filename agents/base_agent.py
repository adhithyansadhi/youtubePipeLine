"""
Base Agent -- all agents inherit from this class.
Provides:
  - OpenRouter LLM call helper with retry logic
  - Structured JSON output enforcement
  - Mock mode support
"""
import os
import json
import time
import re
import warnings
import requests
from abc import ABC, abstractmethod

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from rich.console import Console

console = Console()

MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
# Default models from .env
OR_MODEL_DEFAULT = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")


class BaseAgent(ABC):
    """Abstract base class for all pipeline agents using OpenRouter."""

    name: str = "BaseAgent"
    MAX_RETRIES: int = 5
    RETRY_DELAY: float = 2.0

    # -- Public interface ---------------------------------------------------
    def run(self, input_data: dict) -> dict:
        """
        Execute the agent. Handles retries automatically.
        Subclasses implement _execute(input_data) -> dict.
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                result = self._execute(input_data)
                return result
            except Exception as exc:
                console.print(
                    f"[yellow]  [{self.name}] attempt {attempt}/{self.MAX_RETRIES} failed: {exc}[/yellow]"
                )
                if attempt < self.MAX_RETRIES:
                    delay = self._extract_retry_delay(exc)
                    console.print(f"[dim]  [{self.name}] waiting {delay:.0f}s before retry...[/dim]")
                    time.sleep(delay)
                else:
                    console.print(f"[red]  [{self.name}] failed after {self.MAX_RETRIES} attempts.[/red]")
                    raise

    @staticmethod
    def _extract_retry_delay(exc: Exception) -> float:
        """Parse OpenRouter/API suggested retryDelay from 429 errors, or use default."""
        exc_str = str(exc).lower()
        if "429" in exc_str or "rate limit" in exc_str or "resource_exhausted" in exc_str:
            # Look for "retry in X.XXs" patterns in the error message
            match = re.search(r"retry.*?(\d+(?:\.\d+)?)s", exc_str)
            if match:
                return min(float(match.group(1)) + 1, 120)
            return 20.0  # Default wait for rate limits
        return 2.0  # Default wait for other errors

    @abstractmethod
    def _execute(self, input_data: dict) -> dict:
        """Core agent logic -- must be implemented by each subclass."""
        ...

    # -- OpenRouter LLM helpers ---------------------------------------------
    def _call_llm(self, prompt: str, model: str | None = None, mock_response: dict | None = None) -> dict:
        """
        Call OpenRouter Chat API and return parsed JSON dict.
        In MOCK_MODE, returns mock_response instead of calling the API.
        """
        if MOCK_MODE:
            if mock_response is not None:
                return mock_response
            raise ValueError(f"{self.name}: MOCK_MODE enabled but no mock_response provided.")

        if not OPENROUTER_API_KEY:
            raise EnvironmentError("OPENROUTER_API_KEY is not set in .env.")

        target_model = model if model else OR_MODEL_DEFAULT

        full_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Respond ONLY with valid JSON. No markdown fences, no explanation. "
            "Just raw JSON."
        )

        try:
            payload = {
                "model": target_model,
                "messages": [{"role": "user", "content": full_prompt}],
                "max_tokens": 4000,
                "response_format": {"type": "json_object"} if "gemini" in target_model.lower() or "gpt" in target_model.lower() else None
            }
            
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY.strip()}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/turboquant/youtubePipeLine", # Required for some models
                "X-OpenRouter-Title": "YouTubePipeLine"
            }

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            raw_content = data["choices"][0]["message"]["content"].strip()
            
            # Strip markdown fences if present
            raw_content = re.sub(r"^```(?:json)?\s*", "", raw_content)
            raw_content = re.sub(r"\s*```$", "", raw_content.strip())
            
            return json.loads(raw_content)
            
        except requests.exceptions.HTTPError as err:
            console.print(f"[red]  [{self.name}] HTTP Error: {err}[/red]")
            try:
                console.print(f"[dim]  Response body: {err.response.text}[/dim]")
            except:
                pass
            if err.response.status_code == 429:
                # Re-raise to trigger the retry logic in run()
                raise Exception(f"429 Rate Limit: {err.response.text}") from err
            raise

    def _call_llm_text(self, prompt: str, model: str | None = None) -> str:
        """Call OpenRouter and return plain text (no JSON parsing)."""
        if MOCK_MODE:
            return "[MOCK TEXT RESPONSE]"
            
        target_model = model if model else OR_MODEL_DEFAULT
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY.strip()}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": target_model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


    def _call_rerank(self, query: str, documents: list[str], mock_response: list[dict] | None = None) -> list[dict]:
        """
        Call OpenRouter/Cohere Rerank API to score documents against a query.
        Returns a list of dicts: [{"index": int, "relevance_score": float}]
        """
        if MOCK_MODE:
            return mock_response if mock_response else []

        if not OPENROUTER_API_KEY:
            console.print("[yellow]  [BaseAgent] OPENROUTER_API_KEY not found. Skipping rerank.[/yellow]")
            return []

        try:
            payload = {
                "model": "cohere/rerank-4-pro",
                "query": query,
                "documents": documents,
                "top_n": len(documents)
            }
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY.strip()}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/rerank",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # OpenRouter returns results in results list
            return data.get("results", [])
            
        except Exception as exc:
            console.print(f"[yellow]  [BaseAgent] OpenRouter Rerank failed: {exc}[/yellow]")
            return []

