"""
Agent 9 — Memory Agent
Persists used topics and past run metadata to disk.
Prevents topic duplication across runs.
Output: { "status": "saved" | "loaded", "used_topics": [...], "run_history": [...] }
"""
import json
import os
from datetime import datetime
from .base_agent import BaseAgent

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "memory", "used_topics.json")


class MemoryAgent(BaseAgent):
    name = "MemoryAgent"
    MAX_RETRIES = 1  # File I/O doesn't need LLM retries

    def _execute(self, input_data: dict) -> dict:
        """
        Modes (set 'action' in input_data):
          - 'load'  → returns used_topics + run_history
          - 'save'  → saves topic + optional metadata
        """
        action = input_data.get("action", "load")

        if action == "load":
            return self._load()
        elif action == "save":
            return self._save(
                topic=input_data.get("topic", ""),
                metadata=input_data.get("metadata", {}),
            )
        else:
            raise ValueError(f"MemoryAgent: unknown action '{action}'")

    def _load(self) -> dict:
        path = self._resolved_path()
        if not os.path.exists(path):
            return {"status": "loaded", "used_topics": [], "run_history": []}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "status": "loaded",
            "used_topics": data.get("used_topics", []),
            "run_history": data.get("run_history", []),
        }

    def _save(self, topic: str, metadata: dict) -> dict:
        path = self._resolved_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Load existing
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"used_topics": [], "run_history": []}

        # Append topic
        if topic and topic not in data["used_topics"]:
            data["used_topics"].append(topic)

        # Append run history entry
        if metadata:
            data["run_history"].append({
                "timestamp": datetime.now().isoformat(),
                "topic": topic,
                **metadata,
            })

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return {"status": "saved", "topic": topic}

    def _resolved_path(self) -> str:
        return os.path.abspath(MEMORY_FILE)
