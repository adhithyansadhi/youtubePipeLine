"""
Agent 8 -- Quality Control Agent (Critical)
Reviews all content. Scores Hook, Pacing, Retention (0-10).
If any score < 7 -> returns approved=False with specific feedback.
Max 2 retries before forced approval.
Output: { "approved": bool, "scores": {...}, "feedback": str, "overall_score": float }
"""
from .base_agent import BaseAgent
from .mock_generator import generate_mock_qc

PASS_THRESHOLD = 7.0


class QualityControlAgent(BaseAgent):
    name = "QualityControlAgent"

    def _execute(self, input_data: dict) -> dict:
        script: str = input_data.get("script", "")
        hook: str = input_data.get("hook", "")
        cta: str = input_data.get("cta", "")
        topic: str = input_data.get("selected_topic", "")
        attempt: int = input_data.get("qc_attempt", 1)
        force_pass: bool = input_data.get("force_pass", False)

        if force_pass:
            return {
                "approved": True,
                "scores": {"hook_strength": 7, "pacing": 7, "retention_potential": 7},
                "overall_score": 7.0,
                "feedback": "Force-approved after max retries.",
            }

        prompt = f"""
You are a ruthless YouTube Shorts quality control reviewer. Evaluate this script.

TOPIC: {topic}
HOOK: {hook}
SCRIPT:
{script}
CTA: {cta}

Score each dimension from 0-10:

1. hook_strength: Does the opening sentence make the viewer NEED to keep watching?
2. pacing: Is every sentence earning its place? No slow parts, no fluff?
3. retention_potential: Would someone watch and immediately share this?

RULES:
- Be brutally honest. Most scripts score 6-8. A 10 is exceptional.
- If any score is below 7, set approved: false and give SPECIFIC rewrite instructions in feedback.
- If all scores are 7+, set approved: true.

Respond ONLY with JSON:
{{
  "approved": true,
  "scores": {{
    "hook_strength": 8,
    "pacing": 7,
    "retention_potential": 8
  }},
  "overall_score": 7.7,
  "feedback": "Specific improvement instructions or empty string if approved"
}}
"""
        mock = generate_mock_qc(topic, attempt)
        result = self._call_llm(prompt, mock_response=mock)

        # Compute overall if missing
        if "overall_score" not in result:
            scores = result.get("scores", {})
            vals = list(scores.values())
            result["overall_score"] = round(sum(vals) / len(vals), 1) if vals else 0

        result["approved"] = result["overall_score"] >= PASS_THRESHOLD
        return result
