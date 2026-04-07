"""
video_utils.py -- Helper utilities for the Video Creator Agent.

Provides:
  - TTS generation via edge-tts with word-level timestamps
  - Pexels API video search and download
  - Subtitle frame rendering via Pillow (no ImageMagick needed)
"""

import asyncio
import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Optional

import requests

# ── Constants ─────────────────────────────────────────────────────────────
PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
TTS_VOICE = "en-US-ChristopherNeural"

# Subtitle style
SUBTITLE_FONT_SIZE = 120
SUBTITLE_COLOR = (255, 255, 255)        # white text
SUBTITLE_HIGHLIGHT_COLOR = (255, 255, 0) # pure yellow
SUBTITLE_SHADOW_COLOR = (0, 0, 0, 220)  # semi-transparent heavy black shadow
SUBTITLE_STROKE_WIDTH = 6


# ─────────────────────────────────────────────────────────────────────────────
# 1. TTS — edge-tts with word boundary events
# ─────────────────────────────────────────────────────────────────────────────

class WordBoundary:
    __slots__ = ("word", "start_sec", "end_sec")
    def __init__(self, word: str, start_sec: float, end_sec: float):
        self.word = word
        self.start_sec = start_sec
        self.end_sec = end_sec

    def __repr__(self):
        return f"<Word '{self.word}' {self.start_sec:.2f}-{self.end_sec:.2f}s>"


async def _generate_tts_async(text: str, audio_path: str) -> list[WordBoundary]:
    """
    Generate TTS audio and capture word-level boundary events.
    Returns list of WordBoundary objects with accurate start/end times.
    """
    import edge_tts

    boundaries = []
    communicate = edge_tts.Communicate(text, TTS_VOICE)

    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset and duration are in 100-nanosecond units
                start_sec = chunk["offset"] / 10_000_000
                dur_sec = chunk["duration"] / 10_000_000
                boundaries.append(
                    WordBoundary(
                        word=chunk["text"],
                        start_sec=start_sec,
                        end_sec=start_sec + dur_sec,
                    )
                )
    return boundaries


def generate_tts(text: str, audio_path: str) -> list[WordBoundary]:
    """Synchronous wrapper around the async TTS generator."""
    return asyncio.run(_generate_tts_async(text, audio_path))


def get_audio_duration(audio_path: str) -> float:
    """Return audio duration in seconds using moviepy."""
    from moviepy.editor import AudioFileClip
    clip = AudioFileClip(audio_path)
    dur = clip.duration
    clip.close()
    return dur


def group_boundaries_into_chunks(
    boundaries: list[WordBoundary], words_per_chunk: int = 3
) -> list[dict]:
    """
    Group individual word boundaries into multi-word subtitle chunks.
    Returns list of {"text": str, "start": float, "end": float, "highlight": bool}
    """
    HIGHLIGHT_WORDS = {
        "never", "always", "first", "only", "secret", "hidden", "real", "fake",
        "dead", "billion", "trillion", "impossible", "proven", "shocking", "truth",
        "discovered", "found", "revealed", "warning", "ancient", "ai", "brain",
        "mind", "nobody", "lied", "strangest", "dark", "zero", "infinite",
    }

    chunks = []
    i = 0
    while i < len(boundaries):
        group = boundaries[i : i + words_per_chunk]
        text = " ".join(b.word for b in group).upper()
        highlight = any(b.word.lower() in HIGHLIGHT_WORDS for b in group)
        chunks.append({
            "text": text,
            "start": group[0].start_sec,
            "end": group[-1].end_sec,
            "highlight": highlight,
        })
        i += words_per_chunk
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# 2. Pexels — search and download vertical video clips
# ─────────────────────────────────────────────────────────────────────────────

def search_pexels_video(
    keywords: list[str],
    min_duration: float,
    api_key: str,
    used_ids: Optional[set] = None,
) -> Optional[str]:
    """
    Search Pexels for a vertical video matching the keywords.
    Returns a direct download URL or None.
    """
    query = " ".join(keywords[:3])
    params = {
        "query": query,
        "orientation": "portrait",
        "size": "medium",
        "per_page": 10,
    }
    headers = {"Authorization": api_key}

    try:
        resp = requests.get(PEXELS_SEARCH_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"  [Pexels] Search failed for '{query}': {exc}")
        return None

    videos = data.get("videos", [])
    if not videos:
        # Retry with a shorter, more generic query
        fallback_query = keywords[0] if keywords else "nature"
        params["query"] = fallback_query
        try:
            resp = requests.get(PEXELS_SEARCH_URL, params=params, headers=headers, timeout=15)
            data = resp.json()
            videos = data.get("videos", [])
        except Exception:
            return None

    for video in videos:
        vid_id = video.get("id")
        if used_ids and vid_id in used_ids:
            continue
        if video.get("duration", 0) < min_duration:
            continue
        # Pick best quality file that isn't too large
        files = video.get("video_files", [])
        # Prefer portrait HD files, then SD
        portrait_files = [
            f for f in files
            if f.get("width", 9999) < f.get("height", 0)  # portrait: width < height
        ]
        target_files = portrait_files if portrait_files else files
        # Sort by quality: prefer 1080p > 720p > others
        def quality_score(f):
            h = f.get("height", 0)
            if h >= 1080:
                return 2
            elif h >= 720:
                return 1
            return 0

        target_files.sort(key=quality_score, reverse=True)
        if target_files:
            if used_ids is not None:
                used_ids.add(vid_id)
            return target_files[0]["link"]

    return None


def download_video(url: str, dest_path: str) -> bool:
    """Download a video file from url to dest_path. Returns True on success."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(dest_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
        return True
    except Exception as exc:
        print(f"  [Pexels] Download failed: {exc}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 3. Subtitle rendering — Pillow-based, no ImageMagick required
# ─────────────────────────────────────────────────────────────────────────────

def _load_font(size: int):
    """Load a bold font. Tries common system fonts, falls back to default."""
    from PIL import ImageFont

    candidate_fonts = [
        # Windows
        "C:/Windows/Fonts/ariblk.ttf",   # Arial Black
        "C:/Windows/Fonts/arialbd.ttf",  # Arial Bold
        "C:/Windows/Fonts/impact.ttf",   # Impact
        "C:/Windows/Fonts/calibrib.ttf", # Calibri Bold
        "C:/Windows/Fonts/georgiab.ttf", # Georgia Bold
        "C:/Windows/Fonts/segoeuib.ttf", # Segoe UI Bold
        # Linux / fallbacks
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidate_fonts:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Last resort: PIL default (will look basic but won't crash)
    return ImageFont.load_default()


def render_subtitle_image(
    text: str,
    highlight: bool,
    video_width: int = 1080,
    video_height: int = 1920,
) -> "numpy.ndarray":
    """
    Render a subtitle text card as a numpy RGBA array.
    Positioned at 70% down the screen height.
    """
    import numpy as np
    from PIL import Image, ImageDraw

    # Create transparent canvas matching video dimensions
    img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _load_font(SUBTITLE_FONT_SIZE)

    text_color = SUBTITLE_HIGHLIGHT_COLOR if highlight else SUBTITLE_COLOR

    # Measure text size
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except AttributeError:
        # Older Pillow
        text_w, text_h = draw.textsize(text, font=font)

    # Center horizontally, place at 70% vertical
    x = (video_width - text_w) // 2
    y = int(video_height * 0.70)

    # Shadow / stroke — draw slightly offset in black
    for dx in range(-SUBTITLE_STROKE_WIDTH, SUBTITLE_STROKE_WIDTH + 1):
        for dy in range(-SUBTITLE_STROKE_WIDTH, SUBTITLE_STROKE_WIDTH + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 220))

    # Main text
    draw.text((x, y), text, font=font, fill=(*text_color, 255))

    return np.array(img)
