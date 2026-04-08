"""
Agent 1 — Trend Analyst
Discovers trending or high-interest topics using multiple sources:
  1. LLM (Gemini) — primary source for fresh, real-world trending topics
  2. Google Trends (pytrends) — bonus enhancer when available
  3. Evergreen topics — blended in for variety
LLM scores each topic for virality, curiosity, and relevance.
Output: { "topics": [{"topic": str, "score": int, "reason": str}] }
"""
import os
import random
from rich.console import Console
from .base_agent import BaseAgent
import os

console = Console()
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

# ── Evergreen viral topic pool (blended in for variety) ────────────────────
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
        if not raw_topics:
            return {"topics": []}

        # ── Step 1: Rerank all raw topics using OpenRouter ──────────────────
        query = "Highly viral, curiosity-triggering, and educational YouTube Shorts topics with high audience retention."
        console.print(f"    [dim]Reranking {len(raw_topics)} topics via OpenRouter...[/dim]")
        
        rerank_results = self._call_rerank(query, raw_topics)
        
        scored_topics = []
        if rerank_results:
            # Map index back to topic and relevance_score to 1-10
            for res in rerank_results:
                idx = res.get("index")
                score = res.get("relevance_score", 0)
                if idx is not None and idx < len(raw_topics):
                    scored_topics.append({
                        "topic": raw_topics[idx],
                        "score": max(1, min(10, int(score * 10))),
                        "reason": "Scored by OpenRouter Reranker (optimizing for virality)."
                    })
        else:
            # Fallback if rerank fails
            console.print("    [yellow]Rerank failed or returned no results. Using fallback scores.[/yellow]")
            scored_topics = [{"topic": t, "score": 5, "reason": "Fallback score."} for t in raw_topics]

        # Sort by score descending
        scored_topics = sorted(scored_topics, key=lambda x: x["score"], reverse=True)

        # ── Step 2: Use Gemini to generate 'reasons' for only the top 5 ─────
        # This keeps the logs rich but saves 80% of the LLM tokens
        top_n = 5
        to_enhance = scored_topics[:top_n]
        if to_enhance and not MOCK_MODE:
            try:
                enhance_prompt = f"""
For each of these top trending topics, provide a one-sentence explanation of why it would go viral as a YouTube Short.

TOPICS:
{chr(10).join(f"- {t['topic']}" for t in to_enhance)}

Respond with a JSON object:
{{
  "reasons": ["reason 1", "reason 2", ...]
}}
"""
                enhancements = self._call_llm(enhance_prompt)
                reasons = enhancements.get("reasons", [])
                for i, reason in enumerate(reasons):
                    if i < len(to_enhance):
                        to_enhance[i]["reason"] = reason
            except Exception as exc:
                console.print(f"    [dim]Reason enhancement skipped: {exc}[/dim]")

        return {"topics": scored_topics}

    def _fetch_trends(self) -> list[str]:
        """
        Fetch trending topics from multiple sources:
          1. LLM-discovered trends (primary — most reliable)
          2. Google Trends via pytrends (bonus, often rate-limited)
          3. Evergreen topics (blended in for variety)
        """
        all_topics: list[str] = []

        # ── Source 1: LLM-discovered trending topics (primary) ─────────
        llm_topics = self._fetch_llm_trends()
        if llm_topics:
            console.print(f"    [dim]LLM discovered {len(llm_topics)} trending topics[/dim]")
            all_topics.extend(llm_topics)
        else:
            console.print("    [yellow]LLM trend discovery returned no topics[/yellow]")

        # ── Source 2: Google Trends via pytrends (bonus) ───────────────
        pytrend_topics = self._fetch_pytrends()
        if pytrend_topics:
            console.print(f"    [dim]pytrends found {len(pytrend_topics)} trending queries[/dim]")
            all_topics.extend(pytrend_topics)

        # ── Source 3: Blend in some evergreen topics for variety ────────
        num_evergreen = max(3, 15 - len(all_topics))
        extras = random.sample(EVERGREEN_TOPICS, min(num_evergreen, len(EVERGREEN_TOPICS)))
        all_topics.extend(extras)

        # Deduplicate while preserving order, cap at 25
        seen = set()
        unique = []
        for t in all_topics:
            key = t.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(t)
        return unique[:25]

    def _fetch_llm_trends(self) -> list[str]:
        """Use Gemini to discover currently trending topics for YouTube Shorts."""
        from datetime import datetime

        today = datetime.now().strftime("%B %d, %Y")

        prompt = f"""
You are a trend research assistant. Today is {today}.

Generate 15 currently trending or highly engaging topics that would work as
YouTube Shorts (20-30 second videos). Focus on topics people are ACTUALLY
talking about RIGHT NOW in the news, social media, tech, science, and pop culture.

REQUIREMENTS:
- Each topic must be a specific, compelling statement or question (not a vague category)
- Write each topic as a clickbait-style hook that creates instant curiosity
- Mix categories: tech/AI, science, world events, psychology, space, history
- Prioritize topics that are timely and currently in the news cycle
- Each topic should be 8-15 words, punchy and attention-grabbing

Respond ONLY with JSON:
{{
  "trending_topics": [
    "Topic statement 1",
    "Topic statement 2"
  ]
}}
"""
        try:
            result = self._call_llm(prompt, mock_response={
                "trending_topics": random.sample(EVERGREEN_TOPICS, min(15, len(EVERGREEN_TOPICS)))
            })
            topics = result.get("trending_topics", [])
            if isinstance(topics, list) and topics:
                return [str(t) for t in topics if t]
        except Exception as exc:
            console.print(f"    [yellow]LLM trend discovery failed: {exc}[/yellow]")
        return []

    def _fetch_pytrends(self) -> list[str]:
        """Try Google Trends via pytrends. Returns topics or empty list (never crashes)."""
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
            return topics
        except Exception as exc:
            console.print(f"    [yellow]pytrends unavailable: {exc}[/yellow]")
            return []
