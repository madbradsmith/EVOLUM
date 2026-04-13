# BETA v1.5 BUILD 1.2 — STABLE

from flask import Flask, request, render_template, send_file, jsonify, abort, session, redirect, url_for, session, redirect, url_for
from pathlib import Path
import json
import shutil
import subprocess
import os
import time
from datetime import datetime

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "evolum-beta-gate-v4-7")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
STATUS_FILE = BASE_DIR / "status.txt"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEMO_DECK = BASE_DIR / "static" / "NOT_TODAY_Pitch_Deck_FINAL.pdf"

LATEST_PPTX = OUTPUT_DIR / "latest.pptx"
LATEST_PDF = OUTPUT_DIR / "latest.pdf"

LATEST_ANALYSIS_JSON = OUTPUT_DIR / "latest_analysis_report.json"
LATEST_ANALYSIS_PDF = OUTPUT_DIR / "latest_analysis_report.pdf"

ALLOWED_EXTENSIONS = {".txt", ".pdf"}

ACCESS_CODES = [
    "beta1",
    "beta2",
    "vip",
    "madbrad",
]

BETA_ACCESS_LOGS_DIR = BASE_DIR / "beta_access_logs"
BETA_ACCESS_LOGS_DIR.mkdir(parents=True, exist_ok=True)


def is_render_env() -> bool:
    return os.environ.get("RENDER", "").lower() == "true"


def has_beta_access() -> bool:
    return session.get("beta_access") is True


def log_beta_access(access_code: str, status: str):
    safe_code = "".join(ch for ch in access_code if ch.isalnum() or ch in ("-", "_")).strip() or "unknown"
    code_dir = BETA_ACCESS_LOGS_DIR / safe_code
    code_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
    user_agent = request.headers.get("User-Agent", "unknown")
    log_line = f"{timestamp} | {status} | code={access_code} | ip={ip_addr} | ua={user_agent}\n"

    log_file = code_dir / "access_log.txt"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)

    print(log_line.strip())


def log_usage(event, **kwargs):
    parts = [f"{k}={v}" for k, v in kwargs.items()]
    
    if parts:
        line = f"USAGE | {event} | " + " | ".join(parts)
    else:
        line = f"USAGE | {event}"
    
    print(line, flush=True)


def set_status(text: str):
    STATUS_FILE.write_text(text, encoding="utf-8")


def get_status() -> str:
    if not STATUS_FILE.exists():
        return "IDLE"
    return STATUS_FILE.read_text(encoding="utf-8").strip() or "IDLE"


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def clear_latest_targets():
    for path in (LATEST_PPTX, LATEST_PDF):
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass


def newest_generated_file(ext: str):
    excluded = {LATEST_PPTX.name, LATEST_PDF.name}
    files = [p for p in OUTPUT_DIR.glob(f"pitch_deck_v*{ext}") if p.name not in excluded]

    if not files:
        return None

    return max(files, key=lambda p: p.stat().st_mtime)


def publish_latest_outputs(pptx_source, pdf_source):
    if pptx_source and pptx_source.exists():
        shutil.copy2(pptx_source, LATEST_PPTX)

    if pdf_source and pdf_source.exists():
        shutil.copy2(pdf_source, LATEST_PDF)


def safe_text(value, fallback="-"):
    if value is None:
        return fallback
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value if str(v).strip())
    value = str(value).strip()
    return value or fallback


def wrap_text(text, font_name="Helvetica", font_size=11, max_width=500):
    words = safe_text(text, "").split()
    if not words:
        return []

    lines = []
    current = words[0]

    for word in words[1:]:
        trial = f"{current} {word}"
        if stringWidth(trial, font_name, font_size) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word

    lines.append(current)
    return lines


def draw_wrapped_text(pdf, text, x, y, max_width=500, font_name="Helvetica", font_size=11, leading=15):
    lines = wrap_text(text, font_name=font_name, font_size=font_size, max_width=max_width)
    pdf.setFont(font_name, font_size)
    for line in lines:
        pdf.drawString(x, y, line)
        y -= leading
    return y


def build_simple_analysis_pdf(report_output: dict, out_path: Path):
    pdf = canvas.Canvas(str(out_path), pagesize=LETTER)
    width, height = LETTER

    left = 54
    top = height - 54
    y = top

    def new_page():
        nonlocal y
        pdf.showPage()
        y = top

    def ensure_space(lines_needed=3, line_height=15):
        nonlocal y
        needed = lines_needed * line_height
        if y - needed < 54:
            new_page()

    title = safe_text(report_output.get("title"), "UNTITLED PROJECT")
    pdf.setTitle(f"{title} Analysis Report")

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(left, y, title)
    y -= 28

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(left, y, "Script Analysis Report")
    y -= 20

    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, y, "Powered by Developum AI Engine")
    y -= 28

    sections = [
        ("Summary Note", report_output.get("summary_note")),
        ("Tagline", report_output.get("tagline")),
        ("Logline", report_output.get("logline")),
        ("Synopsis", report_output.get("synopsis")),
        ("Lead Character", report_output.get("lead_character")),
        ("Supporting Characters", report_output.get("supporting_characters")),
        ("Genre", report_output.get("genre")),
        ("Tone", report_output.get("tone")),
        ("Theme", report_output.get("theme")),
        ("World", report_output.get("world")),
        ("Core Conflict", report_output.get("core_conflict")),
        ("Story Engine", report_output.get("story_engine")),
        ("Reversal", report_output.get("reversal")),
    ]

    for heading, body in sections:
        ensure_space(lines_needed=4)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(left, y, heading)
        y -= 16
        y = draw_wrapped_text(pdf, safe_text(body), left, y, max_width=500)
        y -= 12

    def draw_list_section(title_text, items):
        nonlocal y
        if not items:
            return
        ensure_space(lines_needed=len(items) + 3)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(left, y, title_text)
        y -= 18
        pdf.setFont("Helvetica", 11)
        for item in items:
            ensure_space(lines_needed=2)
            y = draw_wrapped_text(pdf, f"• {safe_text(item)}", left, y, max_width=500)
            y -= 6

    draw_list_section("Story Insights", report_output.get("story_insights", []))
    draw_list_section("What’s Working", report_output.get("whats_working", []))
    draw_list_section("What Needs Work", report_output.get("what_needs_work", []))

    top_characters = report_output.get("character_analysis", {}).get("top_characters", [])
    if top_characters:
        ensure_space(lines_needed=5)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(left, y, "Top Characters")
        y -= 18
        for entry in top_characters:
            ensure_space(lines_needed=3)
            line = (
                f"{safe_text(entry.get('name'))} — "
                f"Dialogue: {entry.get('dialogue_count', 0)}, "
                f"Action: {entry.get('action_count', 0)}, "
                f"First Seen: {entry.get('first_seen', 0)}"
            )
            y = draw_wrapped_text(pdf, line, left, y, max_width=500)
            y -= 6

    pdf.save()


@app.before_request
def require_beta_gate():
    public_endpoints = {"index", "beta_access", "static"}

    if request.endpoint in public_endpoints:
        return None

    if has_beta_access():
        return None

    if request.method == "GET":
        return redirect(url_for("index"))

    return ("Unauthorized", 403)


@app.route("/beta-access", methods=["POST"])
def beta_access():
    access_code = (request.form.get("access_code") or "").strip()

    if access_code in ACCESS_CODES:
        session["beta_access"] = True
        session["beta_code"] = access_code
        log_beta_access(access_code, "ACCESS GRANTED")
        log_usage("beta_access", code=access_code, success=True)
        return redirect(url_for("index"))

    log_beta_access(access_code or "blank", "ACCESS FAILED")
    log_usage("beta_access", code=access_code or "blank", success=False)
    return render_template(
        "index.html",
        is_render=is_render_env(),
        gate_locked=True,
        gate_error="Incorrect access code. Please try again.",
    )


@app.route("/")
def index():
    return render_template(
        "index.html",
        is_render=is_render_env(),
        gate_locked=not has_beta_access(),
        gate_error=None,
    )


@app.route("/status")
def status():
    return jsonify({"status": get_status()})


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("script")

    if not file or file.filename == "":
        return "No file uploaded", 400

    if not allowed_file(file.filename):
        return "Only .txt and .pdf supported", 400

    clear_latest_targets()
    set_status("UPLOADED")

    save_path = UPLOAD_DIR / Path(file.filename).name
    file.save(save_path)

    started_at = time.time()
    log_usage("generate_start", filename=file.filename)

    logline = (request.form.get("logline") or "").strip()
    synopsis = (request.form.get("synopsis") or "").strip()
    poster = request.files.get("poster")
    images = request.files.getlist("images")

    visuals_root = BASE_DIR / "visuals" / "user_uploaded"
    poster_dir = visuals_root / "poster"
    current_dir = visuals_root / "current"

    poster_dir.mkdir(parents=True, exist_ok=True)
    current_dir.mkdir(parents=True, exist_ok=True)

    for old_file in poster_dir.iterdir():
        if old_file.is_file():
            old_file.unlink()

    for old_file in current_dir.iterdir():
        if old_file.is_file():
            old_file.unlink()

    if poster and poster.filename:
        poster_path = poster_dir / Path(poster.filename).name
        poster.save(poster_path)

    saved_images = []
    for image in images:
        if image and image.filename:
            image_path = current_dir / Path(image.filename).name
            image.save(image_path)
            saved_images.append(image_path.name)

    upload_context = {
        "script_filename": Path(file.filename).name,
        "logline": logline,
        "synopsis": synopsis,
        "poster_filename": poster.filename if poster and poster.filename else "",
        "image_filenames": saved_images,
    }

    (BASE_DIR / "user_upload_context.json").write_text(
        json.dumps(upload_context, indent=2),
        encoding="utf-8",
    )

    try:
        set_status("ANALYZING")
        log_path = BASE_DIR / "pipeline.log"

        with open(log_path, "w", encoding="utf-8") as log_file:
            subprocess.run(
                ["python3", str(BASE_DIR / "run_pipeline.py"), str(save_path)],
                cwd=str(BASE_DIR),
                stdout=log_file,
                stderr=log_file,
                text=True,
                check=True,
            )

        set_status("BUILDING")
    except subprocess.CalledProcessError:
        set_status("ERROR")
        return "Engine failed", 500

    fresh_pptx = newest_generated_file(".pptx")
    fresh_pdf = newest_generated_file(".pdf")

    if not fresh_pptx or not fresh_pptx.exists():
        set_status("ERROR")
        return "No deck generated", 500

    publish_latest_outputs(fresh_pptx, fresh_pdf)

    if not LATEST_PPTX.exists():
        set_status("ERROR")
        return "Latest deck publish failed", 500

    set_status("COMPLETE")
    elapsed = int(time.time() - started_at)
    log_usage("generate_complete", success=True, filename=file.filename, elapsed=f"{elapsed}s")
    return ("OK", 200)


@app.route("/demo", methods=["POST"])
def demo():
    if not DEMO_DECK.exists():
        return "Demo deck not found", 500
    return send_file(DEMO_DECK, as_attachment=False)


@app.route("/download/latest.pptx")
def download_latest_pptx():
    if not LATEST_PPTX.exists():
        abort(404)
    return send_file(LATEST_PPTX, as_attachment=True)


@app.route("/download/latest.pdf")
def download_latest_pdf():
    if not LATEST_PDF.exists():
        abort(404)
    return send_file(LATEST_PDF, as_attachment=True)


@app.route("/analyze-script-pass", methods=["POST"])
def analyze_script_pass():
    file = request.files.get("script")

    if not file or file.filename == "":
        return jsonify({"error": "No file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only .txt and .pdf supported"}), 400

    temp_path = UPLOAD_DIR / Path(file.filename).name
    file.save(temp_path)

    started_at = time.time()
    log_usage("analyze_start", filename=file.filename)

    try:
        subprocess.run(
            ["python3", str(BASE_DIR / "single_brain_orchestrator_v3.py"), str(temp_path)],
            cwd=str(BASE_DIR),
            check=True,
        )
    except subprocess.CalledProcessError:
        log_usage("analyze_complete", success=False, filename=file.filename, error="analysis_failed")
        return jsonify({"error": "analysis failed"}), 500

    brain_file = BASE_DIR / "approved_brain_output.json"

    if not brain_file.exists():
        return jsonify({"error": "No brain output"}), 500

    with open(brain_file, "r", encoding="utf-8") as f:
        brain = json.load(f)

    characters = brain.get("characters") or []
    lead_character = brain.get("protagonist") or (characters[0] if characters else "-")
    supporting_characters = characters[1:5] if len(characters) > 1 else []

    report_output = {
        "title": safe_text(brain.get("title"), "UNTITLED PROJECT"),
        "tagline": safe_text(brain.get("tagline") or brain.get("logline")),
        "logline": safe_text(brain.get("logline")),
        "synopsis": safe_text(brain.get("synopsis")),
        "lead_character": safe_text(lead_character),
        "supporting_characters": supporting_characters,
        "genre": safe_text(brain.get("world"), "Drama"),
        "tone": safe_text(brain.get("tone")),
        "theme": safe_text(brain.get("theme")),
        "world": safe_text(brain.get("world")),
        "core_conflict": safe_text(brain.get("core_conflict")),
        "story_engine": safe_text(brain.get("story_engine")),
        "reversal": safe_text(brain.get("reversal")),
        "story_insights": [
            f"Top characters identified: {', '.join(characters[:5])}" if characters else "Top characters identified.",
            f"Protagonist detected: {lead_character}",
            f"World detected: {safe_text(brain.get('world'), 'Unknown')}",
        ],
        "character_analysis": {
            "top_characters": [
                {
                    "name": name,
                    "dialogue_count": (brain.get("character_stats") or {}).get(name, {}).get("dialogue_count", 0),
                    "action_count": (brain.get("character_stats") or {}).get(name, {}).get("action_count", 0),
                    "first_seen": (brain.get("character_stats") or {}).get(name, {}).get("first_seen", 0),
                }
                for name in characters[:5]
            ]
        },
    }

    summary_note = safe_text(report_output.get("summary_note"), "")
    if summary_note in {"", "-"}:
        title = safe_text(report_output.get("title"), "This script")
        lead = safe_text(report_output.get("lead_character"), "the lead character")
        genre = safe_text(report_output.get("genre"), "a cinematic story")
        tone = safe_text(report_output.get("tone"), "grounded and emotional")

        summary_note = (
            f"{title} puts {lead} at the center of {genre.lower()}, "
            f"with a tone that feels {tone.lower()}."
        )

    report_output["summary_note"] = summary_note

    LATEST_ANALYSIS_JSON.write_text(
        json.dumps(report_output, indent=2),
        encoding="utf-8",
    )
    build_simple_analysis_pdf(report_output, LATEST_ANALYSIS_PDF)

    return jsonify(
        {
            "summary_note": summary_note,
            "title": report_output.get("title", "UNTITLED PROJECT"),
            "report_json": str(LATEST_ANALYSIS_JSON.name),
            "report_pdf": str(LATEST_ANALYSIS_PDF.name),
        }
    )


@app.route("/analysis-report/latest.json")
def analysis_report_latest_json():
    if not LATEST_ANALYSIS_JSON.exists():
        return jsonify({"error": "No analysis report yet"}), 404

    with open(LATEST_ANALYSIS_JSON, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/analysis-report/latest.pdf")
def analysis_report_latest_pdf():
    if not LATEST_ANALYSIS_PDF.exists():
        abort(404)
    return send_file(LATEST_ANALYSIS_PDF, as_attachment=False)


@app.route("/analyzer")
def analyzer():
    analyzer_file = BASE_DIR / "builder" / "deck_builder_output.json"

    if not analyzer_file.exists():
        return jsonify({"error": "No analyzer output yet"}), 404

    with open(analyzer_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return jsonify(data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
