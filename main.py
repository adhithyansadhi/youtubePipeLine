"""
main.py — Entry point for the YouTube Shorts Multi-Agent System
Usage:
  python main.py                # Generate 3 Shorts (default)
  python main.py --count 5      # Generate 5 Shorts
  python main.py --mock         # Run in mock mode (no API key needed)
  python main.py --count 1 --mock
"""
import sys
import io
# Force UTF-8 output on Windows so emoji in rich/print don't crash
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
# ── Load .env before importing agents ──────────────────────────────────────
def load_env():
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())
    else:
        print(
            "⚠  No .env file found. Copy .env.template to .env and add your GEMINI_API_KEY.\n"
            "   To test without an API key, run:  python main.py --mock\n"
        )

load_env()

# ── Parse CLI args ──────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="YouTube Shorts Multi-Agent AI System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                  # Generate 3 Shorts with Gemini API
  python main.py --count 5        # Generate 5 Shorts
  python main.py --mock           # Run without API key (demo mode)
  python main.py --count 1 --mock # Quick single-Short demo
  python main.py --reset-memory   # Clear used topics and start fresh
        """,
    )
    parser.add_argument(
        "--count", "-c", type=int, default=None,
        help="Number of Shorts to generate (1–5, default: from .env or 3)"
    )
    parser.add_argument(
        "--mock", "-m", action="store_true",
        help="Run in mock mode without Gemini API (uses template responses)"
    )
    parser.add_argument(
        "--reset-memory", action="store_true",
        help="Clear used_topics.json memory and exit"
    )
    return parser.parse_args()


def reset_memory():
    import json
    memory_path = Path(__file__).parent / "memory" / "used_topics.json"
    memory_path.parent.mkdir(exist_ok=True)
    with open(memory_path, "w") as f:
        json.dump({"used_topics": [], "run_history": []}, f, indent=2)
    print("✅ Memory reset. used_topics.json cleared.")


def validate_environment(mock_mode: bool):
    if mock_mode:
        return
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_api_key_here":
        print(
            "❌ GEMINI_API_KEY is not set or is still the placeholder value.\n"
            "   Options:\n"
            "   1. Add your key to .env:  GEMINI_API_KEY=your_actual_key\n"
            "   2. Run in mock mode:      python main.py --mock\n"
            "   Get a free key at: https://aistudio.google.com/app/apikey\n"
        )
        sys.exit(1)


def main():
    args = parse_args()

    if args.reset_memory:
        reset_memory()
        return

    # Set mock mode env var BEFORE importing orchestrator (which imports agents)
    if args.mock:
        os.environ["MOCK_MODE"] = "true"
        print("[MOCK] Running in MOCK MODE -- no API calls will be made.\n")

    validate_environment(mock_mode=args.mock or os.getenv("MOCK_MODE", "false").lower() == "true")

    # Determine number of Shorts
    num_shorts = args.count or int(os.getenv("NUM_SHORTS", "3"))
    num_shorts = max(1, min(5, num_shorts))

    # Import here so MOCK_MODE env var is already set
    from orchestrator import Orchestrator

    orchestrator = Orchestrator(num_shorts=num_shorts)
    results = orchestrator.run()

    # Print file paths for easy access
    successful = [r for r in results if "error" not in r]
    if successful:
        print("\n[OUTPUT] Files saved:")
        for r in successful:
            print(f"   {r.get('file_path', '')}")
    else:
        print("\n[!] No Shorts were generated successfully.")
        sys.exit(1)


if __name__ == "__main__":
    main()
