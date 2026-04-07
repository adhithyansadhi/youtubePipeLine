"""
Agent 6 -- Audio Engineer Agent
Selects background music genre and suggests timed sound effects.
Rules: music must NOT overpower voice, SFX adds engagement.
Output: { "music": { ... }, "sfx": [ ... ] }
"""
from .base_agent import BaseAgent
from .mock_generator import generate_mock_audio


class AudioEngineerAgent(BaseAgent):
    name = "AudioEngineerAgent"

    def _execute(self, input_data: dict) -> dict:
        tone: str = input_data.get("tone", "")
        emotion: str = input_data.get("emotion", "")
        topic: str = input_data.get("selected_topic", "")
        scenes: list = input_data.get("scenes", [])

        scene_summary = "\n".join(
            f"- Scene {s['scene_id']} at ~{sum(sc['duration_sec'] for sc in scenes[:i])}s: {s.get('visual_description', '')[:60]}"
            for i, s in enumerate(scenes)
        ) if scenes else "No scene data available."

        prompt = f"""
You are an audio engineer for YouTube Shorts. Select the perfect music and sound effects.

TOPIC: {topic}
VOICE TONE: {tone}
EMOTION: {emotion}
SCENES:
{scene_summary}

RULES:
- Background music must stay 25-35% of voice volume (never overpowers speech)
- Choose music that MATCHES the emotional tone
- Add 3-5 SFX timed to key moments (scene changes, emphasis points, CTA)
- SFX should be subtle -- enhancing, not distracting

Respond ONLY with JSON:
{{
  "music": {{
    "genre": "...",
    "description": "...",
    "bpm": "...",
    "volume_level": "25-30% of voice",
    "search_keywords": ["keyword1", "keyword2"]
  }},
  "sfx": [
    {{"timestamp_sec": 0, "effect": "effect name", "purpose": "why this effect here"}}
  ]
}}
"""
        mock = generate_mock_audio(topic)
        return self._call_llm(prompt, mock_response=mock)
