"""
Agent 1 — Trend Analyst
Discovers trending or high-interest topics from Google Trends (via pytrends)
and falls back to a curated evergreen viral topic list.
LLM scores each topic for virality, curiosity, and relevance.
Output: { "topics": [{"topic": str, "score": int, "reason": str}] }
"""
import os
import random
from .base_agent import BaseAgent

# ── Evergreen viral topic pool (fallback) ──────────────────────────────────
EVERGREEN_TOPICS = [
    "The Dead Internet Theory — Most of the web is bots",
    "AI is replacing jobs faster than anyone predicted",
    "The Great Green Wall — Africa's 5000-mile forest",
    "Scientists found a hidden corridor in the Great Pyramid",
    "Starlink's plan to give internet to every human on Earth",
    "The Fermi Paradox — Why haven't we found aliens yet?",
    "Your smartphone is more powerful than Apollo 11's computers",
    "The world's deepest hole — What they found shocked everyone",
    "Sleep deprivation is literally shrinking your brain",
    "The Voynich Manuscript — A book no one can read",
    "North Korea's secret underground city",
    "Octopuses can see color despite being colorblind",
    "A single bolt of lightning contains enough energy to power a house",
    "The largest structure in the universe — The Hercules Corona Borealis",
    "Quantum computers can break all encryption in minutes",
    "The reason you can't remember being a baby (explained)",
    "The real reason NASA stopped going to the Moon",
    "There are more trees on Earth than stars in the Milky Way",
    "Your gut bacteria control your mood more than your brain does",
    "The Antikythera Mechanism — Ancient Greece's computer",
    "The Library of Alexandria had a copy of every book ever written",
    "How GPS satellites actually work in space",
    "The Ice Wall at the edge of the Antarctic Treaty",
    "What happens to your body in the first 60 seconds after you die",
    "India's space mission found water on the Moon first",
]

# ── Topics to query in Google Trends ─────────────────────────────────────
TREND_KEYWORDS = ["AI technology", "space exploration", "science facts", "history mystery", "tech breakthrough"]


class TrendAnalystAgent(BaseAgent):
    name = "TrendAnalystAgent"

    def _execute(self, input_data: dict) -> dict:
        raw_topics = self._fetch_trends()

        prompt = f"""
You are a YouTube Shorts trend analyst. Your job is to score topics for YouTube Shorts virality.

Score each topic from 1–10 based on:
- Virality potential (will people share this?)
- Curiosity trigger (does the title make you NEED to watch?)
- Relevance (is this timely or evergreen-interesting?)

Topics to score:
{chr(10).join(f"- {t}" for t in raw_topics)}

Respond with a JSON object in this exact format:
{{
  "topics": [
    {{"topic": "exact topic string", "score": 8, "reason": "one sentence why"}},
    ...
  ]
}}

Include ALL topics. Sort by score descending.
"""
        mock = {
            "topics": [
                {"topic": t, "score": random.randint(6, 10), "reason": "High curiosity and shareability."}
                for t in raw_topics
            ]
        }

        result = self._call_llm(prompt, mock_response=mock)
        # Sort by score descending
        result["topics"] = sorted(result["topics"], key=lambda x: x.get("score", 0), reverse=True)
        return result

    def _fetch_trends(self) -> list[str]:
        """Try pytrends; fall back to evergreen list on any error."""
        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl="en-US", tz=330, timeout=(10, 25))
            pytrends.build_payload(TREND_KEYWORDS, cat=0, timeframe="now 1-d", geo="", gprop="")
            related = pytrends.related_queries()

            topics = []
            for kw, data in related.items():
                if data and data.get("top") is not None:
                    top_df = data["top"]
                    if top_df is not None and not top_df.empty:
                        for _, row in top_df.head(3).iterrows():
                            topics.append(str(row["query"]))
            if topics:
                # Blend with some evergreen picks so we always have variety
                extras = random.sample(EVERGREEN_TOPICS, min(15, len(EVERGREEN_TOPICS)))
                topics = list(dict.fromkeys(topics + extras))[:25]
                return topics
        except Exception:
            pass  # Fall through to evergreen

        return random.sample(EVERGREEN_TOPICS, min(20, len(EVERGREEN_TOPICS)))
