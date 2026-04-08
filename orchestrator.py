"""
Agent 10 -- ORCHESTRATOR (Main Controller)
Coordinates all agents in the correct sequence for each Short:
  Trend -> Filter -> Script -> Visual -> Voice -> Audio -> Subtitle -> QC (retry loop) -> Package -> Approve -> Video
Handles retries, progress display, and memory persistence.
"""
import os
import time
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import box

from agents import (
    TrendAnalystAgent,
    TopicFilterAgent,
    ScriptWriterAgent,
    VisualDirectorAgent,
    VoiceDesignAgent,
    AudioEngineerAgent,
    SubtitleAgent,
    QualityControlAgent,
    MemoryAgent,
    FactCheckerAgent,
    OutputPackagerAgent,
    ApprovalAgent,
    VideoCreatorAgent,
    YouTubeUploaderAgent,
)

console = Console()

MAX_QC_RETRIES = 2       # Max script rewrites before force-passing
MAX_FACT_RETRIES = 2     # Max fact-check rejections before force-passing


class Orchestrator:
    def __init__(self, num_shorts: int = 3):
        self.num_shorts = max(1, min(5, num_shorts))
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Instantiate all agents
        self.trend_analyst = TrendAnalystAgent()
        self.topic_filter = TopicFilterAgent()
        self.script_writer = ScriptWriterAgent()
        self.visual_director = VisualDirectorAgent()
        self.voice_design = VoiceDesignAgent()
        self.audio_engineer = AudioEngineerAgent()
        self.subtitle_agent = SubtitleAgent()
        self.quality_control = QualityControlAgent()
        self.memory_agent = MemoryAgent()
        self.fact_checker = FactCheckerAgent()
        self.output_packager = OutputPackagerAgent()
        self.approval_agent = ApprovalAgent()
        self.video_creator = VideoCreatorAgent()
        self.youtube_uploader = YouTubeUploaderAgent()

        # Check if video rendering is enabled
        self.pexels_key = os.getenv("PEXELS_API_KEY", "")
        self.render_video = bool(self.pexels_key) and os.getenv("SKIP_VIDEO_RENDER", "false").lower() != "true"
        self.upload_youtube = os.getenv("YOUTUBE_UPLOAD_ENABLED", "false").lower() == "true"

    def run(self) -> list[dict]:
        console.print(Panel.fit(
            f"[bold cyan]🎬 YouTube Shorts Multi-Agent System[/bold cyan]\n"
            f"Run ID: [yellow]{self.run_id}[/yellow] | Shorts to generate: [green]{self.num_shorts}[/green]",
            border_style="cyan"
        ))

        results = []
        selected_this_run: list[str] = []

        # ── Step 1: Load memory ─────────────────────────────────────────
        self._log("Memory Agent", "Loading used topics from memory...")
        memory = self.memory_agent.run({"action": "load"})
        used_topics: list[str] = memory.get("used_topics", [])
        console.print(f"  [dim]Previously used topics: {len(used_topics)}[/dim]")

        # ── Step 2: Trend analysis (done ONCE for all shorts) ──────────
        self._log("Trend Analyst", "Discovering trending topics...")
        time.sleep(2)  # Tiny delay to avoid hitting RPM/TPM quota too fast
        trend_data = self.trend_analyst.run({})
        console.print(f"  [dim]Found {len(trend_data.get('topics', []))} topics to rank[/dim]")

        # ── Generate each Short ─────────────────────────────────────────
        for i in range(1, self.num_shorts + 1):
            console.print(f"\n[bold magenta]{'═'*55}[/bold magenta]")
            console.print(f"[bold magenta]  SHORT #{i} of {self.num_shorts}[/bold magenta]")
            console.print(f"[bold magenta]{'═'*55}[/bold magenta]\n")

            try:
                result = self._generate_single_short(
                    short_index=i,
                    trend_data=trend_data,
                    used_topics=used_topics,
                    selected_this_run=selected_this_run,
                )
                results.append(result)
                # Track topic used in this run to avoid immediate repeats
                selected_this_run.append(result.get("topic", ""))

                # Save to memory immediately after each Short
                self.memory_agent.run({
                    "action": "save",
                    "topic": result.get("topic", ""),
                    "metadata": {
                        "title": result.get("title", ""),
                        "file_path": result.get("file_path", ""),
                        "run_id": self.run_id,
                    },
                })

            except Exception as exc:
                console.print(f"[red]✗ Short #{i} failed: {exc}[/red]")
                results.append({"error": str(exc), "short_index": i})

        # ── Final Summary ───────────────────────────────────────────────
        self._print_summary(results)
        return results

    def _generate_single_short(
        self,
        short_index: int,
        trend_data: dict,
        used_topics: list[str],
        selected_this_run: list[str],
    ) -> dict:

        # ── Agent 2: Topic Filter ───────────────────────────────────────
        self._log("Topic Filter", "Selecting best unused topic...")
        time.sleep(2)
        topic_data = self.topic_filter.run({
            "topics": trend_data.get("topics", []),
            "used_topics": used_topics,
            "exclude_this_run": selected_this_run,
        })
        topic = topic_data["selected_topic"]
        console.print(f"  [green]✓ Topic:[/green] [bold]{topic}[/bold] (score: {topic_data.get('score', '?')}/10)")

        # ── Agent 3: Script Writer + QC retry loop ─────────────────────
        script_data = None
        qc_result = None
        qc_feedback = ""

        for qc_attempt in range(1, MAX_QC_RETRIES + 2):
            force_pass = qc_attempt > MAX_QC_RETRIES

            if force_pass:
                self._log("Script Writer", "[yellow]Force-passing QC after max retries[/yellow]")

            self._log("Script Writer", f"Writing script (attempt {qc_attempt})...")
            time.sleep(2)
            script_data = self.script_writer.run({
                "selected_topic": topic,
                "qc_feedback": qc_feedback,
            })
            console.print(f"  [green]✓ Script written[/green] ({script_data.get('estimated_duration_sec', '?')}s estimated)")

            # ── Agent 8: Quality Control ────────────────────────────────
            self._log("Quality Control", f"Reviewing script (attempt {qc_attempt})...")
            time.sleep(2)
            qc_result = self.quality_control.run({
                "selected_topic": topic,
                "script": script_data.get("script", ""),
                "hook": script_data.get("hook", ""),
                "cta": script_data.get("cta", ""),
                "qc_attempt": qc_attempt,
                "force_pass": force_pass,
            })

            scores = qc_result.get("scores", {})
            overall = qc_result.get("overall_score", 0)
            approved = qc_result.get("approved", False)

            score_str = f"Hook:{scores.get('hook_strength','?')} Pacing:{scores.get('pacing','?')} Retention:{scores.get('retention_potential','?')} → Overall:{overall}"
            if approved:
                console.print(f"  [bold green]✓ QC PASSED[/bold green] [{score_str}]")
                break
            else:
                qc_feedback = qc_result.get("feedback", "")
                console.print(f"  [yellow]⚠ QC FAILED (attempt {qc_attempt})[/yellow] [{score_str}]")
                console.print(f"  [dim]Feedback: {qc_feedback[:120]}...[/dim]")
                if force_pass:
                    break

        # ── Agent 15: Fact Checker (post-QC verification) ───────────────
        for fact_attempt in range(1, MAX_FACT_RETRIES + 2):
            self._log("Fact Checker", f"Verifying script claims (attempt {fact_attempt})...")
            time.sleep(1)
            fact_result = self.fact_checker.run({
                "script": script_data.get("script", ""),
                "selected_topic": topic,
            })

            is_verified = fact_result.get("verified", True)
            claims = fact_result.get("claims", [])
            false_claims = [c for c in claims if c.get("verdict") == "FALSE"]
            true_claims = [c for c in claims if c.get("verdict") == "TRUE"]

            console.print(
                f"  [dim]Claims: {len(true_claims)} verified, "
                f"{len(false_claims)} false, "
                f"{len(claims) - len(true_claims) - len(false_claims)} unverifiable[/dim]"
            )

            if is_verified or not false_claims:
                console.print(f"  [bold green]✓ FACT CHECK PASSED[/bold green] — {fact_result.get('summary', '')}")
                break
            else:
                # Show what's wrong
                for fc in false_claims:
                    console.print(f"  [red]✗ FALSE:[/red] {fc.get('claim', '')[:80]}")
                    if fc.get("correction"):
                        console.print(f"    [green]→ Correct:[/green] {fc['correction'][:80]}")

                if fact_attempt > MAX_FACT_RETRIES:
                    console.print("  [yellow]⚠ Force-passing fact check after max retries[/yellow]")
                    break

                # Rewrite the script with corrections
                corrections = fact_result.get("corrected_facts", "")
                if not corrections:
                    corrections = "; ".join(
                        f"{c['claim']} → {c['correction']}" for c in false_claims if c.get('correction')
                    )

                self._log("Script Writer", f"Rewriting script with fact corrections (attempt {fact_attempt})...")
                time.sleep(2)
                script_data = self.script_writer.run({
                    "selected_topic": topic,
                    "qc_feedback": f"FACT CHECK FAILED — fix these false claims: {corrections}",
                })
                console.print(f"  [green]✓ Script rewritten with corrections[/green]")

        # ── Agent 4: Visual Director ────────────────────────────────────
        self._log("Visual Director", "Creating scene breakdown...")
        time.sleep(2)
        visual_data = self.visual_director.run({
            "selected_topic": topic,
            "script": script_data.get("script", ""),
        })
        console.print(f"  [green]✓[/green] {len(visual_data.get('scenes', []))} scenes planned")

        # ── Agent 5: Voice Design ───────────────────────────────────────
        self._log("Voice Design", "Defining narration style...")
        time.sleep(2)
        voice_data = self.voice_design.run({
            "selected_topic": topic,
            "script": script_data.get("script", ""),
            "hook": script_data.get("hook", ""),
        })
        console.print(f"  [green]✓[/green] Tone: {voice_data.get('tone', 'N/A')}")

        # ── Agent 6: Audio Engineer ─────────────────────────────────────
        self._log("Audio Engineer", "Selecting music & SFX...")
        time.sleep(2)
        audio_data = self.audio_engineer.run({
            "selected_topic": topic,
            "tone": voice_data.get("tone", ""),
            "emotion": voice_data.get("emotion", ""),
            "scenes": visual_data.get("scenes", []),
        })
        console.print(f"  [green]✓[/green] Music: {audio_data.get('music', {}).get('genre', 'N/A')}")

        # ── Agent 7: Subtitles ──────────────────────────────────────────
        self._log("Subtitle Agent", "Generating subtitle cards...")
        time.sleep(2)
        subtitle_data = self.subtitle_agent.run({
            "script": script_data.get("script", ""),
        })
        subs = subtitle_data.get("subtitles", [])
        console.print(f"  [green]✓[/green] {len(subs)} subtitle cards generated")

        # ── Agent 11: Output Packager ───────────────────────────────────
        self._log("Output Packager", "Compiling final output...")
        time.sleep(2)
        package_data = self.output_packager.run({
            "selected_topic": topic,
            "script": script_data.get("script", ""),
            "hook": script_data.get("hook", ""),
            "cta": script_data.get("cta", ""),
            "estimated_duration_sec": script_data.get("estimated_duration_sec", 27),
            "scenes": visual_data.get("scenes", []),
            "voice": voice_data,
            "audio": audio_data,
            "subtitles": subs,
            "qc_scores": qc_result.get("scores", {}),
            "qc_overall": qc_result.get("overall_score", "?"),
        })

        # ── Agent 12: Approval ──────────────────────────────────────────
        self._log("Approval Agent", "Stamping READY_FOR_REVIEW...")
        time.sleep(2)
        approval_data = self.approval_agent.run({
            "full_markdown": package_data.get("full_markdown", ""),
            "title": package_data.get("title", topic[:50]),
            "run_id": self.run_id,
            "short_index": short_index,
        })

        file_path = approval_data.get("file_path", "")
        console.print(f"\n  [bold green]SHORT #{short_index} READY_FOR_REVIEW[/bold green]")
        console.print(f"  [dim]Script saved: {file_path}[/dim]")

        # ── Agent 13: Video Creator (optional) ─────────────────────────
        video_path = None
        video_status = "SKIPPED"
        if self.render_video:
            self._log("Video Creator", "Rendering MP4 video...")
            video_result = self.video_creator.run({
                "selected_topic": topic,
                "script": script_data.get("script", ""),
                "scenes": visual_data.get("scenes", []),
                "title": package_data.get("title", topic[:50]),
                "run_id": self.run_id,
                "short_index": short_index,
                "pexels_api_key": self.pexels_key,
            })
            video_status = video_result.get("status", "VIDEO_FAILED")
            video_path = video_result.get("video_path")
            if video_status == "VIDEO_RENDERED":
                console.print(f"  [bold green]  Video:[/bold green] {os.path.basename(video_path)}")
            else:
                console.print(f"  [yellow]  Video skipped: {video_result.get('reason', '')}[/yellow]")
        else:
            if not self.pexels_key:
                console.print("  [dim]  Video rendering skipped (add PEXELS_API_KEY to .env to enable)[/dim]")
            else:
                console.print("  [dim]  Video rendering skipped (SKIP_VIDEO_RENDER=true)[/dim]")

        # ── Agent 14: YouTube Uploader ──────────────────────────────────
        upload_data = {"status": "SKIPPED"}
        if video_path and self.upload_youtube:
            upload_data = self.youtube_uploader.run({
                "video_path": video_path,
                "title": package_data.get("title", ""),
                "script": script_data.get("script", ""),
                "selected_topic": topic,
            })

        return {
            "short_index": short_index,
            "topic": topic,
            "title": package_data.get("title", ""),
            "file_path": file_path,
            "video_path": video_path,
            "video_status": video_status,
            "upload_status": upload_data.get("status", "SKIPPED"),
            "upload_url": upload_data.get("url", ""),
            "qc_score": qc_result.get("overall_score", 0),
            "status": "READY_FOR_REVIEW",
        }

    def _log(self, agent_name: str, message: str) -> None:
        console.print(f"  [cyan][{agent_name}][/cyan] {message}")

    def _print_summary(self, results: list[dict]) -> None:
        console.print(f"\n[bold cyan]{'='*55}[/bold cyan]")
        console.print("[bold cyan]  PIPELINE COMPLETE -- SUMMARY[/bold cyan]")
        console.print(f"[bold cyan]{'='*55}[/bold cyan]\n")

        table = Table(box=box.ROUNDED, border_style="cyan", show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Topic", min_width=28)
        table.add_column("QC", justify="center", width=6)
        table.add_column("Script", justify="center", width=8)
        table.add_column("Video", justify="center", width=12)
        table.add_column("YouTube", justify="center", width=12)

        for r in results:
            if "error" in r:
                table.add_row(
                    str(r.get("short_index", "?")),
                    "[red]FAILED[/red]",
                    "--", "[red]ERROR[/red]",
                    r.get("error", "")[:30],
                )
            else:
                vs = r.get("video_status", "SKIPPED")
                if vs == "VIDEO_RENDERED":
                    video_col = "[bold green]RENDERED[/bold green]"
                elif vs == "SKIPPED":
                    video_col = "[dim]SKIPPED[/dim]"
                else:
                    video_col = "[dim]FAILED[/dim]"
                
                us = r.get("upload_status", "SKIPPED")
                if us == "UPLOAD_SUCCESSFUL":
                    upload_col = "[bold green]UPLOADED[/bold green]"
                elif us == "UPLOAD_FAILED":
                    upload_col = "[red]FAILED[/red]"
                else:
                    upload_col = "[dim]SKIPPED[/dim]"

                table.add_row(
                    str(r.get("short_index", "?")),
                    r.get("topic", "")[:35],
                    f"{r.get('qc_score', '?')}/10",
                    "[bold green]READY[/bold green]",
                    video_col,
                    upload_col,
                )

        console.print(table)
        # Print file paths
        console.print()
        for r in results:
            if "error" not in r:
                console.print(f"  [dim]Script: {r.get('file_path', '')}[/dim]")
                if r.get("video_path"):
                    console.print(f"  [green]Video:  {r.get('video_path', '')}[/green]")
        console.print(f"\n[dim]Output directory: output/{self.run_id}/[/dim]\n")

