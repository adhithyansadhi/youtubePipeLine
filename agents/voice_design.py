"""
Agent 5 -- Voice Design Agent
Defines narration style based on script content.
Output: { "tone": str, "speed": str, "emotion": str, "voice_notes": str }
"""
from .base_agent import BaseAgent
from .mock_generator import generate_mock_voice


class VoiceDesignAgent(BaseAgent):
    name = "VoiceDesignAgent"

    def _execute(self, input_data: dict) -> dict:
        script: str = input_data.get("script", "")
        topic: str = input_data.get("selected_topic", "")
        hook: str = input_data.get("hook", "")

        prompt = f"""
You are a voice acting director for YouTube Shorts. Based on this script, define the ideal narration style.

TOPIC: {topic}
HOOK: {hook}
SCRIPT:
{script}

Analyze the script's emotion and determine:
- Tone (e.g., mysterious, energetic, inspiring, dark, comedic, educational)
- Speed (e.g., fast-paced 1.2x, moderate with pauses, slow and deliberate)
- Emotion level (e.g., high curiosity, calm authority, playful urgency, intense)
- Voice notes: 2-3 sentences of specific performance direction for a TTS or voice actor

Respond ONLY with JSON:
{{
  "tone": "...",
  "speed": "...",
  "emotion": "...",
  "voice_notes": "..."
}}
"""
        mock = generate_mock_voice(topic)
        return self._call_llm(prompt, mock_response=mock)
