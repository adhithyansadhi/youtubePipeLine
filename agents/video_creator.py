"""
Agent 13 -- Video Creator Agent
Takes the packaged Short output and renders a real 1080x1920 MP4 video.

Pipeline:
  1. Generate voiceover (edge-tts, en-US-ChristopherNeural) + word timestamps
  2. Download Pexels vertical clips per scene
  3. Resize/crop each clip to 1080x1920
  4. Loop/trim clips to proportionally match audio duration
  5. Concatenate all clips
  6. Overlay burned-in subtitles (Pillow-rendered, word-by-word chunks)
  7. Mux video + voiceover audio
  8. Export MP4, clean up temp files

Input keys:
  - selected_topic, script, hook, scenes (list), subtitles (list)
  - title, run_id, short_index
  - pexels_api_key

Output:
  - { "status": "VIDEO_RENDERED", "video_path": str }
  - { "status": "VIDEO_SKIPPED", "reason": str }
"""

import os
import shutil
import tempfile
import time
from pathlib import Path

# ── Pillow 10+ / MoviePy 1.0.3 compatibility shim ───────────────────────
# MoviePy 1.0.3 uses PIL.Image.ANTIALIAS which was removed in Pillow 10.
# Patch it back before MoviePy is imported anywhere.
try:
    from PIL import Image as _PILImage
    if not hasattr(_PILImage, "ANTIALIAS"):
        _PILImage.ANTIALIAS = _PILImage.LANCZOS  # LANCZOS is the modern equivalent
except Exception:
    pass
# ─────────────────────────────────────────────────────────────────────────

from rich.console import Console

from .base_agent import BaseAgent

console = Console()

# Output directory (relative to this file's parent)
OUTPUT_DIR = Path(__file__).parent.parent / "output"


class VideoCreatorAgent(BaseAgent):
    name = "VideoCreatorAgent"
    MAX_RETRIES = 1  # Video rendering is slow; don't retry on soft errors

    def _execute(self, input_data: dict) -> dict:
        pexels_key = input_data.get("pexels_api_key", "") or os.getenv("PEXELS_API_KEY", "")
        if not pexels_key:
            return {"status": "VIDEO_SKIPPED", "reason": "PEXELS_API_KEY not set"}

        # Validate deps early
        missing = self._check_dependencies()
        if missing:
            return {"status": "VIDEO_SKIPPED", "reason": f"Missing packages: {', '.join(missing)}"}

        script: str = input_data.get("script", "")
        scenes: list = input_data.get("scenes", [])
        run_id: str = input_data.get("run_id", "unknown")
        short_index: int = input_data.get("short_index", 1)
        title: str = input_data.get("title", f"short_{short_index:02d}")

        if not script or not scenes:
            return {"status": "VIDEO_SKIPPED", "reason": "No script or scenes provided"}

        # Create temp working directory
        tmp_dir = Path(tempfile.mkdtemp(prefix="yt_short_"))
        run_output_dir = OUTPUT_DIR / run_id
        run_output_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize title for filename
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)
        safe = safe.strip().replace(" ", "_")[:40]
        video_path = str(run_output_dir / f"short_{short_index:02d}_{safe}.mp4")

        try:
            return self._render(
                script=script,
                scenes=scenes,
                pexels_key=pexels_key,
                tmp_dir=tmp_dir,
                video_path=video_path,
            )
        except Exception as exc:
            console.print(f"  [VideoCreatorAgent] Render error: {exc}")
            return {"status": "VIDEO_FAILED", "reason": str(exc)}
        finally:
            # Always clean up temp files
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # ── Core Render Pipeline ─────────────────────────────────────────────

    def _render(
        self,
        script: str,
        scenes: list,
        pexels_key: str,
        tmp_dir: Path,
        video_path: str,
    ) -> dict:
        from .video_utils import (
            generate_tts,
            get_audio_duration,
            group_boundaries_into_chunks,
            search_pexels_video,
            download_video,
            render_subtitle_image,
        )
        from moviepy.editor import (
            VideoFileClip,
            AudioFileClip,
            ImageClip,
            CompositeVideoClip,
            concatenate_videoclips,
        )
        import numpy as np

        VIDEO_W, VIDEO_H = 1080, 1920
        FPS = 30

        # ── Step 1: Generate voiceover ──────────────────────────────────
        console.print("    [dim]Generating voiceover (edge-tts)...[/dim]")
        audio_path = str(tmp_dir / "voiceover.mp3")
        boundaries = generate_tts(script, audio_path)
        audio_duration = get_audio_duration(audio_path)
        console.print(f"    [dim]Audio: {audio_duration:.1f}s, {len(boundaries)} word boundaries[/dim]")

        # ── Step 2: Calculate per-scene clip durations ──────────────────
        # Use director's suggested durations, scaled to match actual audio
        raw_durations = [float(s.get("duration_sec", 4)) for s in scenes]
        total_raw = sum(raw_durations)
        if total_raw <= 0:
            total_raw = len(scenes) * 4
        scale = audio_duration / total_raw
        clip_durations = [d * scale for d in raw_durations]

        # ── Step 3: Download clips from Pexels ─────────────────────────
        console.print("    [dim]Fetching stock footage from Pexels...[/dim]")
        used_pexels_ids: set = set()
        video_clips = []
        fallback_keywords = ["nature", "city", "technology", "abstract", "sky", "people"]

        # ── Step 3: Download clips from Pexels ─────────────────────────
        console.print("    [dim]Fetching stock footage from Pexels...[/dim]")
        used_pexels_ids: set = set()
        video_clips = []
        raw_clips_to_close = []
        fallback_keywords = ["nature", "city", "technology", "abstract", "sky", "people"]

        for idx, (scene, target_dur) in enumerate(zip(scenes, clip_durations)):
            keywords = scene.get("stock_keywords", []) or fallback_keywords
            clip_path = str(tmp_dir / f"clip_{idx:02d}.mp4")

            # Try the scene keywords, then fallback
            url = search_pexels_video(keywords, min_duration=max(3, target_dur), api_key=pexels_key, used_ids=used_pexels_ids)
            if not url:
                url = search_pexels_video(fallback_keywords[idx % len(fallback_keywords):idx % len(fallback_keywords) + 1],
                                          min_duration=3, api_key=pexels_key, used_ids=used_pexels_ids)
            if not url:
                console.print(f"    [yellow]  Scene {idx+1}: no Pexels clip found, skipping[/yellow]")
                continue

            console.print(f"    [dim]  Scene {idx+1}/{len(scenes)}: downloading...[/dim]")
            if not download_video(url, clip_path):
                continue

            # Rate limit safety
            time.sleep(0.3)

            # Load and process clip
            try:
                # IMPORTANT: Keep raw open until the final render is done
                raw = VideoFileClip(clip_path, audio=False)
                raw_clips_to_close.append(raw)
                
                processed = self._resize_crop(raw, VIDEO_W, VIDEO_H)
                # Trim or loop to target duration
                processed = self._fit_duration(processed, target_dur, FPS)
                video_clips.append(processed)
            except Exception as clip_err:
                console.print(f"    [yellow]  Scene {idx+1} clip error: {clip_err}[/yellow]")
                continue

        if not video_clips:
            raise RuntimeError("No video clips could be successfully downloaded or processed.")

        # ── Step 4: Concatenate clips ───────────────────────────────────
        console.print("    [dim]Concatenating clips...[/dim]")
        # method="chain" is faster than "compose" since we pre-processed sizes
        base_video = concatenate_videoclips(video_clips, method="chain")

        # Ensure base_video duration matches audio exactly
        if base_video.duration < audio_duration:
            # Loop last clip to fill gap
            gap = audio_duration - base_video.duration
            last = video_clips[-1].subclip(0, min(gap, video_clips[-1].duration))
            base_video = concatenate_videoclips([base_video, last], method="chain")
        base_video = base_video.subclip(0, audio_duration)

        # ── Step 5: Build subtitle overlays ────────────────────────────
        console.print("    [dim]Building subtitle overlays...[/dim]")
        subtitle_chunks = group_boundaries_into_chunks(boundaries, words_per_chunk=3)
        sub_clips = []

        for chunk in subtitle_chunks:
            start = chunk["start"]
            end = min(chunk["end"], audio_duration)
            if end <= start:
                continue
            frame = render_subtitle_image(
                text=chunk["text"],
                highlight=chunk["highlight"],
                video_width=VIDEO_W,
                video_height=VIDEO_H,
            )
            img_clip = (
                ImageClip(frame, transparent=True)
                .set_start(start)
                .set_end(end)
                .set_duration(end - start)
            )
            sub_clips.append(img_clip)

        # ── Step 6: Composite video + subtitles ─────────────────────────
        console.print("    [dim]Compositing video + subtitles...[/dim]")
        layers = [base_video] + sub_clips
        final_video = CompositeVideoClip(layers, size=(VIDEO_W, VIDEO_H))

        # ── Step 7: Set audio ───────────────────────────────────────────
        console.print("    [dim]Muxing audio...[/dim]")
        voiceover = AudioFileClip(audio_path)
        final_video = final_video.set_audio(voiceover)
        final_video = final_video.set_duration(audio_duration)

        # ── Step 8: Export ──────────────────────────────────────────────
        console.print(f"    [dim]Exporting MP4 to {os.path.basename(video_path)}...[/dim]")
        final_video.write_videofile(
            video_path,
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",   # Much faster than "fast"
            threads=8,            # Increased threads for multi-core speedup
            logger=None,
        )

        # Close all clips to free memory
        for c in video_clips:
            try:
                c.close()
            except Exception:
                pass
        for c in raw_clips_to_close:
            try:
                c.close()
            except Exception:
                pass
        voiceover.close()
        final_video.close()

        console.print(f"  [bold green]  Video rendered:[/bold green] {os.path.basename(video_path)}")
        return {"status": "VIDEO_RENDERED", "video_path": video_path}

    # ── Video Processing Helpers ─────────────────────────────────────────

    def _resize_crop(self, clip, target_w: int, target_h: int):
        """Resize and center-crop a clip to target_w x target_h (1080x1920)."""
        from moviepy.video.fx.all import crop

        clip_w, clip_h = clip.size
        target_ratio = target_w / target_h      # 0.5625 = 9:16
        clip_ratio = clip_w / clip_h

        if clip_ratio > target_ratio:
            # Clip is too wide → scale by height, then crop width
            new_h = target_h
            new_w = int(clip_w * (target_h / clip_h))
            resized = clip.resize((new_w, new_h))
            x_center = new_w / 2
            cropped = crop(resized, width=target_w, x_center=x_center)
        else:
            # Clip is too tall → scale by width, then crop height
            new_w = target_w
            new_h = int(clip_h * (target_w / clip_w))
            resized = clip.resize((new_w, new_h))
            y_center = new_h / 2
            cropped = crop(resized, height=target_h, y_center=y_center)

        return cropped

    def _fit_duration(self, clip, target_dur: float, fps: int):
        """Trim clip if too long, or loop if too short, to match target_dur."""
        if clip.duration >= target_dur:
            return clip.subclip(0, target_dur)
        else:
            # Loop the clip
            from moviepy.video.fx.all import loop
            loops_needed = int(target_dur / clip.duration) + 1
            looped = loop(clip, n=loops_needed)
            return looped.subclip(0, target_dur)

    def _check_dependencies(self) -> list[str]:
        """Return list of missing required packages."""
        missing = []
        for pkg in ["edge_tts", "moviepy", "PIL", "imageio_ffmpeg"]:
            pkg_name = "PIL" if pkg == "PIL" else pkg
            try:
                __import__(pkg_name)
            except ImportError:
                missing.append(pkg.replace("_", "-"))
        return missing
