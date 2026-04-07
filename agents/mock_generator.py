"""
mock_generator.py
Generates topic-specific mock responses for all agents when MOCK_MODE=true.
This ensures each Short has unique, relevant content even without a real API key.
All patterns vary based on the topic string so repeated runs produce different outputs.
"""
import hashlib
import random


# ── Hook templates (slot: {topic_short}) ───────────────────────────────────
HOOK_TEMPLATES = [
    "Most people have no idea that {topic_short} is this mind-blowing.",
    "Scientists discovered something about {topic_short} that changes everything.",
    "No one talks about this, but {topic_short} will leave you speechless.",
    "Here's what they never taught you about {topic_short}.",
    "This fact about {topic_short} kept me up at night.",
    "The truth about {topic_short} is stranger than fiction.",
    "You've been lied to about {topic_short} your entire life.",
    "In 30 seconds, {topic_short} will make complete sense to you.",
]

# ── Value body templates ────────────────────────────────────────────────────
VALUE_TEMPLATES = [
    (
        "Here's the part that blows people's minds.\n\n"
        "The scale of what's happening with {topic} goes far beyond what mainstream media covers.\n\n"
        "Researchers have been documenting this for years.\n\n"
        "And every time new data comes out, the numbers are more extreme than before.\n\n"
        "We're talking about something that affects every single person on Earth."
    ),
    (
        "Let's break this down simply.\n\n"
        "{topic} isn't just a trend — it's a fundamental shift.\n\n"
        "The data has been clear for over a decade.\n\n"
        "Yet the majority of people still don't know it exists.\n\n"
        "That's by design. Complex things get buried under noise."
    ),
    (
        "The numbers tell a story that's hard to ignore.\n\n"
        "When it comes to {topic}, what we see on the surface is just 1% of reality.\n\n"
        "The other 99% is what experts spend their careers trying to understand.\n\n"
        "And when they DO understand it — they can't stop talking about it.\n\n"
        "Because it rewires how you see everything."
    ),
    (
        "Here's what the research actually shows.\n\n"
        "{topic} operates on a scale that our brains literally weren't built to comprehend.\n\n"
        "Think about the biggest number you can imagine.\n\n"
        "Now multiply it.\n\n"
        "Still not close."
    ),
]

# ── Pattern interrupt sentences ─────────────────────────────────────────────
INTERRUPT_TEMPLATES = [
    "But here's where it gets strange.",
    "And then the twist nobody expected happened.",
    "Wait — it gets even more unsettling.",
    "Now flip everything you just heard.",
    "Here's what nobody wants to admit.",
    "This is where mainstream understanding falls apart.",
]

# ── Endings ─────────────────────────────────────────────────────────────────
ENDING_TEMPLATES = [
    "Once you know this, you can never un-know it.",
    "And scientists still don't fully understand why.",
    "The implications of this are still being figured out.",
    "We're living through history and most people don't even notice.",
    "This changes the question from 'if' to 'when'.",
]

# ── CTAs ────────────────────────────────────────────────────────────────────
CTA_TEMPLATES = [
    "Comment the one fact that shocked you most.",
    "Follow for more facts that actually matter.",
    "Drop a comment if this changed how you think.",
    "Subscribe — more like this every day.",
    "Share this with someone who needs to see it.",
    "Tell me in the comments: did you already know this?",
]

# ── Scene visual types ──────────────────────────────────────────────────────
SCENE_VISUALS = [
    ("Dramatic zoom into a dark space with glowing text overlay", "dark dramatic text reveal", "glitch cut"),
    ("Fast-cut montage of data visualizations and graphs", "data visualization animation", "whip pan"),
    ("Split screen: expert on left, visual proof on right", "split screen comparison", "flash cut"),
    ("Time-lapse footage showing scale and movement", "time lapse nature science", "zoom in"),
    ("Close-up of a human face registering shock, slow motion", "slow motion reaction person", "smash cut"),
    ("Aerial drone shot revealing massive scale", "aerial drone wide shot", "fade"),
    ("3D animation of a concept building and expanding", "3d animation concept explainer", "zoom out"),
    ("Archival footage with color-graded high contrast filter", "archival documentary vintage", "flash cut"),
]

# ── Music genres ────────────────────────────────────────────────────────────
MUSIC_GENRES = [
    ("Dark cinematic suspense", "cinematic dark tension royalty free", 95),
    ("Lo-fi hip hop with subtle urgency", "lo-fi documentary beat royalty free", 85),
    ("Orchestral swell building to climax", "orchestral cinematic build royalty free", 110),
    ("Synth-wave mystery pulse", "synthwave mystery atmospheric royalty free", 100),
    ("Ambient electronic with deep bass", "ambient electronic dark royalty free", 80),
]


def _seed(topic: str) -> random.Random:
    """Return a seeded Random instance so the same topic always produces the same mock output."""
    h = int(hashlib.md5(topic.encode()).hexdigest(), 16)
    return random.Random(h)


def _topic_short(topic: str) -> str:
    """Return a short version of the topic (first 5 words max)."""
    words = topic.replace("—", "").replace("-", "").split()
    return " ".join(words[:5])


# ── Public mock generators (one per agent) ─────────────────────────────────

def generate_mock_script(topic: str) -> dict:
    rng = _seed(topic)
    ts = _topic_short(topic)

    hook = rng.choice(HOOK_TEMPLATES).format(topic_short=ts)
    body = rng.choice(VALUE_TEMPLATES).format(topic=topic)
    interrupt = rng.choice(INTERRUPT_TEMPLATES)
    ending = rng.choice(ENDING_TEMPLATES)
    cta = rng.choice(CTA_TEMPLATES)

    script = f"{hook}\n\n{body}\n\n{interrupt}\n\n{ending}\n\n{cta}"
    return {
        "hook": hook,
        "script": script,
        "cta": cta,
        "estimated_duration_sec": rng.randint(24, 30),
    }


def generate_mock_scenes(topic: str, script: str) -> dict:
    rng = _seed(topic + "scenes")
    ts = _topic_short(topic)

    # Pick 6 scene types randomly (seeded)
    selected = rng.sample(SCENE_VISUALS, min(6, len(SCENE_VISUALS)))
    on_screen_texts = [
        ts.upper()[:30],
        "THE NUMBERS ARE STAGGERING",
        "NOBODY TALKS ABOUT THIS",
        "HERE'S THE PROOF",
        "WAIT FOR IT...",
        "NOW YOU KNOW",
    ]

    scenes = []
    for i, (visual, stock_kw, transition) in enumerate(selected, 1):
        scenes.append({
            "scene_id": i,
            "duration_sec": rng.randint(2, 4),
            "visual_description": f"{visual} — related to: {ts}",
            "stock_keywords": [stock_kw, ts.lower(), "documentary style"],
            "on_screen_text": on_screen_texts[i - 1],
            "transition": transition,
        })
    return {"scenes": scenes}


def generate_mock_voice(topic: str) -> dict:
    rng = _seed(topic + "voice")
    tones = [
        ("Deep documentary authority", "Moderate-fast with dramatic pauses", "Calm urgency"),
        ("Mysterious and whispery", "Fast-clear 1.2x pacing", "High curiosity"),
        ("Energetic and punchy", "Fast 1.3x — no pauses", "Excitement"),
        ("Conversational but urgent", "Natural pace with emphasis drops", "Relatable shock"),
        ("Cinematic narrator", "Slow and precise", "Awe and wonder"),
    ]
    tone, speed, emotion = rng.choice(tones)
    ts = _topic_short(topic)
    return {
        "tone": tone,
        "speed": speed,
        "emotion": emotion,
        "voice_notes": (
            f"Open with a measured, confident delivery on the hook about {ts}. "
            "Build pace through the value section. "
            "Slow and emphasize the pattern interrupt — let it land. "
            "Deliver the CTA directly into camera with eye contact energy."
        ),
    }


def generate_mock_audio(topic: str) -> dict:
    rng = _seed(topic + "audio")
    genre, search_kw, bpm = rng.choice(MUSIC_GENRES)
    sfx_options = [
        (1, "Deep impact boom", "Hook entrance"),
        (5, "Whoosh transition", "Scene change"),
        (10, "Subtle notification ping", "Fact emphasis"),
        (16, "Vinyl scratch / record stop", "Pattern interrupt"),
        (22, "Rising tension swell", "Build to ending"),
        (27, "Click / tap sound", "CTA energy"),
    ]
    sfx = [{"timestamp_sec": t, "effect": e, "purpose": p} for t, e, p in rng.sample(sfx_options, 4)]
    return {
        "music": {
            "genre": genre,
            "description": f"Background track that complements the topic of {_topic_short(topic)}. Sits low under the voice.",
            "bpm": f"{bpm} BPM",
            "volume_level": "25-30% of voice volume",
            "search_keywords": [search_kw, "background music no copyright"],
        },
        "sfx": sorted(sfx, key=lambda x: x["timestamp_sec"]),
    }


def generate_mock_subtitles(topic: str, script: str) -> dict:
    """Generate subtitle cards from the actual script text."""
    import re
    # Highlight triggers
    HIGHLIGHT = {
        "never", "always", "first", "only", "secret", "hidden", "real", "fake",
        "dead", "billion", "trillion", "impossible", "proven", "shocking", "truth",
        "discovered", "found", "revealed", "warning", "ancient", "ai", "brain",
        "mind", "insane", "nobody", "lied", "strangest", "stranger", "dark",
    }
    words = re.sub(r"[^\w\s?.]", "", script.upper()).split()
    subtitles = []
    i = 0
    while i < len(words):
        chunk = words[i: i + 3]
        text = " ".join(chunk)
        highlight = any(w.lower() in HIGHLIGHT for w in chunk)
        subtitles.append({"text": text, "highlight": highlight, "start_word": chunk[0] if chunk else ""})
        i += 3
    return {"subtitles": subtitles}


def generate_mock_qc(topic: str, attempt: int) -> dict:
    """QC fails on attempt 1, passes on attempt 2+ to exercise the retry loop."""
    rng = _seed(topic + f"qc{attempt}")
    if attempt == 1:
        hook_score = rng.randint(4, 6)
        pacing = rng.randint(5, 7)
        retention = rng.randint(4, 6)
        overall = round((hook_score + pacing + retention) / 3, 1)
        feedbacks = [
            f"Hook is weak — it doesn't create instant curiosity about {_topic_short(topic)}. Rewrite it as a more shocking question or contradiction. The middle section is too generic — add a specific, surprising stat. End with a stronger punchline.",
            f"The script opens too slowly. Lead with the most surprising fact about {_topic_short(topic)} in the first 3 words. Tighten the value section — cut 30% of the words. Add a sharper pattern interrupt before the ending.",
            f"Retention risk: sentences are too long. Chop everything to 8 words max. The hook about {_topic_short(topic)} is a statement — make it a question instead. The CTA is forgettable, rewrite it with urgency.",
        ]
        return {
            "approved": False,
            "scores": {"hook_strength": hook_score, "pacing": pacing, "retention_potential": retention},
            "overall_score": overall,
            "feedback": rng.choice(feedbacks),
        }
    else:
        hook_score = rng.randint(7, 9)
        pacing = rng.randint(7, 10)
        retention = rng.randint(7, 9)
        overall = round((hook_score + pacing + retention) / 3, 1)
        return {
            "approved": True,
            "scores": {"hook_strength": hook_score, "pacing": pacing, "retention_potential": retention},
            "overall_score": overall,
            "feedback": "",
        }


def generate_mock_metadata(topic: str) -> dict:
    rng = _seed(topic + "meta")
    ts = _topic_short(topic)
    titles = [
        f"The Dark Truth About {ts} ✨",
        f"Nobody Talks About {ts} (Here's Why) 🤫",
        f"What They Hid About {ts} 🔍",
        f"{ts} Will Change How You See Everything 🌍",
        f"The {ts} Secret Nobody Wanted You to Know 💀",
    ]
    title = rng.choice(titles)[:59]  # Enforce <60 chars
    description = (
        f"Most people have no idea about the real story behind {topic}. "
        f"In this Short, we break down the key facts that mainstream media ignores. "
        f"Once you learn this, you'll never see things the same way again."
    )
    hashtag_base = ts.replace(" ", "").replace("—", "").replace("-", "")
    hashtags = [
        f"#{hashtag_base[:20]}",
        "#Shorts",
        "#Facts",
        "#LearnOnTikTok",
        "#MindBlown",
        "#DidYouKnow",
        "#Science",
        "#History",
    ]
    return {"title": title, "description": description, "hashtags": hashtags}
