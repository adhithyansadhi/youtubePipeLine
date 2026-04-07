"""
Agent 2 — Topic Filter
Removes already-used topics (from memory) and selects the best remaining one.
Output: { "selected_topic": str, "reason": str }
"""
from .base_agent import BaseAgent


class TopicFilterAgent(BaseAgent):
    name = "TopicFilterAgent"

    def _execute(self, input_data: dict) -> dict:
        """
        input_data:
          - topics: list of {"topic", "score", "reason"}
          - used_topics: list of already-used topic strings
          - exclude_this_run: list of topics already selected in this run
        """
        all_topics: list[dict] = input_data.get("topics", [])
        used_topics: list[str] = input_data.get("used_topics", [])
        exclude_this_run: list[str] = input_data.get("exclude_this_run", [])

        blocked = set(t.lower().strip() for t in used_topics + exclude_this_run)

        # Filter out used/excluded topics (fuzzy: check if any word overlap)
        def is_blocked(topic: str) -> bool:
            t_lower = topic.lower()
            for b in blocked:
                # Simple overlap check: if >50% of words match
                t_words = set(t_lower.split())
                b_words = set(b.split())
                if t_words and b_words:
                    overlap = len(t_words & b_words) / max(len(t_words), len(b_words))
                    if overlap > 0.5:
                        return True
            return False

        available = [t for t in all_topics if not is_blocked(t["topic"])]

        if not available:
            raise ValueError(
                "All topics have been used! Clear memory/used_topics.json to reset."
            )

        # Pick the highest-scored available topic
        best = max(available, key=lambda x: x.get("score", 0))
        return {
            "selected_topic": best["topic"],
            "score": best.get("score", 0),
            "reason": best.get("reason", ""),
        }
