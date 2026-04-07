"""
Agent 12 — Approval Agent
Stamps output with STATUS: READY_FOR_REVIEW.
Saves final markdown to output/ directory.
Output: { "status": "READY_FOR_REVIEW", "file_path": str }
"""
import os
from datetime import datetime
from .base_agent import BaseAgent

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


class ApprovalAgent(BaseAgent):
    name = "ApprovalAgent"
    MAX_RETRIES = 1  # Pure I/O — no LLM needed

    def _execute(self, input_data: dict) -> dict:
        full_markdown: str = input_data.get("full_markdown", "")
        title: str = input_data.get("title", "untitled")
        run_id: str = input_data.get("run_id", datetime.now().strftime("%Y%m%d_%H%M%S"))
        short_index: int = input_data.get("short_index", 1)

        # Stamp the output
        stamped = full_markdown + f"\n\n---\n\n**STATUS: READY_FOR_REVIEW** ✅\n\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

        # Sanitize title for filename
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)
        safe_title = safe_title.strip().replace(" ", "_")[:40]
        filename = f"short_{short_index:02d}_{safe_title}.md"

        # Create output directory for this run
        run_dir = os.path.join(os.path.abspath(OUTPUT_DIR), run_id)
        os.makedirs(run_dir, exist_ok=True)

        file_path = os.path.join(run_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(stamped)

        return {
            "status": "READY_FOR_REVIEW",
            "file_path": file_path,
            "run_id": run_id,
        }
