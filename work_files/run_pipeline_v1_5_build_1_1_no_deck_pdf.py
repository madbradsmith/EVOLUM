#!V_1 UPDATED FOR NEW CLEAN APP SPACE
import os
import sys
import json
import subprocess
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
STATUS_FILE = APP_DIR / "status.json"


def write_status(step, progress, message, start_time, state="running"):
    elapsed = int(time.time() - start_time)
    payload = {
        "state": state,
        "step": step,
        "progress": progress,
        "message": message,
        "elapsed_seconds": elapsed
    }
    STATUS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run(cmd, step_key, progress, message, start_time):
    write_status(step_key, progress, message, start_time, state="running")
    print("\n" + "=" * 40)
    print(cmd)
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        write_status(step_key, progress, f"Failed during: {message}", start_time, state="error")
        print("❌ Step failed")
        sys.exit(1)


def find_latest_pptx():
    files = list(APP_DIR.glob("pitch_deck_v*.pptx"))
    exports_dir = APP_DIR / "exports"
    if exports_dir.exists():
        files += list(exports_dir.glob("pitch_deck_v*.pptx"))

    files = [f for f in files if f.is_file()]
    if not files:
        return None

    return max(files, key=lambda f: f.stat().st_mtime)


def main(input_file):
    start_time = time.time()

    write_status("start", 1, "Starting pipeline...", start_time, state="running")
    print("🚀 Starting full pipeline")
    print(f"📄 Script input: {input_file}")
    print(f"📁 Working directory: {APP_DIR}")

    run(
        f'python3 "{APP_DIR}/input_handler_v1.py" "{input_file}"',
        "input_handler",
        15,
        "Parsing screenplay...",
        start_time
    )

    run(
        f"python3 {APP_DIR}/single_brain_orchestrator_v3.py {APP_DIR}/input.txt",
        "brain",
        35,
        "Generating story analysis...",
        start_time
    )

    upload_context_path = APP_DIR / "user_upload_context.json"
    approved_path = APP_DIR / "approved_brain_output.json"

    if upload_context_path.exists() and approved_path.exists():
        try:
            with open(upload_context_path, "r", encoding="utf-8") as f:
                user_context = json.load(f)

            with open(approved_path, "r", encoding="utf-8") as f:
                approved = json.load(f)

            user_logline = (user_context.get("logline") or "").strip()
            user_synopsis = (user_context.get("synopsis") or "").strip()

            if user_logline:
                approved["logline"] = user_logline

            if user_synopsis:
                approved["synopsis"] = user_synopsis

            with open(approved_path, "w", encoding="utf-8") as f:
                json.dump(approved, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not merge user upload context: {e}")
            
import os
import sys
import json
import subprocess
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
STATUS_FILE = APP_DIR / "status.json"


def write_status(step, progress, message, start_time, state="running"):
    elapsed = int(time.time() - start_time)
    payload = {
        "state": state,
        "step": step,
        "progress": progress,
        "message": message,
        "elapsed_seconds": elapsed
    }
    STATUS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run(cmd, step_key, progress, message, start_time):
    write_status(step_key, progress, message, start_time, state="running")
    print("\n" + "=" * 40)
    print(cmd)
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        write_status(step_key, progress, f"Failed during: {message}", start_time, state="error")
        print("❌ Step failed")
        sys.exit(1)


def find_latest_pptx():
    files = []

    output_dir = APP_DIR / "output"
    if output_dir.exists():
        files += list(output_dir.glob("pitch_deck_v*.pptx"))

    exports_dir = APP_DIR / "exports"
    if exports_dir.exists():
        files += list(exports_dir.glob("pitch_deck_v*.pptx"))

    files += list(APP_DIR.glob("pitch_deck_v*.pptx"))

    files = [f for f in files if f.is_file()]
    if not files:
        return None

    return max(files, key=lambda f: f.stat().st_mtime)


def main(input_file):
    start_time = time.time()

    write_status("start", 1, "Starting pipeline...", start_time, state="running")
    print("🚀 Starting full pipeline")
    print(f"📄 Script input: {input_file}")
    print(f"📁 Working directory: {APP_DIR}")

    run(
        f'python3 "{APP_DIR}/input_handler_v1.py" "{input_file}"',
        "input_handler",
        15,
        "Parsing screenplay...",
        start_time
    )

    run(
        f"python3 {APP_DIR}/single_brain_orchestrator_v3.py {APP_DIR}/input.txt",
        "brain",
        35,
        "Generating story analysis...",
        start_time
    )

    upload_context_path = APP_DIR / "user_upload_context.json"
    approved_path = APP_DIR / "approved_brain_output.json"

    if upload_context_path.exists() and approved_path.exists():
        try:
            with open(upload_context_path, "r", encoding="utf-8") as f:
                user_context = json.load(f)

            with open(approved_path, "r", encoding="utf-8") as f:
                approved = json.load(f)

            user_logline = (user_context.get("logline") or "").strip()
            user_synopsis = (user_context.get("synopsis") or "").strip()

            if user_logline:
                approved["logline"] = user_logline

            if user_synopsis:
                approved["synopsis"] = user_synopsis

            with open(approved_path, "w", encoding="utf-8") as f:
                json.dump(approved, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not merge user upload context: {e}")
            
    run(
        f"python3 {APP_DIR}/layout_engine.py {APP_DIR}/approved_brain_output.json",
        "layout",
        55,
        "Building slide plan...",
        start_time
    )

    run(
        f"python3 {APP_DIR}/deck_builder.py {APP_DIR}/slide_plan.json",
        "deck_builder",
        75,
        "Building pitch deck...",
        start_time
    )

    pptx = find_latest_pptx()

    if pptx:
        print(f"📄 Found PPTX: {pptx}")
        write_status(
            "pdf_conversion",
            90,
            "Skipping PDF conversion. PowerPoint export ready.",
            start_time,
            state="running"
        )
        print("⚠️ Skipping deck PDF conversion")
    else:
        write_status("pdf_conversion", 90, "No PPTX found.", start_time, state="error")
        print("⚠️ No PPTX found")
        sys.exit(1)

    write_status("complete", 100, "Complete", start_time, state="complete")
    print("\n🎉 Pipeline complete")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ No input file provided")
        sys.exit(1)

    main(sys.argv[1])
