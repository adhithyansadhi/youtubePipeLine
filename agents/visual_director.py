"""
Agent 4 -- Visual Director
Converts script into a scene-by-scene visual plan.
Each scene: visual description, stock footage keywords, on-screen text, transition.
Scene changes every 2-4 seconds. No static visuals.
Output: { "scenes": [ { scene fields } ] }
"""
from .base_agent import BaseAgent
from .mock_generator import generate_mock_scenes


class VisualDirectorAgent(BaseAgent):
    name = "VisualDirectorAgent"

    def _execute(self, input_data: dict) -> dict:
        script: str = input_data.get("script", "")
        topic: str = input_data.get("selected_topic", "")

        prompt = f"""
You are a YouTube Shorts visual director. Convert this script into a detailed scene-by-scene plan.

TOPIC: {topic}

SCRIPT:
{script}

RULES:
- Create 5-8 scenes
- Each scene is 2-4 seconds long (they must add up to ~25-30 sec total)
- Every scene MUST have a different visual -- no static shots
- Use stock footage style descriptions that a video editor can search for
- On-screen text: SHORT, BOLD, capitalized -- max 5 words per scene
- Transitions: use glitch cut, whip pan, zoom in, flash cut, fade out, smash cut

Respond ONLY with JSON:
{{
  "scenes": [
    {{
      "scene_id": 1,
      "duration_sec": 3,
      "visual_description": "detailed visual description for the editor",
      "stock_keywords": ["keyword1", "keyword2", "keyword3"],
      "on_screen_text": "BOLD TEXT HERE",
      "transition": "transition type"
    }}
  ]
}}
"""
        mock = generate_mock_scenes(topic, script)
        return self._call_llm(prompt, mock_response=mock)
