"""
Agent 11 — Output Packager Agent
Assembles all agent outputs into a single, beautifully formatted markdown document.
Generates: viral title (<60 chars), SEO description, 5–10 hashtags.
Output: { "title": str, "description": str, "hashtags": list[str], "full_markdown": str }
"""
from .base_agent import BaseAgent
from .mock_generator import generate_mock_metadata



class OutputPackagerAgent(BaseAgent):
    name = "OutputPackagerAgent"

    def _execute(self, input_data: dict) -> dict:
        topic: str = input_data.get("selected_topic", "Unknown Topic")
        script: str = input_data.get("script", "")
        hook: str = input_data.get("hook", "")
        cta: str = input_data.get("cta", "")
        scenes: list = input_data.get("scenes", [])
        voice: dict = input_data.get("voice", {})
        audio: dict = input_data.get("audio", {})
        subtitles: list = input_data.get("subtitles", [])
        qc_scores: dict = input_data.get("qc_scores", {})

        # Generate title + description + hashtags via LLM
        meta_prompt = f"""
You are a YouTube Shorts metadata specialist. Generate a viral title, SEO description, and hashtags.

TOPIC: {topic}
HOOK: {hook}
SCRIPT SUMMARY: {script[:300]}

REQUIREMENTS:
Title: Under 60 characters. Clickbait-style but truthful. Use an emoji. Create curiosity.
Description: 2–3 sentences for SEO. Include the core facts. Natural language.
Hashtags: 6–10 tags. Mix niche + broad. Include #Shorts. No spaces in hashtags.

Respond ONLY with JSON:
{{
  "title": "...",
  "description": "...",
  "hashtags": ["#Tag1", "#Tag2"]
}}
"""
        meta = self._call_llm(meta_prompt, mock_response=generate_mock_metadata(topic))

        # Build scene table markdown
        scenes_md = self._format_scenes(scenes)

        # Build subtitles markdown
        subs_md = self._format_subtitles(subtitles)

        # Build SFX list
        sfx = audio.get("sfx", [])
        sfx_md = "\n".join(
            f"  - `{s.get('timestamp_sec', '?')}s` — **{s.get('effect', '')}** _{s.get('purpose', '')}_"
            for s in sfx
        )

        music = audio.get("music", {})

        title = meta.get("title", f"Shorts: {topic[:50]}")
        description = meta.get("description", "")
        hashtags = meta.get("hashtags", [])

        # Assemble full markdown
        full_md = f"""# {title}

---

## 📋 TOPIC
{topic}

---

## 🎬 SCRIPT
```
{script}
```

**Hook:** {hook}
**CTA:** {cta}
**Estimated Duration:** {input_data.get("estimated_duration_sec", "~27")} seconds

---

## 🎞️ SCENE BREAKDOWN

{scenes_md}

---

## 🎤 VOICE STYLE
| Attribute | Value |
|-----------|-------|
| **Tone** | {voice.get('tone', 'N/A')} |
| **Speed** | {voice.get('speed', 'N/A')} |
| **Emotion** | {voice.get('emotion', 'N/A')} |

**Director Notes:** {voice.get('voice_notes', 'N/A')}

---

## 💬 SUBTITLES

{subs_md}

---

## 🎵 MUSIC & SFX

**Background Music:**
- Genre: {music.get('genre', 'N/A')}
- Description: {music.get('description', 'N/A')}
- BPM: {music.get('bpm', 'N/A')}
- Volume: {music.get('volume_level', 'N/A')}
- Search: `{", ".join(music.get('search_keywords', []))}`

**Sound Effects:**
{sfx_md}

---

## 📊 QUALITY SCORES
| Hook Strength | Pacing | Retention | Overall |
|:---:|:---:|:---:|:---:|
| {qc_scores.get('hook_strength', '?')}/10 | {qc_scores.get('pacing', '?')}/10 | {qc_scores.get('retention_potential', '?')}/10 | {input_data.get('qc_overall', '?')}/10 |

---

## 📱 UPLOAD METADATA

**Title:**
{title}

**Description:**
{description}

**Hashtags:**
{" ".join(hashtags)}

---
"""
        return {
            "title": title,
            "description": description,
            "hashtags": hashtags,
            "full_markdown": full_md,
        }

    def _format_scenes(self, scenes: list) -> str:
        if not scenes:
            return "_No scene data._"
        rows = ["| # | Duration | Visual | On-Screen Text | Transition |",
                "|---|----------|--------|----------------|------------|"]
        for s in scenes:
            rows.append(
                f"| {s.get('scene_id', '')} | {s.get('duration_sec', '?')}s "
                f"| {s.get('visual_description', '')[:60]}... "
                f"| **{s.get('on_screen_text', '')}** "
                f"| _{s.get('transition', '')}_  |"
            )
        return "\n".join(rows)

    def _format_subtitles(self, subtitles: list) -> str:
        if not subtitles:
            return "_No subtitle data._"
        cards = []
        for s in subtitles:
            text = s.get("text", "")
            if s.get("highlight"):
                cards.append(f"**`{text}`**")
            else:
                cards.append(f"`{text}`")
        return " → ".join(cards)
