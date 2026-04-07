"""
Base Agent -- all agents inherit from this class.
Provides:
  - Gemini LLM call helper with retry logic (uses google-genai SDK)
  - Structured JSON output enforcement
  - Mock mode support
"""
import os
import json
import time
import re
import warnings
from abc import ABC, abstractmethod

# Suppress the legacy google.generativeai FutureWarning if it ever surfaces
warnings.filterwarnings("ignore", category=FutureWarning)

from rich.console import Console

console = Console()

MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

_CLIENT = None  # google.genai.Client singleton


def _get_client():
    """Lazy-init the google.genai client."""
    global _CLIENT
    if _CLIENT is None:
        from google import genai
        _CLIENT = genai.Client(api_key=GEMINI_API_KEY)
    return _CLIENT


def _generate(prompt: str) -> str:
    """Call the configured Gemini model and return raw text response."""
    from google import genai
    client = _get_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text.strip()


class BaseAgent(ABC):
    """Abstract base class for all pipeline agents."""

    name: str = "BaseAgent"
    MAX_RETRIES: int = 3
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
                    time.sleep(self.RETRY_DELAY)
                else:
                    console.print(f"[red]  [{self.name}] failed after {self.MAX_RETRIES} attempts.[/red]")
                    raise

    @abstractmethod
    def _execute(self, input_data: dict) -> dict:
        """Core agent logic -- must be implemented by each subclass."""
        ...

    # -- LLM helpers --------------------------------------------------------
    def _call_llm(self, prompt: str, mock_response: dict | None = None) -> dict:
        """
        Call Gemini and return parsed JSON dict.
        In MOCK_MODE, returns mock_response instead of calling the API.
        """
        if MOCK_MODE:
            if mock_response is not None:
                return mock_response
            raise ValueError(f"{self.name}: MOCK_MODE enabled but no mock_response provided.")

        if not GEMINI_API_KEY:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. Add it to your .env file or set MOCK_MODE=true."
            )

        full_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Respond ONLY with valid JSON. No markdown fences, no explanation, no extra text. "
            "Just raw JSON."
        )

        raw = _generate(full_prompt)

        # Strip markdown code fences if Gemini wraps it anyway
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw.strip())

        return json.loads(raw)

    def _call_llm_text(self, prompt: str) -> str:
        """Call Gemini and return plain text (no JSON parsing)."""
        if MOCK_MODE:
            return "[MOCK TEXT RESPONSE]"
        if not GEMINI_API_KEY:
            raise EnvironmentError("GEMINI_API_KEY is not set.")
        return _generate(prompt)
