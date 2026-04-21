# =====================================================
# ===== EVOLUM MASTER APP STRUCTURE (VX BETA) =========
# =====================================================

# ===== IMPORTS / SETUP START =========================
# FULL v1_0 BUILD 1.1 — STABLE

from flask import Flask, request, render_template, send_file, jsonify, abort, session, redirect, url_for
from pathlib import Path
import json
import io
import contextlib
import shutil
import subprocess
import os
import importlib.util
import re
import time
import uuid
from datetime import datetime
from urllib.parse import unquote, quote

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from pptx import Presentation
from dai_tools import build_actor_prep_pdf, build_actor_booked_pdf, build_simple_analysis_pdf
from pypdf import PdfReader


# ===== IMPORTS / SETUP END ===========================

# ===== GLOBAL CONFIG / PATHS START ===================
app = Flask(__name__)

_REFINE_BUILDER_MODULE = None
_LATEST_SLIDE_PAYLOAD_CACHE = {"key": None, "payload": None}
app.secret_key = os.environ.get("SECRET_KEY")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
STATUS_FILE = BASE_DIR / "status.json"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEMO_DECK = BASE_DIR / "static" / "NOT_TODAY_Pitch_Deck_FINAL.pdf"

LATEST_PPTX = OUTPUT_DIR / "latest.pptx"
LATEST_PDF = OUTPUT_DIR / "latest.pdf"

LATEST_ANALYSIS_JSON = OUTPUT_DIR / "latest_analysis_report.json"
LATEST_ANALYSIS_PDF = OUTPUT_DIR / "latest_analysis_report.pdf"
LATEST_ACTOR_PREP_PDF = OUTPUT_DIR / "latest_actor_prep_report.pdf"
LATEST_ACTOR_BOOKED_PDF = OUTPUT_DIR / "latest_actor_booked_report.pdf"
LATEST_DECK_MANIFEST_JSON = OUTPUT_DIR / "latest_deck_manifest.json"

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".fdx", ".docx", ".doc"}


def extract_script_text(file) -> str:
    import xml.etree.ElementTree as ET
    from zipfile import ZipFile
    import io

    filename = file.filename.lower()

    if filename.endswith(".txt"):
        return file.read().decode("utf-8", errors="ignore")

    if filename.endswith(".pdf"):
        try:
            reader = PdfReader(file)
            return "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
        except Exception:
            return ""

    if filename.endswith(".fdx"):
        try:
            tree = ET.parse(file)
            root = tree.getroot()
            lines = []
            for p in root.findall(".//Paragraph"):
                texts = [t.text for t in p.findall(".//Text") if t.text]
                line = "".join(texts).strip()
                if line:
                    lines.append(line)
            return "\n".join(lines)
        except Exception:
            return ""

    if filename.endswith(".docx") or filename.endswith(".doc"):
        try:
            raw = file.read()
            with ZipFile(io.BytesIO(raw)) as z:
                xml_bytes = z.read("word/document.xml")
            root = ET.fromstring(xml_bytes)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            lines = []
            for p in root.findall(".//w:p", ns):
                texts = [t.text for t in p.findall(".//w:t", ns) if t.text]
                line = "".join(texts).strip()
                if line:
                    lines.append(line)
            return "\n".join(lines)
        except Exception:
            return ""

    return ""

ACCESS_CODES = [
    "beta1",
    "beta2",
    "beta3",
    "beta4", 
    "beta5",
    "beta6",
    "beta7",
    "beta8",
    "beta9",
    "beta10",
    "beta11",
    "beta12",    
    "beta13",
    "beta14",
    "beta15",
    "beta16",
    "beta17",
    "beta18",
    "beta19",
    "beta20",
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
    try:
        existing = json.loads(STATUS_FILE.read_text(encoding="utf-8")) if STATUS_FILE.exists() else {}
    except Exception:
        existing = {}
    existing["state"] = text
    STATUS_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def get_status() -> str:
    if not STATUS_FILE.exists():
        return "IDLE"
    try:
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        return data.get("state", "IDLE") or "IDLE"
    except Exception:
        return "IDLE"


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

def find_latest_slide_plan_file():
    candidates = []

    direct_candidates = [
        BASE_DIR / "slide_plan.json",
        OUTPUT_DIR / "slide_plan.json",
        BASE_DIR / "pipeline" / "slide_plan.json",
        BASE_DIR / "pipeline" / "compile" / "slide_plan.json",
    ]
    for path in direct_candidates:
        if path.exists():
            candidates.append(path)

    search_roots = [
        BASE_DIR,
        OUTPUT_DIR,
        BASE_DIR / "projects",
        BASE_DIR / "pipeline",
    ]
    seen = set()
    for root in search_roots:
        if not root.exists():
            continue
        for path in root.rglob("slide_plan.json"):
            if path in seen:
                continue
            seen.add(path)
            candidates.append(path)

    if not candidates:
        return None

    return max(candidates, key=lambda p: p.stat().st_mtime)

def safe_relpath(path_obj):
    try:
        return str(path_obj.relative_to(BASE_DIR))
    except Exception:
        return str(path_obj)


def resolve_quiet_image_for_slide(slide_title, stage, layout, slide_number):
    visuals_root = BASE_DIR / "visuals"

    if not visuals_root.exists():
        return None

    exts = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    candidates = []

    for ext in exts:
        candidates.extend(visuals_root.rglob(ext))

    if not candidates:
        return None

    title_words = str(slide_title).lower().replace("(", " ").replace(")", " ").split()

    for candidate in candidates:
        name = candidate.stem.lower()

        for word in title_words:
            if len(word) >= 4 and word in name:
                return candidate

    return candidates[0]

def build_refine_slide_payload(slide_plan_data: dict, slide_plan_file=None):
    project_title = safe_text(slide_plan_data.get("title"), "UNTITLED PROJECT")
    raw_slides = slide_plan_data.get("slides") or []
    slide_plan_file = Path(slide_plan_file) if slide_plan_file else None
    project_dir = find_latest_project_dir(slide_plan_file)

    mapped_slides = []
    last_used_image_name = ""

    for index, slide in enumerate(raw_slides):
        if not isinstance(slide, dict):
            continue

        stage = safe_text(slide.get("stage"), "").lower()
        layout = safe_text(slide.get("layout"), "").lower()
        title = safe_text(slide.get("title"), f"Slide {index + 1}")

        body = safe_text(
            slide.get("body")
            or slide.get("content")
            or slide.get("text")
            or slide.get("copy"),
            "",
        )

        slide_type = title

        if stage == "title" or layout == "title":
            slide_type = "Title Slide"
        elif "logline" in title.lower():
            slide_type = "Logline"
        elif "synopsis" in title.lower():
            slide_type = "Synopsis"
        elif stage == "character":
            slide_type = "Characters"
        elif stage == "why_now":
            slide_type = "Why This Project"

        subtitle = ""

        if stage == "title" or layout == "title":
            subtitle = project_title if title.strip().lower() != project_title.strip().lower() else ""
        elif title.lower() in {
            "logline",
            "synopsis",
            "synopsis (2)",
            "hook",
            "conflict",
            "stakes",
            "world",
            "tone",
            "story engine",
            "reversal",
            "why this movie",
            "protagonist",
        }:
            subtitle = title
        elif stage:
            subtitle = stage.replace("_", " ").title()
        elif layout:
            subtitle = layout.replace("_", " ").title()

        caption_bits = []

        if stage:
            caption_bits.append(f"Stage: {stage.replace('_', ' ').title()}")

        if layout:
            caption_bits.append(f"Layout: {layout.replace('_', ' ').title()}")

        configured_image_path = safe_text(slide.get("image_path"), "")
        configured_image_name = safe_text(slide.get("image_name"), "")
        configured_image_url = safe_text(slide.get("image_url"), "")
        image_options = normalize_manifest_image_options(slide.get("image_options") or [])
        selected_option_id = safe_text(slide.get("selected_option_id"), "")

        resolved_image = None
        if configured_image_path:
            try:
                configured_candidate = Path(configured_image_path)
                if not configured_candidate.is_absolute():
                    configured_candidate = (BASE_DIR / configured_candidate).resolve()
                else:
                    configured_candidate = configured_candidate.resolve()
                if configured_candidate.exists() and configured_candidate.is_file():
                    resolved_image = configured_candidate
            except Exception:
                resolved_image = None

        if resolved_image is None:
            resolved_image = resolve_quiet_image_for_slide(
                slide_title=title,
                stage=stage,
                layout=layout,
                slide_number=index + 1,
            )

        image_name = configured_image_name or (resolved_image.name if resolved_image else "")
        image_url = configured_image_url or project_file_url_for_path(configured_image_path)
        if not image_url and resolved_image:
            image_url = f"/project-file?path={safe_relpath(resolved_image)}"

        if image_name:
            caption_bits.append(f"Image: {image_name}")

        caption = " • ".join(caption_bits) if caption_bits else f"Generated slide {index + 1}"

        mapped_slides.append({
            "type": slide_type,
            "title": title,
            "subtitle": subtitle,
            "body": body,
            "caption": caption,
            "accent": "#ffb347",
            "layout": layout,
            "stage": stage,
            "source_index": index,
            "image_name": image_name,
            "image_url": image_url,
            "image_options": image_options,
            "selected_option_id": selected_option_id,
        })

    return {
        "title": project_title,
        "slide_count": len(mapped_slides),
        "slides": mapped_slides,
    }


def load_deck_builder_module():
    global _REFINE_BUILDER_MODULE
    if _REFINE_BUILDER_MODULE is not None:
        return _REFINE_BUILDER_MODULE

    builder_path = BASE_DIR / "deck_builder_MADBRAD_BRAIN_V_1.py"
    if not builder_path.exists():
        _REFINE_BUILDER_MODULE = False
        return None

    try:
        spec = importlib.util.spec_from_file_location("deck_builder_madbrad_brain_v1", builder_path)
        if not spec or not spec.loader:
            _REFINE_BUILDER_MODULE = False
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _REFINE_BUILDER_MODULE = module
        return module
    except Exception as e:
        print(f"⚠️ Could not load deck builder for refine image mapping: {e}", flush=True)
        _REFINE_BUILDER_MODULE = False
        return None


def find_latest_project_dir(slide_plan_file=None):
    if slide_plan_file and slide_plan_file.exists():
        return slide_plan_file.parent
    return BASE_DIR


def ensure_relative_to_base(path: Path) -> bool:
    try:
        path.resolve().relative_to(BASE_DIR.resolve())
        return True
    except Exception:
        return False


def resolve_refine_image_for_slide(project_dir, deck_title, slide, slide_number, last_used_name=""):
    explicit_candidates = []
    for key in ("image_path", "image", "image_file", "preview_image"):
        value = slide.get(key)
        if value:
            explicit_candidates.append(Path(str(value)))

    for candidate in explicit_candidates:
        resolved = candidate if candidate.is_absolute() else (project_dir / candidate)
        if resolved.exists() and ensure_relative_to_base(resolved):
            return resolved.resolve()

    builder = load_deck_builder_module()
    if not builder:
        return None

    visuals_dir = project_dir / "visuals"
    approved_brain_output_path = project_dir / "approved_brain_output.json"
    brain_output = {}
    if approved_brain_output_path.exists():
        try:
            brain_output = json.loads(approved_brain_output_path.read_text(encoding="utf-8"))
        except Exception:
            brain_output = {}
    elif (BASE_DIR / "approved_brain_output.json").exists():
        try:
            brain_output = json.loads((BASE_DIR / "approved_brain_output.json").read_text(encoding="utf-8"))
        except Exception:
            brain_output = {}

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            image_path = builder.find_image_for_slide(
                visuals_dir=visuals_dir,
                deck_title=deck_title,
                slide_title=safe_text(slide.get("title"), f"Slide {slide_number}"),
                slide_number=slide_number,
                brain_output=brain_output,
                last_used_name=last_used_name,
                slide_body=safe_text(slide.get("body"), ""),
            )
    except Exception as e:
        print(f"⚠️ Refine image resolution failed for slide {slide_number}: {e}", flush=True)
        return None

    if not image_path or not Path(image_path).exists():
        return None

    image_path = Path(image_path).resolve()
    if not ensure_relative_to_base(image_path):
        return None

    return image_path


def build_project_file_url(image_path: Path) -> str:
    rel = image_path.resolve().relative_to(BASE_DIR.resolve())
    return "/project-file?path=" + quote(str(rel).replace('\\', '/'))


def make_slide_payload_cache_key(slide_plan_file=None):
    if not slide_plan_file or not slide_plan_file.exists():
        return "missing"
    parts = [f"slide:{slide_plan_file}:{slide_plan_file.stat().st_mtime_ns}"]
    project_dir = find_latest_project_dir(slide_plan_file)
    abo = project_dir / "approved_brain_output.json"
    if not abo.exists():
        abo = BASE_DIR / "approved_brain_output.json"
    if abo.exists():
        parts.append(f"abo:{abo}:{abo.stat().st_mtime_ns}")
    builder_path = BASE_DIR / "deck_builder_MADBRAD_BRAIN_V_1.py"
    if builder_path.exists():
        parts.append(f"builder:{builder_path.stat().st_mtime_ns}")
    return "|".join(parts)


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


# ===== BETA ACCESS ROUTES START ======================
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
        base_path_prefix=str(BASE_DIR) + "/",
    )


# ===== CORE ROUTES START =============================
@app.route("/")
def index():
    return render_template(
        "index.html",
        is_render=is_render_env(),
        gate_locked=not has_beta_access(),
        gate_error=None,
        base_path_prefix=str(BASE_DIR) + "/",
    )


@app.route("/status")
def status():
    return jsonify({"status": get_status()})
    
# ===== PITCH DECK ROUTES START =======================

# ===== UPLOAD OVERRIDE HELPERS START ====================
def apply_upload_text_overrides(project_dir, logline_override="", synopsis_override=""):
    logline_override = (logline_override or "").strip()
    synopsis_override = (synopsis_override or "").strip()

    if not logline_override and not synopsis_override:
        return

    deck_content_candidates = [
        Path(project_dir) / "deck_content.json",
        Path(project_dir) / "pipeline" / "compile" / "deck_content.json",
        Path(project_dir) / "pipeline" / "compile" / "final_compiled_payload.json",
    ]

    for candidate in deck_content_candidates:
        if not candidate.exists():
            continue

        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue

        changed = False

        # Common payload-level keys
        if logline_override:
            for key in ["logline", "project_logline", "one_line_pitch"]:
                if key in data:
                    data[key] = logline_override
                    changed = True

        if synopsis_override:
            for key in ["synopsis", "project_synopsis", "story_overview"]:
                if key in data:
                    data[key] = synopsis_override
                    changed = True

        # Common slide structures
        slide_collections = []
        for key in ["slides", "deck_slides", "slide_plan"]:
            value = data.get(key)
            if isinstance(value, list):
                slide_collections.append(value)

        for slides in slide_collections:
            for slide in slides:
                if not isinstance(slide, dict):
                    continue

                slide_title = str(slide.get("title", "") or "").lower()
                slide_type = str(slide.get("type", "") or "").lower()

                if logline_override and ("logline" in slide_title or "logline" in slide_type):
                    for field in ["title", "subtitle", "body", "content", "text", "copy", "description"]:
                        if field in slide:
                            # preserve title if it's literally "Logline"
                            if field == "title" and str(slide.get(field, "")).strip().lower() == "logline":
                                continue
                            slide[field] = logline_override
                            changed = True
                            break

                if synopsis_override and ("synopsis" in slide_title or "synopsis" in slide_type):
                    for field in ["title", "subtitle", "body", "content", "text", "copy", "description"]:
                        if field in slide:
                            if field == "title" and str(slide.get(field, "")).strip().lower() == "synopsis":
                                continue
                            slide[field] = synopsis_override
                            changed = True
                            break

        if changed:
            candidate.write_text(json.dumps(data, indent=2), encoding="utf-8")
# ===== UPLOAD OVERRIDE HELPERS END ======================

@app.route("/upload", methods=["POST"])
def upload():
    submitted_logline = (request.form.get("logline") or "").strip()
    submitted_synopsis = (request.form.get("synopsis") or "").strip()
    file = request.files.get("script")

    if not file or file.filename == "":
        return "No file uploaded", 400

    if not allowed_file(file.filename):
        return "Unsupported file type. Please upload a TXT, PDF, FDX, or DOCX file.", 400

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

    # === ENSURE OVERRIDE FILE EXISTS IN ALL PIPELINE PATHS ===
    try:
        override_data = json.dumps(upload_context, indent=2)
        (BASE_DIR / "user_upload_context.json").write_text(override_data, encoding="utf-8")
        (BASE_DIR / "input").mkdir(exist_ok=True)
        (BASE_DIR / "input" / "user_upload_context.json").write_text(override_data, encoding="utf-8")
        (BASE_DIR / "pipeline").mkdir(exist_ok=True)
        (BASE_DIR / "pipeline" / "user_upload_context.json").write_text(override_data, encoding="utf-8")
        print("✅ Upload overrides written to all known paths")
    except Exception as e:
        print("⚠️ Failed to write override files:", e)


    # Delete previous session's generated images before starting new build
    prev_session_file = BASE_DIR / "current_session_id.txt"
    if prev_session_file.exists():
        try:
            prev_id = prev_session_file.read_text().strip()
            prev_dir = BASE_DIR / "generated_images" / prev_id
            if prev_dir.exists():
                shutil.rmtree(prev_dir)
        except Exception:
            pass

    session_id = uuid.uuid4().hex
    prev_session_file.write_text(session_id)
    build_env = {**os.environ, "EVOLUM_SESSION_ID": session_id}

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
                env=build_env,
            )

        set_status("BUILDING")
    except subprocess.CalledProcessError:
        set_status("ERROR")
        return "Engine failed", 500
    finally:
        try:
            save_path.unlink(missing_ok=True)
        except Exception:
            pass

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


@app.route("/output-file")
def output_file():
    name = (request.args.get("name") or "").strip()
    if not name:
        abort(404)

    candidate = (OUTPUT_DIR / name).resolve()
    if not ensure_relative_to_base(candidate) or not candidate.exists() or not candidate.is_file():
        abort(404)

    return send_file(candidate, as_attachment=True, conditional=True)

# ===== DEMO ROUTES START =============================
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


# ===== ANALYZE ROUTES START ==========================
@app.route("/analyze-script-pass", methods=["POST"])
def analyze_script_pass():
    file = request.files.get("script")

    if not file or file.filename == "":
        return jsonify({"error": "No file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type. Please upload a TXT, PDF, FDX, or DOCX file."}), 400

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
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass

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
        "setting": safe_text(brain.get("setting")),
        "time_frame": safe_text(brain.get("time_frame")),
        "commercial_positioning": safe_text(brain.get("commercial_positioning")),
        "audience_profile": brain.get("audience_profile") or [],
        "tone_comparables": brain.get("tone_comparables") or [],
        "comparable_films": brain.get("comparable_films") or [],
        "market_projections": brain.get("market_projections") or {},
        "strength_index": brain.get("strength_index") or {},
        "executive_summary": safe_text(brain.get("executive_summary")),
        "packaging_potential": safe_text(brain.get("packaging_potential")),
        "protagonist_summary": safe_text(brain.get("protagonist_summary")),
        "character_leverage": safe_text(brain.get("character_leverage")),
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

@app.route("/download/latest_analysis_report.pdf")
def analysis_report_download():
    if not LATEST_ANALYSIS_PDF.exists():
        abort(404)
    return send_file(LATEST_ANALYSIS_PDF, as_attachment=True)


@app.route("/analyzer")
def analyzer():
    analyzer_file = BASE_DIR / "builder" / "deck_builder_output.json"

    if not analyzer_file.exists():
        return jsonify({"error": "No analyzer output yet"}), 404

    with open(analyzer_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return jsonify(data)



# ===== REFINE DECK ROUTES START =======================
@app.route("/latest-slide-plan")
def latest_slide_plan():
    slide_plan_file = find_latest_slide_plan_file()

    if not slide_plan_file or not slide_plan_file.exists():
        return jsonify({
            "error": "No generated slide plan found yet.",
            "slides": [],
            "slide_count": 0,
        }), 404

    try:
        with open(slide_plan_file, "r", encoding="utf-8") as f:
            slide_plan_data = json.load(f)
    except Exception as e:
        return jsonify({"error": f"Could not read latest slide plan: {e}"}), 500

    cache_key = make_slide_payload_cache_key(slide_plan_file)
    if _LATEST_SLIDE_PAYLOAD_CACHE.get("key") == cache_key and _LATEST_SLIDE_PAYLOAD_CACHE.get("payload") is not None:
        payload = dict(_LATEST_SLIDE_PAYLOAD_CACHE["payload"])
    else:
        payload = build_refine_slide_payload(slide_plan_data, slide_plan_file=slide_plan_file)
        payload["source_file"] = str(slide_plan_file.relative_to(BASE_DIR)) if slide_plan_file.is_relative_to(BASE_DIR) else str(slide_plan_file)
        _LATEST_SLIDE_PAYLOAD_CACHE["key"] = cache_key
        _LATEST_SLIDE_PAYLOAD_CACHE["payload"] = dict(payload)
    return jsonify(payload)


@app.route("/project-file")
def project_file():
    raw_path = unquote((request.args.get("path") or "").strip())
    if not raw_path:
        abort(404)
    candidate = (BASE_DIR / raw_path).resolve()
    if not ensure_relative_to_base(candidate) or not candidate.exists() or not candidate.is_file():
        abort(404)
    return send_file(candidate, as_attachment=False, conditional=True)

@app.route("/refine-deck", methods=["POST"])
def refine_deck():
    data = request.get_json(silent=True) or {}
    slides = data.get("slides", [])

    if not slides or not isinstance(slides, list):
        return jsonify({"error": "No slide data provided."}), 400

    try:
        slide_plan_payload = {
            "title": slides[0].get("title", "Refined Deck") if slides else "Refined Deck",
            "slides": [
                {
                    "title": str(slide_data.get("title", "") or "").strip(),
                    "body": str(slide_data.get("body", "") or "").strip(),
                    "layout": str(slide_data.get("layout", "") or "text").strip(),
                    "stage": str(slide_data.get("stage", "") or "refine").strip(),
                    "subtitle": str(slide_data.get("subtitle", "") or "").strip(),
                    "image_path": str(slide_data.get("image_path", "") or "").strip(),
                    "image_name": str(slide_data.get("image_name", "") or "").strip(),
                    "image_url": str(slide_data.get("image_url", "") or "").strip(),
                    "image_source": str(slide_data.get("image_source", "") or "").strip(),
                    "image_options": slide_data.get("image_options", []) if isinstance(slide_data.get("image_options", []), list) else [],
                    "selected_option_id": str(slide_data.get("selected_option_id", "") or "").strip(),
                }
                for slide_data in slides
            ],
            "slide_count": len(slides),
        }

        slide_plan_path = BASE_DIR / "slide_plan.json"
        temp_slide_plan_path = BASE_DIR / "slide_plan.tmp.json"
        temp_slide_plan_path.write_text(json.dumps(slide_plan_payload, indent=2), encoding="utf-8")
        temp_slide_plan_path.replace(slide_plan_path)

        manifest_payload = []
        for i, slide_data in enumerate(slides, start=1):
            manifest_payload.append({
                "slide_number": i,
                "title": str(slide_data.get("title", "") or "").strip(),
                "body": str(slide_data.get("body", "") or "").strip(),
                "layout": str(slide_data.get("layout", "") or "").strip(),
                "stage": str(slide_data.get("stage", "") or "").strip(),
                "image_path": str(slide_data.get("image_path", "") or "").strip(),
                "image_name": str(slide_data.get("image_name", "") or "").strip(),
                "image_url": str(slide_data.get("image_url", "") or "").strip(),
                "image_source": str(slide_data.get("image_source", "") or "").strip(),
                "image_options": slide_data.get("image_options", []) if isinstance(slide_data.get("image_options", []), list) else [],
                "selected_option_id": str(slide_data.get("selected_option_id", "") or "").strip(),
            })

        LATEST_DECK_MANIFEST_JSON.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

        refine_session_file = BASE_DIR / "current_refine_session_id.txt"
        if refine_session_file.exists():
            try:
                prev_id = refine_session_file.read_text().strip()
                prev_dir = BASE_DIR / "generated_images" / prev_id
                if prev_dir.exists():
                    shutil.rmtree(prev_dir)
            except Exception:
                pass

        refine_session_id = uuid.uuid4().hex
        refine_session_file.write_text(refine_session_id)
        refine_env = {**os.environ, "EVOLUM_SESSION_ID": refine_session_id}
        subprocess.run(
            ["python3", str(BASE_DIR / "deck_builder.py"), str(slide_plan_path)],
            cwd=str(BASE_DIR),
            check=True,
            env=refine_env,
        )

        fresh_pptx = newest_generated_file(".pptx")
        fresh_pdf = newest_generated_file(".pdf")
        publish_latest_outputs(fresh_pptx, fresh_pdf)

        _LATEST_SLIDE_PAYLOAD_CACHE["key"] = None
        _LATEST_SLIDE_PAYLOAD_CACHE["payload"] = None

        return jsonify({
            "message": "Your refined deck has been rebuilt successfully.",
            "deck": fresh_pptx.name if fresh_pptx else LATEST_PPTX.name,
        })

    except Exception as e:
        return jsonify({"error": f"Refine rebuild failed: {e}"}), 500

# ===== REFINE DECK ROUTES END =========================

# ===== ACTOR PREP ROUTES START =======================
@app.route("/actor-prep-pass", methods=["POST"])
def actor_prep_pass():
    character_name = (request.form.get("character_name") or "").strip()
    pasted_text = (request.form.get("script_text") or "").strip()
    file = request.files.get("script")

    if not character_name:
        return jsonify({"error": "Please enter the role you are preparing."}), 400

    script_text = ""
    source_mode = "paste"

    if file and file.filename:
        source_mode = "upload"
        script_text = extract_script_text(file)

        if not script_text.strip() and not pasted_text:
            return jsonify({
                "error": "The formatted script could not be read cleanly.",
                "needs_paste": True,
                "message": "Please paste the script text to continue."
            }), 422

    if pasted_text:
        script_text = pasted_text
        source_mode = "paste"

    if not script_text.strip():
        return jsonify({"error": "No script text was provided."}), 400

    brain_data = {}
    try:
        brain_file = OUTPUT_DIR / "approved_brain_output.json"
        if brain_file.exists():
            brain_data = json.loads(brain_file.read_text(encoding="utf-8"))
    except Exception:
        pass

    log_usage("actor_prep_start", role=character_name, mode=source_mode)

    try:
        build_actor_prep_pdf(script_text, character_name, LATEST_ACTOR_PREP_PDF, brain_data=brain_data)
    except Exception as e:
        log_usage("actor_prep_complete", success=False, role=character_name, error="actor_prep_failed")
        return jsonify({"error": f"Actor preparation failed: {e}"}), 500

    if not LATEST_ACTOR_PREP_PDF.exists():
        log_usage("actor_prep_complete", success=False, role=character_name, error="actor_pdf_missing")
        return jsonify({"error": "Actor prep PDF was not created."}), 500

    log_usage("actor_prep_complete", success=True, role=character_name)

    return jsonify({
        "summary_note": f"Your actor preparation packet for {character_name} is ready.",
        "report_pdf": str(LATEST_ACTOR_PREP_PDF.name),
    })




@app.route("/actor-booked-pass", methods=["POST"])
def actor_booked_pass():
    character_name = (request.form.get("character_name") or "").strip()
    pasted_text = (request.form.get("script_text") or "").strip()
    file = request.files.get("script")

    if not character_name:
        return jsonify({"error": "Please enter the role you are preparing."}), 400

    script_text = ""
    source_mode = "paste"

    if file and file.filename:
        source_mode = "upload"
        script_text = extract_script_text(file)

        if not script_text.strip() and not pasted_text:
            return jsonify({
                "error": "The formatted script could not be read cleanly.",
                "needs_paste": True,
                "message": "Please paste the script text to continue."
            }), 422

    if pasted_text:
        script_text = pasted_text
        source_mode = "paste"

    if not script_text.strip():
        return jsonify({"error": "No script text was provided."}), 400

    brain_data = {}
    try:
        brain_file = OUTPUT_DIR / "approved_brain_output.json"
        if brain_file.exists():
            brain_data = json.loads(brain_file.read_text(encoding="utf-8"))
    except Exception:
        pass

    log_usage("actor_booked_start", role=character_name, mode=source_mode)

    try:
        build_actor_booked_pdf(script_text, character_name, LATEST_ACTOR_BOOKED_PDF, brain_data=brain_data)
    except Exception as e:
        log_usage("actor_booked_complete", success=False, role=character_name, error="actor_booked_failed")
        return jsonify({"error": f"Booked role preparation failed: {e}"}), 500

    if not LATEST_ACTOR_BOOKED_PDF.exists():
        log_usage("actor_booked_complete", success=False, role=character_name, error="actor_booked_pdf_missing")
        return jsonify({"error": "Booked role PDF was not created."}), 500

    log_usage("actor_booked_complete", success=True, role=character_name)

    return jsonify({
        "summary_note": f"{character_name.title()} is ready for the set. Your full role preparation packet breaks down every speaking beat, scene by scene, with continuity notes and performance priorities built in.",
        "report_pdf": str(LATEST_ACTOR_BOOKED_PDF.name),
    })


@app.route("/output/latest_actor_booked_report.pdf")
def actor_booked_latest_pdf():
    if not LATEST_ACTOR_BOOKED_PDF.exists():
        abort(404)
    return send_file(LATEST_ACTOR_BOOKED_PDF, as_attachment=False)


@app.route("/download/latest_actor_booked_report.pdf")
def actor_booked_latest_download_pdf():
    if not LATEST_ACTOR_BOOKED_PDF.exists():
        abort(404)
    return send_file(LATEST_ACTOR_BOOKED_PDF, as_attachment=True)


@app.route("/output/latest_actor_prep_report.pdf")
def actor_prep_latest_pdf():
    if not LATEST_ACTOR_PREP_PDF.exists():
        abort(404)
    return send_file(LATEST_ACTOR_PREP_PDF, as_attachment=False)


@app.route("/download/latest_actor_prep_report.pdf")
def actor_prep_latest_download_pdf():
    if not LATEST_ACTOR_PREP_PDF.exists():
        abort(404)
    return send_file(LATEST_ACTOR_PREP_PDF, as_attachment=True)

# ===== ACTOR PREP ROUTES END =========================

# ===== FEEDBACK ROUTE START ==========================
@app.route("/feedback", methods=["POST"])
def submit_feedback():
    data = request.get_json(silent=True) or {}
    feedback_type = data.get("type", "").strip()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"ok": False, "error": "No message"}), 400

    feedback_file = OUTPUT_DIR / "feedback.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] type={feedback_type or 'none'} | name={name or 'anon'} | email={email or 'none'} | {message}\n"

    with open(feedback_file, "a", encoding="utf-8") as f:
        f.write(line)

    return jsonify({"ok": True})
# ===== FEEDBACK ROUTE END ============================

@app.route("/generate-slide-options", methods=["POST"])
def generate_slide_options():
    import urllib.request as _urlreq

    data = request.get_json(silent=True) or {}
    slide_title = (data.get("slide_title") or "").strip()
    slide_body = (data.get("slide_body") or "").strip()
    user_prompt = (data.get("user_prompt") or "").strip()
    slide_number = int(data.get("slide_number") or 1)
    current_image_path = (data.get("current_image_path") or "").strip()
    current_image_url = (data.get("current_image_url") or "").strip()

    fal_key = os.environ.get("FAL_API_KEY", "")
    if not fal_key:
        return jsonify({"error": "Image generation not configured"}), 503

    brain_file = BASE_DIR / "approved_brain_output.json"
    brain = {}
    if brain_file.exists():
        try:
            brain = json.loads(brain_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    from deck_builder import build_image_prompt
    base = build_image_prompt(slide_title, brain)
    if user_prompt:
        base = base.replace(", 16:9 aspect ratio", f", {user_prompt}, 16:9 aspect ratio")

    variations = [
        base.replace(", 16:9 aspect ratio", ", wide establishing shot, epic scale, golden hour light, 16:9 aspect ratio"),
        base.replace(", 16:9 aspect ratio", ", dramatic close-up, intense emotion, shallow depth of field, 16:9 aspect ratio"),
    ]

    regen_dir = BASE_DIR / "generated_images" / "regen"
    regen_dir.mkdir(parents=True, exist_ok=True)

    options = []
    if current_image_path and current_image_path != "__none__":
        options.append({
            "option_id": "selected",
            "label": "Current Pick",
            "image_path": current_image_path,
            "image_url": current_image_url,
            "image_source": "fal_generated",
        })

    labels = ["Wide Shot", "Close-Up"]
    for i, prompt in enumerate(variations):
        safe_title = re.sub(r"[^a-z0-9_]", "_", slide_title.lower())[:30]
        save_path = regen_dir / f"{slide_number:02d}_{safe_title}_opt{i+1}.jpg"
        payload = json.dumps({
            "prompt": prompt,
            "image_size": "landscape_16_9",
            "num_inference_steps": 4,
            "num_images": 1,
            "enable_safety_checker": True,
        }).encode("utf-8")
        req = _urlreq.Request(
            "https://fal.run/fal-ai/flux/schnell",
            data=payload,
            headers={"Authorization": f"Key {fal_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with _urlreq.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            image_url = result["images"][0]["url"]
            _urlreq.urlretrieve(image_url, save_path)
            options.append({
                "option_id": f"opt_{i+1}",
                "label": labels[i],
                "image_path": str(save_path),
                "image_url": f"/project-file?path=generated_images/regen/{save_path.name}",
                "image_source": "fal_generated",
            })
        except Exception as e:
            print(f"⚠️ Option {i+1} generation failed: {e}")

    return jsonify({"options": options})


@app.route("/regenerate-slide-image", methods=["POST"])
def regenerate_slide_image():
    import urllib.request as _urlreq
    import urllib.error as _urlerr

    data = request.get_json(silent=True) or {}
    slide_title = (data.get("slide_title") or "").strip()
    slide_body = (data.get("slide_body") or "").strip()
    user_prompt = (data.get("user_prompt") or "").strip()
    slide_number = int(data.get("slide_number") or 1)

    fal_key = os.environ.get("FAL_API_KEY", "")
    if not fal_key:
        return jsonify({"error": "Image generation not configured"}), 503

    brain_file = BASE_DIR / "approved_brain_output.json"
    brain = {}
    if brain_file.exists():
        try:
            brain = json.loads(brain_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    from deck_builder import build_image_prompt
    base_prompt = build_image_prompt(slide_title, brain)
    if user_prompt:
        base_prompt = base_prompt.replace(", 16:9 aspect ratio", f", {user_prompt}, 16:9 aspect ratio")

    payload = json.dumps({
        "prompt": base_prompt,
        "image_size": "landscape_16_9",
        "num_inference_steps": 4,
        "num_images": 1,
        "enable_safety_checker": True,
    }).encode("utf-8")

    req = _urlreq.Request(
        "https://fal.run/fal-ai/flux/schnell",
        data=payload,
        headers={"Authorization": f"Key {fal_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with _urlreq.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        image_url = result["images"][0]["url"]

        regen_dir = BASE_DIR / "generated_images" / "regen"
        regen_dir.mkdir(parents=True, exist_ok=True)
        safe_title = re.sub(r"[^a-z0-9_]", "_", slide_title.lower())[:40]
        save_path = regen_dir / f"{slide_number:02d}_{safe_title}.jpg"
        _urlreq.urlretrieve(image_url, save_path)

        serve_url = f"/project-file?path=generated_images/regen/{save_path.name}"
        return jsonify({"image_url": serve_url, "image_path": str(save_path)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/contact", methods=["POST"])
def submit_contact():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"ok": False, "error": "No message"}), 400

    contact_file = OUTPUT_DIR / "contact.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] name={name or 'anon'} | email={email or 'none'} | {message}\n"

    with open(contact_file, "a", encoding="utf-8") as f:
        f.write(line)

    return jsonify({"ok": True})

# ===== STARTUP CLEANUP START =========================
def _clear_stock_images_once():
    visuals_dir = BASE_DIR / "visuals"
    sentinel = visuals_dir / ".stock_cleared"
    if sentinel.exists():
        return
    if not visuals_dir.exists():
        return
    cleared = 0
    for child in visuals_dir.iterdir():
        if child.is_dir() and child.name != "user_uploaded":
            try:
                shutil.rmtree(child)
                cleared += 1
            except Exception as e:
                print(f"⚠️ Could not remove {child.name}: {e}")
    sentinel.touch()
    print(f"🧹 Stock images cleared on startup ({cleared} folders removed)")

_clear_stock_images_once()
# ===== STARTUP CLEANUP END ===========================

# ===== APP RUN START =================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


# ===== APP RUN END ===================================
