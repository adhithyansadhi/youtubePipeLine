"""
Agent 7 -- Subtitle Agent
Chunk script into 2-4 word subtitle cards synced to speech rhythm.
Identifies KEY words to highlight (bold/colored in editor).
Output: { "subtitles": [ {"text": str, "highlight": bool, "start_word": str} ] }
"""
from .base_agent import BaseAgent
from .mock_generator import generate_mock_subtitles


class SubtitleAgent(BaseAgent):
    name = "SubtitleAgent"

    def _execute(self, input_data: dict) -> dict:
        script: str = input_data.get("script", "")
        topic: str = input_data.get("selected_topic", "")

        prompt = f"""
You are a subtitle designer for YouTube Shorts. Your job is to break a script into subtitle cards.

SCRIPT:
{script}

RULES:
- Each subtitle card = 2-4 words MAX
- ALL CAPS
- Mark "highlight": true for emotionally powerful or surprising words/phrases
- The subtitle cards must cover the ENTIRE script in order
- No punctuation except "?" and "..."
- "start_word" = the first word of that card (helps editor sync timing)

Respond ONLY with JSON:
{{
  "subtitles": [
    {{"text": "CARD TEXT HERE", "highlight": false, "start_word": "CARD"}}
  ]
}}

Create enough cards to cover the full script. Typically 15-25 cards for a 25-30 sec script.
"""
        mock = generate_mock_subtitles(topic, script)
        return self._call_llm(prompt, mock_response=mock)
