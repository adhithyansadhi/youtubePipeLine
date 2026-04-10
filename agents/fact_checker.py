import os
import json
import re
from .base_agent import BaseAgent
from rich.console import Console

console = Console()

# Fact check model from .env
HF_FACT_CHECK_MODEL = os.getenv("HF_FACT_CHECK_MODEL", "meta-llama/Llama-3.3-70B-Instruct")


class FactCheckerAgent(BaseAgent):
    """
    Agent 15 — Fact Checker Agent
    Verifies factual claims using a large HF model.
    Ensures that script content is grounded in real-world data and not hallucinated.
    """
    name = "FactCheckerAgent"
    MAX_RETRIES = 2

    def _execute(self, input_data: dict) -> dict:
        script: str = input_data.get("script", "")
        topic: str = input_data.get("selected_topic", "")

        if not script:
            return {"verified": True, "claims": [], "summary": "No script to verify."}

        console.print(f"    [dim]Verifying claims with fact-check model: {HF_FACT_CHECK_MODEL}[/dim]")
        
        prompt = f"""
You are an ELITE fact-checker for a high-traffic YouTube Shorts channel. 
Your goal is to ensure 100% factual accuracy. You must proactively search the web to verify every specific claim.

TOPIC: {topic}

SCRIPT TO VERIFY:
{script}

TASK:
1. Break down the script into individual testable factual claims (e.g., names of companies, statistics, dates, scientific facts).
2. For each claim, use your web-search capabilities to verify its accuracy.
3. Mark every claim as TRUE, FALSE, or UNVERIFIABLE.
4. If FALSE, you MUST provide the correct fact and a source reference.
5. If the script mentions a specific project or source that doesn't exist, mark it FALSE.

RESPONSE FORMAT (JSON ONLY):
{{
  "verified": true/false (false if ANY claim is FALSE),
  "claims": [
    {{
      "claim": "exact text from the script",
      "verdict": "TRUE" | "FALSE" | "UNVERIFIABLE",
      "source": "Title of the website or URL where you verified this",
      "correction": "Correct factual statement if FALSE, otherwise empty string"
    }}
  ],
  "summary": "One sentence overall assessment",
  "corrected_facts": "A single paragraph containing ONLY the corrected versions of the false claims found."
}}

If all claims are TRUE, "corrected_facts" should be an empty string.
"""
        
        # Call Hugging Face API with the specialized fact-check model
        try:
            result = self._call_llm(prompt, model=HF_FACT_CHECK_MODEL)
            
            # If the LLM returns a list instead of a dict, wrap it or take the first element
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
            
            # Basic validation of result structure
            if not isinstance(result, dict) or "claims" not in result:
                # If it's still not a dict or missing claims, try to re-parse or fallback
                # Sometimes LLMs wrap the JSON in a "result" key
                if isinstance(result, dict) and "result" in result:
                    result = result["result"]
                else:
                    raise ValueError("Fact Checker returned malformed response.")
                
            return result
        except Exception as exc:
            console.print(f"    [yellow]Verification failed: {exc}. Falling back to internal check.[/yellow]")
            # Fallback to default HF model if primary fails
            return self._verify_with_fallback(script, topic)

    def _verify_with_fallback(self, script: str, topic: str) -> dict:
        """Fallback when the specialized verification model fails."""
        prompt = f"Strictly fact-check this script for fabrications or hallucinations about {topic}:\n\n{script}"
        return self._call_llm(prompt)

