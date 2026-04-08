"""
Agent 3 — Script Writer
Generates a 20–30 second YouTube Shorts script.
Structure: Hook -> Value -> Pattern Interrupt -> Ending -> CTA
Output: { "script": str, "estimated_duration_sec": int, "hook": str, "cta": str }
"""
from .base_agent import BaseAgent
from .mock_generator import generate_mock_script


class ScriptWriterAgent(BaseAgent):
    name = "ScriptWriterAgent"

    def _execute(self, input_data: dict) -> dict:
        topic: str = input_data.get("selected_topic", "")
        feedback: str = input_data.get("qc_feedback", "")

        feedback_block = ""
        if feedback:
            feedback_block = f"\n\nPREVIOUS FEEDBACK TO FIX:\n{feedback}\n"

        prompt = f"""
You are an expert YouTube Shorts script writer. Write a viral script about:

TOPIC: {topic}
{feedback_block}
REQUIREMENTS:
- Total length: 20-30 seconds when spoken at natural pace
- Use simple English. Short punchy sentences. No fluff.
- Structure MUST follow:
    1. HOOK (0-3 sec): One powerful sentence that creates instant curiosity. Start with a shocking fact, question, or contradiction.
    2. VALUE (3-18 sec): Fast, dense facts or story. Each sentence reveals something new.
    3. PATTERN INTERRUPT (18-22 sec): Unexpected twist, reframe, or surprising connection.
    4. ENDING (22-27 sec): Satisfying payoff or cliffhanger.
    5. CTA (27-30 sec): One clear call-to-action (comment, subscribe, follow).
- Do NOT use filler words like "amazing", "incredible", "literally"
- Each sentence on its own line for easy reading

CRITICAL ACCURACY RULES:
- ONLY use REAL, VERIFIABLE facts. Every claim must be something a viewer can Google and confirm.
- NEVER invent project names, study names, company names, statistics, or events.
- NEVER use vague phrases like "reportedly", "rumors suggest", "sources say" to cover for made-up claims.
- If discussing a real event, use the real names, dates, and figures.
- If you are not 100% certain a fact is real, do NOT include it. Replace it with a different real fact.

Respond with JSON:
{{
  "hook": "the opening hook sentence only",
  "script": "full script with line breaks between sentences",
  "cta": "the CTA sentence only",
  "estimated_duration_sec": 27
}}
"""
        mock = generate_mock_script(topic)
        return self._call_llm(prompt, mock_response=mock)
