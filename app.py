# =====================================================
# ===== EVOLUM MASTER APP STRUCTURE (V1 BETA) =========
# =====================================================

# ===== IMPORTS / SETUP START =========================
# BETA v2_0 BUILD 1.1 — STABLE

from flask import Flask, request, render_template, send_file, jsonify, abort, session, redirect, url_for
from pathlib import Path
import json
import io
import contextlib
import shutil
import subprocess
import os
import importlib.util
import time
import re
import urllib.request
import urllib.error
import hashlib
import secrets
import string
from datetime import datetime
from urllib.parse import unquote, quote

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from pptx import Presentation
from pypdf import PdfReader
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from dai_tools import (
    build_actor_prep_pdf, build_actor_booked_pdf, build_simple_analysis_pdf, run_deck_pipeline,
    normalize_project_relative_path, project_file_url_for_path, normalize_manifest_image_options,
    newest_generated_file, publish_latest_outputs, rebuild_refined_deck,
)

# ===== IMPORTS / SETUP END ===========================

# ===== GLOBAL CONFIG / PATHS START ===================
app = Flask(__name__)

_REFINE_BUILDER_MODULE = None
_LATEST_SLIDE_PAYLOAD_CACHE = {"key": None, "payload": None}
app.secret_key = os.environ.get("SECRET_KEY", "evolum-beta-gate-v4-7")

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
DB_ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None

def db_check() -> bool:
    if not DB_ENGINE:
        return False
    with DB_ENGINE.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True

def db_init() -> None:
    if not DB_ENGINE:
        raise RuntimeError("DATABASE_URL is not configured")
    with DB_ENGINE.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS beta_users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE,
                name TEXT,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS activity_events (
                id SERIAL PRIMARY KEY,
                user_email TEXT,
                event_type TEXT NOT NULL,
                route TEXT,
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("ALTER TABLE beta_users ADD COLUMN IF NOT EXISTS name TEXT"))
        conn.execute(text("ALTER TABLE beta_users ADD COLUMN IF NOT EXISTS password_hash TEXT"))
        conn.execute(text("ALTER TABLE beta_users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
        conn.execute(text("ALTER TABLE activity_events ADD COLUMN IF NOT EXISTS user_email TEXT"))
        conn.execute(text("ALTER TABLE activity_events ADD COLUMN IF NOT EXISTS route TEXT"))

def log_activity_event(event_type: str, route: str = "", user_email: str = "", metadata: dict | None = None) -> None:
    if not DB_ENGINE:
        return
    try:
        with DB_ENGINE.begin() as conn:
            conn.execute(text("""
                INSERT INTO activity_events (user_email, event_type, route, metadata_json)
                VALUES (:user_email, :event_type, :route, :metadata_json)
            """), {
                "user_email": user_email or "",
                "event_type": event_type,
                "route": route or "",
                "metadata_json": json.dumps(metadata or {}),
            })
    except Exception as e:
        print(f"⚠️ Activity log write failed: {e}", flush=True)


def get_current_user_email() -> str:
    return (session.get("user_email") or "").strip()

def get_current_user_name() -> str:
    return (session.get("user_name") or "").strip()

def get_user_by_email(email: str):
    email = (email or "").strip().lower()
    if not email or not DB_ENGINE:
        return None
    with DB_ENGINE.connect() as conn:
        row = conn.execute(text("""
            SELECT id, email, name, password_hash, created_at,
                   stripe_customer_id, stripe_subscription_id, subscription_active
            FROM beta_users
            WHERE lower(email) = :email
            LIMIT 1
        """), {"email": email}).mappings().first()
    return dict(row) if row else None

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
STATUS_FILE = BASE_DIR / "status.txt"
ACTIVE_PROJECT_FILE = BASE_DIR / "active_project.txt"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEMO_DECK = BASE_DIR / "static" / "NOT_TODAY_Pitch_Deck_FINAL.pdf"

LATEST_PPTX = OUTPUT_DIR / "latest.pptx"
LATEST_PDF = OUTPUT_DIR / "latest.pdf"

LATEST_ANALYSIS_JSON = OUTPUT_DIR / "latest_analysis_report.json"
LATEST_ANALYSIS_PDF = OUTPUT_DIR / "latest_analysis_report.pdf"
LATEST_ACTOR_PREP_PDF = OUTPUT_DIR / "latest_actor_prep_report.pdf"
LATEST_ACTOR_PREP_JSON = OUTPUT_DIR / "latest_actor_prep_report.json"
LATEST_ACTOR_BOOKED_PDF = OUTPUT_DIR / "latest_actor_booked_report.pdf"
LATEST_ACTOR_BOOKED_JSON = OUTPUT_DIR / "latest_actor_booked_report.json"

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
_TMDB_CACHE: dict = {}
LATEST_DECK_MANIFEST_JSON = OUTPUT_DIR / "latest_deck_manifest.json"

ALLOWED_EXTENSIONS = {".txt", ".pdf"}

ACCESS_CODES = [
    "EVOLUM-REEL-471",
    "EVOLUM-SLATE-829",
    "EVOLUM-GRIP-356",
    "EVOLUM-FRAME-914",
    "EVOLUM-LENS-273",
    "EVOLUM-ROLL-648",
    "EVOLUM-MARK-195",
    "EVOLUM-CUT-537",
    "EVOLUM-FADE-762",
    "EVOLUM-WRAP-483",
]

BETA_ACCESS_LOGS_DIR = BASE_DIR / "beta_access_logs"
BETA_ACCESS_LOGS_DIR.mkdir(parents=True, exist_ok=True)


def is_render_env() -> bool:
    return os.environ.get("RENDER", "").lower() == "true"


def has_beta_access() -> bool:
    return (
        session.get("beta_access") is True or
        bool(session.get("user_email")) or
        session.get("subscription_active") is True
    )


def ensure_subscription_columns():
    if not DB_ENGINE:
        return
    with DB_ENGINE.begin() as conn:
        conn.execute(text("ALTER TABLE beta_users ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT"))
        conn.execute(text("ALTER TABLE beta_users ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT"))
        conn.execute(text("ALTER TABLE beta_users ADD COLUMN IF NOT EXISTS subscription_active BOOLEAN DEFAULT FALSE"))


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


def set_status(text: str, project_id: str = None):
    if project_id:
        STATUS_FILE.write_text(f"{text}|{project_id}", encoding="utf-8")
    else:
        current = STATUS_FILE.read_text(encoding="utf-8").strip() if STATUS_FILE.exists() else ""
        existing_pid = current.split("|")[1] if "|" in current else ""
        STATUS_FILE.write_text(f"{text}|{existing_pid}" if existing_pid else text, encoding="utf-8")


def get_status() -> str:
    if not STATUS_FILE.exists():
        return "IDLE"
    raw = STATUS_FILE.read_text(encoding="utf-8").strip()
    return (raw.split("|")[0] if "|" in raw else raw) or "IDLE"


def get_status_project_id() -> str:
    if not STATUS_FILE.exists():
        return ""
    raw = STATUS_FILE.read_text(encoding="utf-8").strip()
    return raw.split("|")[1] if "|" in raw else ""


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def clear_latest_targets():
    for path in (LATEST_PPTX, LATEST_PDF):
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass


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


FAL_API_KEY = os.environ.get("FAL_API_KEY", "")

_SLIDE_VISUAL_CONCEPTS = {
    "logline": "cinematic establishing shot, wide angle, dramatic lighting",
    "synopsis": "cinematic scene, atmospheric, narrative moment",
    "synopsis 2": "cinematic scene, mid-shot, dramatic tension",
    "synopsis 3": "cinematic scene, close-up, emotional intensity",
    "protagonist": "cinematic portrait, single character, dramatic lighting, film still",
    "antagonist": "cinematic portrait, menacing figure, dramatic shadows, film still",
    "supporting characters": "cinematic ensemble shot, multiple characters, film still",
    "world": "cinematic landscape, establishing shot, rich environment",
    "hook": "cinematic close-up, tension, dramatic moment",
    "conflict": "cinematic confrontation, dramatic tension, high stakes",
    "stakes": "cinematic wide shot, weight of consequence, dramatic",
    "tone": "cinematic mood shot, atmospheric lighting, visual tone",
    "story engine": "cinematic action, driving force, momentum",
    "reversal": "cinematic turning point, dramatic shift, pivotal moment",
    "themes": "cinematic symbolic imagery, thematic visual metaphor",
    "why this movie": "cinematic wide shot, cultural moment, compelling imagery",
    "comparables": "cinematic collage feel, prestige film aesthetic",
    "market projections": "cinematic wide shot, commercial appeal, high production value",
    "closing statement": "cinematic final frame, powerful, memorable",
}

_GENRE_STYLE = {
    "horror": "dark, unsettling, atmospheric horror, shadows, practical effects aesthetic",
    "thriller": "tense, noir-influenced, sharp contrast, suspenseful",
    "comedy": "warm lighting, vibrant colors, playful composition",
    "drama": "naturalistic lighting, intimate, emotionally grounded",
    "action": "dynamic, kinetic energy, bold framing, high contrast",
    "sci-fi": "futuristic, cool tones, technological, epic scale",
    "fantasy": "magical, rich colors, otherworldly, painterly lighting",
    "romance": "warm golden tones, soft focus, intimate, emotional",
    "documentary": "gritty realism, candid, natural light, observational",
    "animation": "stylized, vibrant, expressive, dynamic",
}

def normalize_key(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    return re.sub(r"\s+", " ", cleaned)

def load_latest_brain_output(slide_plan_file=None) -> dict:
    project_dir = find_latest_project_dir(slide_plan_file)
    candidates = [project_dir / "approved_brain_output.json", BASE_DIR / "approved_brain_output.json"]
    for candidate in candidates:
        if candidate.exists():
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except Exception:
                continue
    return {}

def build_fal_image_prompt(slide_title: str, slide_body: str = "", user_prompt: str = "", brain_output: dict | None = None, variation: str = "") -> str:
    brain_output = brain_output or {}
    normalized = normalize_key(slide_title)
    concept = _SLIDE_VISUAL_CONCEPTS.get(normalized, "cinematic scene, dramatic lighting, film still")
    genre = str(brain_output.get("genre", "drama")).lower()
    genre_style = next((style for g, style in _GENRE_STYLE.items() if g in genre), "cinematic, naturalistic lighting, film aesthetic")
    tone = str(brain_output.get("tone", "")).replace("\n", " ").strip()
    world = str(brain_output.get("world", "")).replace("\n", " ").strip()
    body_hint = str(slide_body or "").replace("\n", " ").strip()
    parts = [concept, genre_style]
    if world:
        parts.append(f"set in {world[:120]}")
    if tone:
        parts.append(tone[:100])
    if body_hint:
        parts.append(body_hint[:180])
    if user_prompt:
        parts.append(user_prompt[:220])
    if variation:
        parts.append(variation)
    parts.extend(["professional film still", "35mm", "shallow depth of field", "no text", "no watermarks", "ultra-detailed", "photorealistic", "16:9 aspect ratio"])
    return ", ".join([p for p in parts if p])

def generate_fal_image(prompt: str, cache_path: Path) -> Path | None:
    if not FAL_API_KEY:
        return None
    if cache_path.exists():
        return cache_path
    url = "https://fal.run/fal-ai/flux/schnell"
    payload = json.dumps({
        "prompt": prompt,
        "image_size": "landscape_16_9",
        "num_inference_steps": 4,
        "num_images": 1,
        "enable_safety_checker": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Key {FAL_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        image_url = ((result.get("images") or [{}])[0]).get("url", "")
        if not image_url:
            return None
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(image_url, cache_path)
        print(f"✨ FAL generated image for prompt: {prompt[:80]}...", flush=True)
        return cache_path
    except Exception as e:
        print(f"⚠️ FAL image generation failed: {e}", flush=True)
        return None

def fal_generated_image_payload(cache_path: Path) -> dict:
    rel = normalize_project_relative_path(str(cache_path))
    return {
        "image_path": rel,
        "image_name": cache_path.name,
        "image_source": "fal_generated",
        "image_url": project_file_url_for_path(rel),
    }

def generate_slide_option_images(slide_plan_file, slide_title: str, slide_body: str = "", user_prompt: str = "", slide_number: int = 1) -> list[dict]:
    brain_output = load_latest_brain_output(slide_plan_file)
    project_dir = find_latest_project_dir(slide_plan_file)
    generated_dir = project_dir / "generated_images"
    safe_title = re.sub(r"[^a-z0-9_]+", "_", normalize_key(slide_title) or f"slide_{slide_number}").strip("_") or f"slide_{slide_number}"
    prompt_variations = [
        ("wide", "wide cinematic composition, strong establishing frame"),
        ("portrait", "character-focused frame, expressive subject emphasis"),
        ("dramatic", "dramatic tension, premium cinematic lighting, heightened emotion"),
        ("alt", "alternate composition, fresh visual interpretation, production design detail"),
    ]
    options = []
    for idx, (label_key, variation) in enumerate(prompt_variations, start=1):
        prompt = build_fal_image_prompt(slide_title, slide_body=slide_body, user_prompt=user_prompt, brain_output=brain_output, variation=variation)
        prompt_hash = hashlib.md5(prompt.encode("utf-8")).hexdigest()[:10]
        cache_path = generated_dir / f"{int(slide_number):02d}_{safe_title}_{label_key}_{prompt_hash}.jpg"
        generated = generate_fal_image(prompt, cache_path)
        if not generated:
            continue
        payload = fal_generated_image_payload(generated)
        payload.update({
            "rank": idx,
            "option_id": f"fal_{label_key}_{prompt_hash}",
            "label": f"Option {idx}",
            "focus": variation,
        })
        options.append(payload)
    return options

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
    builder_path = BASE_DIR / "deck_builder.py"
    if builder_path.exists():
        parts.append(f"builder:{builder_path}:{builder_path.stat().st_mtime_ns}")

    return "|".join(parts)


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
        try:
            for _project_dir_name in ["project_dir", "working_dir", "output_dir", "project_path"]:
                if _project_dir_name in locals() and locals()[_project_dir_name]: apply_upload_text_overrides(locals()[_project_dir_name], submitted_logline, submitted_synopsis)
                break
        except Exception:
            pass
            
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
    return redirect("/?auth_error=" + quote("Incorrect access code. Please try again."))


@app.route("/create-account", methods=["POST"])
def create_account():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = (request.form.get("password") or "").strip()
    access_code = (request.form.get("access_code") or "").strip()

    if not name or not email or not password or not access_code:
        return redirect("/?auth_error=" + quote("Please complete all fields including your access code."))

    if access_code not in ACCESS_CODES:
        log_beta_access(access_code or "blank", "CREATE ACCOUNT ACCESS FAILED")
        return redirect("/?auth_error=" + quote("That access code is not approved yet."))

    try:
        db_init()
        existing = get_user_by_email(email)
        if existing:
            return redirect("/?auth_error=" + quote("That email already has an account. Please sign in."))

        password_hash = generate_password_hash(password)
        with DB_ENGINE.begin() as conn:
            row = conn.execute(text("""
                INSERT INTO beta_users (email, name, password_hash)
                VALUES (:email, :name, :password_hash) RETURNING id
            """), {"email": email, "name": name, "password_hash": password_hash}).fetchone()

        session["user_id"] = str(row[0])
        session["user_email"] = email
        session["user_name"] = name
        session["beta_access"] = True
        session["beta_code"] = access_code

        log_beta_access(access_code, "ACCOUNT CREATED")
        log_activity_event("account_created", route="/create-account", user_email=email, metadata={"name": name})
        return redirect("/?welcome=new")
    except Exception as e:
        return redirect("/?auth_error=" + quote(f"Account creation failed: {e}"))


@app.route("/sign-in", methods=["POST"])
def sign_in():
    email = (request.form.get("email") or "").strip().lower()
    password = (request.form.get("password") or "").strip()

    if not email or not password:
        return redirect("/?auth_error=" + quote("Please enter your email and password."))

    try:
        db_init()
        user = get_user_by_email(email)
        if not user or not user.get("password_hash") or not check_password_hash(user["password_hash"], password):
            log_activity_event("sign_in_failed", route="/sign-in", user_email=email)
            return redirect("/?auth_error=" + quote("We couldn't sign you in with those credentials."))

        session["user_id"] = str(user["id"])
        session["user_email"] = user["email"]
        session["user_name"] = user.get("name") or ""
        session["beta_access"] = True
        if user.get("subscription_active"):
            session["subscription_active"] = True

        log_activity_event("sign_in", route="/sign-in", user_email=user["email"])
        return redirect("/?welcome=return")
    except Exception as e:
        return redirect("/?auth_error=" + quote(f"Sign in failed: {e}"))


@app.route("/feedback", methods=["POST"])
def submit_feedback():
    data = request.get_json(silent=True) or {}
    category = (data.get("category") or "").strip()
    message = (data.get("message") or "").strip()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or session.get("user_email") or "").strip()
    if not message:
        return jsonify({"error": "No message provided."}), 400
    log_activity_event("feedback_message", route="/feedback",
                       user_email=email,
                       metadata={"name": name, "category": category, "message": message[:500]})
    return jsonify({"ok": True})

@app.route("/contact", methods=["POST"])
def contact():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "No message provided."}), 400
    log_activity_event("contact_message", route="/contact",
                       user_email=email or session.get("user_email"),
                       metadata={"name": name, "message": message[:500]})
    return jsonify({"ok": True})


@app.route("/logout")
def logout():
    email = get_current_user_email()
    if email:
        log_activity_event("sign_out", route="/logout", user_email=email)
    session.clear()
    return redirect("/?signed_out=1")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/cancel")
def cancel_page():
    if not session.get("user_id") and not session.get("user_email"):
        return redirect("/")
    user = get_user_by_email(session.get("user_email", "")) if session.get("user_email") else None
    if not user:
        return redirect("/")
    import datetime
    created_at = user.get("created_at")
    in_window = False
    if created_at:
        if isinstance(created_at, str):
            created_at = datetime.datetime.fromisoformat(created_at)
        now = datetime.datetime.utcnow()
        if created_at.tzinfo:
            now = datetime.datetime.now(datetime.timezone.utc)
        in_window = (now - created_at).total_seconds() <= 3 * 24 * 3600
    has_sub = bool(user.get("stripe_subscription_id") and user.get("subscription_active"))
    return render_template("cancel.html",
        user_name=user.get("name", ""),
        in_window=in_window,
        has_sub=has_sub,
    )


@app.route("/cancel/confirm", methods=["POST"])
def cancel_confirm():
    if not session.get("user_id") and not session.get("user_email"):
        return redirect("/")
    user = get_user_by_email(session.get("user_email", "")) if session.get("user_email") else None
    if not user:
        return redirect("/")

    import datetime, stripe as stripe_lib
    stripe_lib.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

    sub_id = user.get("stripe_subscription_id")
    refund_issued = False
    error_msg = None

    if sub_id and stripe_lib.api_key:
        try:
            # Check if within 3-day window
            created_at = user.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.datetime.fromisoformat(created_at)
            now = datetime.datetime.utcnow()
            if created_at and created_at.tzinfo:
                now = datetime.datetime.now(datetime.timezone.utc)
            in_window = created_at and (now - created_at).total_seconds() <= 3 * 24 * 3600

            if in_window:
                # Get latest invoice and refund the payment
                sub = stripe_lib.Subscription.retrieve(sub_id, expand=["latest_invoice.payment_intent"])
                pi = sub.latest_invoice.payment_intent if sub.latest_invoice else None
                if pi and pi.status == "succeeded":
                    stripe_lib.Refund.create(payment_intent=pi.id)
                    refund_issued = True

            # Cancel the subscription immediately
            stripe_lib.Subscription.cancel(sub_id)
        except Exception as e:
            error_msg = str(e)

    # Mark inactive in DB regardless of Stripe result
    if DB_ENGINE:
        with DB_ENGINE.begin() as conn:
            conn.execute(text(
                "UPDATE beta_users SET subscription_active=FALSE WHERE id=:uid"
            ), {"uid": user["id"]})

    log_activity_event("cancel_subscription", route="/cancel/confirm",
                       user_email=user.get("email", ""),
                       metadata={"refund_issued": refund_issued, "error": error_msg})
    session.clear()
    return render_template("cancel_done.html", refund_issued=refund_issued)


# ===== STRIPE PAYMENT ROUTES START ===================
@app.route("/stripe-env-check")
def stripe_env_check():
    sk = os.environ.get("STRIPE_SECRET_KEY", "")
    pid = os.environ.get("STRIPE_PRICE_ID", "")
    return jsonify({
        "sk_prefix": sk[:10] if sk else "MISSING",
        "sk_len": len(sk),
        "price_id": pid,
        "price_id_len": len(pid),
    })

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    import stripe as stripe_lib
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = (request.form.get("password") or "").strip()

    if not name or not email or not password:
        return redirect("/?auth_error=" + quote("Please fill in all fields to continue."))
    if len(password) < 6:
        return redirect("/?auth_error=" + quote("Password must be at least 6 characters."))

    try:
        db_init()
        ensure_subscription_columns()
        if get_user_by_email(email):
            return redirect("/?auth_error=" + quote("That email already has an account. Please sign in."))
    except Exception:
        pass

    stripe_lib.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_lib.api_key:
        return redirect("/?auth_error=" + quote("Payment system unavailable — please try again later."))

    session["pending_name"] = name
    session["pending_email"] = email
    session["pending_password_hash"] = generate_password_hash(password)

    try:
        base_url = request.host_url.rstrip("/")
        checkout = stripe_lib.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": 500,
                    "recurring": {"interval": "month"},
                    "product_data": {
                        "name": "EVOLUM Studio",
                        "description": "Full access to the EVOLUM beta — pitch deck builder, script analyzer, and actor tools. Cancel anytime.",
                    },
                },
                "quantity": 1,
            }],
            mode="subscription",
            customer_email=email,
            custom_text={
                "submit": {"message": "You're joining the private beta. $5/month · cancel any time."},
            },
            success_url=f"{base_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/?cancelled=1",
        )
        return redirect(checkout.url, code=303)
    except Exception as e:
        return redirect("/?auth_error=" + quote(f"Could not start checkout: {e}"))


@app.route("/payment-success")
def payment_success():
    import stripe as stripe_lib
    stripe_lib.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    stripe_session_id = request.args.get("session_id", "")

    if not stripe_lib.api_key or not stripe_session_id:
        return redirect("/")

    try:
        checkout = stripe_lib.checkout.Session.retrieve(stripe_session_id)
        if checkout.payment_status not in ("paid", "no_payment_required"):
            return redirect("/?payment_failed=1")

        name = session.pop("pending_name", "") or ""
        email = session.pop("pending_email", "") or checkout.customer_email or ""
        password_hash = session.pop("pending_password_hash", "") or generate_password_hash(secrets.token_hex(16))
        customer_id = checkout.customer or ""
        subscription_id = checkout.subscription or ""

        if not email:
            return redirect("/")

        db_init()
        ensure_subscription_columns()
        existing = get_user_by_email(email)

        if existing:
            with DB_ENGINE.begin() as conn:
                conn.execute(text("""
                    UPDATE beta_users SET stripe_customer_id=:cid, stripe_subscription_id=:sid,
                    subscription_active=TRUE WHERE lower(email)=:email
                """), {"cid": customer_id, "sid": subscription_id, "email": email})
            user_id = str(existing["id"])
            name = existing.get("name") or name
        else:
            if not name:
                name = email.split("@")[0].title()
            with DB_ENGINE.begin() as conn:
                row = conn.execute(text("""
                    INSERT INTO beta_users (email, name, password_hash, stripe_customer_id, stripe_subscription_id, subscription_active)
                    VALUES (:email, :name, :ph, :cid, :sid, TRUE) RETURNING id
                """), {"email": email, "name": name, "ph": password_hash,
                       "cid": customer_id, "sid": subscription_id}).fetchone()
                user_id = str(row[0])

        session["user_id"] = user_id
        session["user_email"] = email
        session["user_name"] = name
        session["beta_access"] = True
        session["subscription_active"] = True

        log_activity_event("payment_success", route="/payment-success", user_email=email,
                           metadata={"stripe_session": stripe_session_id})
        return redirect("/studio")

    except Exception as e:
        return redirect("/")
# ===== STRIPE PAYMENT ROUTES END =====================


# ===== CORE ROUTES START =============================
@app.route("/")
def index():
    if get_current_user_email():
        log_activity_event("page_view", route="/", user_email=get_current_user_email(), metadata={"name": get_current_user_name()})
    return render_template(
        "index.html",
        is_render=is_render_env(),
        user_logged_in=has_beta_access(),
        user_name=get_current_user_name() or "",
        auth_error=request.args.get("auth_error", ""),
        show_auth=bool(request.args.get("auth_error") or request.args.get("cancelled")),
    )
from functools import wraps

def require_login(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if session.get("user_id"):
            return view_func(*args, **kwargs)
        if session.get("user_email") and DB_ENGINE:
            user = get_user_by_email(session["user_email"])
            if user:
                session["user_id"] = str(user["id"])
                return view_func(*args, **kwargs)
        if session.get("beta_access") is True:
            return view_func(*args, **kwargs)
        return redirect("/")
    return wrapper


@app.route("/login-test")
def login_test():
    session.permanent = False
    session["user_id"] = "test_user_001"
    session["user_name"] = "James Evans"
    session["user_email"] = "test@evolumstudio.com"
    return redirect("/studio")

@app.route("/studio")
def studio():
    return redirect("/")


@app.route("/my-projects")
@require_login
def my_projects():
    projects = []
    if DB_ENGINE:
        ensure_projects_table()
        with DB_ENGINE.connect() as conn:
            rows = conn.execute(text("""
                SELECT id, title, type, status, created_at, output_dir
                FROM projects
                WHERE owner_user_id = :uid
                ORDER BY created_at DESC
            """), {"uid": session.get("user_id")}).mappings().all()
            projects = [dict(r) for r in rows]
        for p in projects:
            out = p.get("output_dir")
            p["has_deck"] = bool(out and (BASE_DIR / out / "deck.pdf").exists())
            p.pop("output_dir", None)
            ca = p.get("created_at")
            p["created_at"] = ca.strftime("%b %d, %Y") if hasattr(ca, "strftime") else str(ca)[:10] if ca else ""
            p["id"] = str(p["id"])
    return jsonify({"projects": projects})
@app.route("/studio/chat", methods=["POST"])
@require_login
def studio_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return jsonify({"error": "No message"}), 400

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return jsonify({"reply": "Studio Helper isn't configured yet — ANTHROPIC_API_KEY missing."}), 200

    # Build project context from user's projects
    projects_ctx = ""
    if DB_ENGINE:
        ensure_projects_table()
        with DB_ENGINE.connect() as conn:
            rows = conn.execute(text("""
                SELECT title, type, status FROM projects
                WHERE owner_user_id = :uid ORDER BY created_at DESC LIMIT 5
            """), {"uid": session.get("user_id")}).mappings().all()
            if rows:
                projects_ctx = "User's projects: " + "; ".join(
                    f"{r['title']} ({r['type'] or 'Project'})" for r in rows
                )

    user_name = session.get("user_name") or "Creator"
    system = f"""You are EVOLUM's Studio Helper — a sharp, practical AI partner for film and TV creatives.
EVOLUM is a professional production suite for writers, actors, directors, and producers.

You help with: pitch decks, loglines, synopses, investor pitches, comp titles, script development, actor prep, character breakdowns, market positioning, and general production strategy.

User: {user_name}
{projects_ctx}

Rules:
- Be specific and industry-savvy. No filler or vague encouragement.
- Keep responses concise: 2-3 short paragraphs max unless explicitly asked for more.
- Match the creative's energy — direct, confident, collaborative.
- Do not mention AI, models, or training data. You are a creative partner, not a chatbot.
- Format with short paragraphs. Use bullet lists only when listing discrete items."""

    # Keep last 8 messages to avoid blowing token budget
    trimmed_history = history[-8:] if len(history) > 8 else history
    messages = trimmed_history + [{"role": "user", "content": message}]

    try:
        import anthropic as _anthropic
        client = _anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=system,
            messages=messages,
        )
        reply = (resp.content[0].text or "").strip()
        return jsonify({"reply": reply})
    except Exception as e:
        print(f"⚠️ Studio chat error: {e}", flush=True)
        short_err = str(e)[:120]
        return jsonify({"reply": f"Studio Helper hit an error: {short_err}. Please try again."}), 200


@app.route("/session-test")
def session_test():
    session.clear()
    session["user_id"] = "1"
    session["user_name"] = "James Evans"
    session["user_email"] = "test@evolumstudio.com"
    return redirect("/studio")

PROJECTS = {}

@app.route("/new-project")
def new_project():
    return redirect("/")

@app.route("/project/<project_id>")
def project_workspace(project_id):
    return redirect("/")


@app.route("/project/<project_id>/load", methods=["POST"])
@require_login
def load_project_json(project_id):
    ensure_projects_table()
    uid = session.get("user_id")
    with DB_ENGINE.connect() as conn:
        row = conn.execute(text(
            "SELECT output_dir FROM projects WHERE id = :id AND owner_user_id = :uid"
        ), {"id": project_id, "uid": uid}).mappings().first()
    if not row or not row["output_dir"]:
        return jsonify({"ok": False, "error": "Not found"}), 404
    proj_dir = BASE_DIR / row["output_dir"]
    try:
        if (proj_dir / "deck.pptx").exists():
            shutil.copy2(proj_dir / "deck.pptx", LATEST_PPTX)
        if (proj_dir / "deck.pdf").exists():
            shutil.copy2(proj_dir / "deck.pdf", LATEST_PDF)
        if (proj_dir / "deck_manifest.json").exists():
            shutil.copy2(proj_dir / "deck_manifest.json", LATEST_DECK_MANIFEST_JSON)
        set_status("COMPLETE", project_id=project_id)
        session["active_project_id"] = project_id
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True, "project_id": project_id})


@app.route("/project/<project_id>/delete-asset", methods=["POST"])
@require_login
def delete_project_asset(project_id):
    filename = (request.form.get("filename") or "").strip()
    if not filename or "/" in filename or "\\" in filename or filename.startswith("."):
        return jsonify({"error": "Invalid filename"}), 400
    ensure_projects_table()
    with DB_ENGINE.connect() as conn:
        row = conn.execute(text(
            "SELECT output_dir FROM projects WHERE id = :id AND owner_user_id = :uid"
        ), {"id": project_id, "uid": session.get("user_id")}).mappings().first()
    if not row or not row["output_dir"]:
        return jsonify({"error": "Project not found"}), 404
    proj_dir = (BASE_DIR / row["output_dir"]).resolve()
    file_path = (proj_dir / filename).resolve()
    try:
        file_path.relative_to(proj_dir)
    except ValueError:
        return jsonify({"error": "Invalid path"}), 400
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    file_path.unlink()
    return jsonify({"ok": True})


@app.route("/project/<project_id>/upload-asset", methods=["POST"])
@require_login
def upload_project_asset(project_id):
    ensure_projects_table()
    with DB_ENGINE.connect() as conn:
        row = conn.execute(text(
            "SELECT output_dir FROM projects WHERE id = :id AND owner_user_id = :uid"
        ), {"id": project_id, "uid": session.get("user_id")}).mappings().first()
    if not row or not row["output_dir"]:
        return jsonify({"error": "Project not found"}), 404
    proj_dir = BASE_DIR / row["output_dir"]
    proj_dir.mkdir(parents=True, exist_ok=True)
    f = request.files.get("asset")
    if not f or not f.filename:
        return jsonify({"error": "No file"}), 400
    safe_name = Path(f.filename).name
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".txt", ".fdx", ".docx"}
    if Path(safe_name).suffix.lower() not in allowed_exts:
        return jsonify({"error": "File type not allowed"}), 400
    dest = proj_dir / safe_name
    f.save(dest)
    size_kb = round(dest.stat().st_size / 1024, 1)
    return jsonify({"ok": True, "name": safe_name, "size_kb": size_kb})


@app.route("/project/<project_id>/load-deck", methods=["POST"])
@require_login
def load_project_deck(project_id):
    ensure_projects_table()
    with DB_ENGINE.connect() as conn:
        row = conn.execute(text(
            "SELECT output_dir FROM projects WHERE id = :id AND owner_user_id = :uid"
        ), {"id": project_id, "uid": session.get("user_id")}).mappings().first()
    if not row or not row["output_dir"]:
        return redirect(f"/project/{project_id}")
    proj_dir = BASE_DIR / row["output_dir"]
    try:
        if (proj_dir / "deck.pptx").exists():
            shutil.copy2(proj_dir / "deck.pptx", LATEST_PPTX)
        if (proj_dir / "deck.pdf").exists():
            shutil.copy2(proj_dir / "deck.pdf", LATEST_PDF)
        if (proj_dir / "deck_manifest.json").exists():
            shutil.copy2(proj_dir / "deck_manifest.json", LATEST_DECK_MANIFEST_JSON)
        set_status("COMPLETE")
    except Exception as e:
        print(f"⚠️ load_project_deck error: {e}", flush=True)
        return redirect(f"/project/{project_id}")
    return redirect(f"/?loaded=1&from_project={project_id}")


@app.route("/project/<project_id>/delete", methods=["POST"])
@require_login
def delete_project(project_id):
    ensure_projects_table()
    uid = session.get("user_id")
    with DB_ENGINE.begin() as conn:
        row = conn.execute(text(
            "SELECT id, output_dir FROM projects WHERE id = :id AND owner_user_id = :uid"
        ), {"id": project_id, "uid": uid}).mappings().first()
        if not row:
            return jsonify({"ok": False, "error": "Not found"}), 404
        conn.execute(text(
            "DELETE FROM projects WHERE id = :id AND owner_user_id = :uid"
        ), {"id": project_id, "uid": uid})
    proj_dir = BASE_DIR / "user_data" / str(uid) / str(project_id)
    if proj_dir.exists():
        shutil.rmtree(proj_dir, ignore_errors=True)
    return jsonify({"ok": True})


@app.route("/project/<project_id>/slides")
@require_login
def get_project_slides(project_id):
    ensure_projects_table()
    with DB_ENGINE.connect() as conn:
        row = conn.execute(text(
            "SELECT output_dir FROM projects WHERE id = :id AND owner_user_id = :uid"
        ), {"id": project_id, "uid": session.get("user_id")}).mappings().first()
    if not row or not row["output_dir"]:
        return jsonify({"error": "Project not found", "slides": []}), 404
    proj_dir = BASE_DIR / row["output_dir"]
    manifest_path = proj_dir / "deck_manifest.json"
    if not manifest_path.exists():
        return jsonify({"slides": [], "slide_count": 0, "error": "No deck built yet"}), 200
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            slide_plan_data = json.load(f)
        payload = build_refine_slide_payload(slide_plan_data, slide_plan_file=manifest_path)
        return jsonify(payload)
    except Exception as e:
        return jsonify({"error": str(e), "slides": []}), 500


@app.route("/project/<project_id>/refine", methods=["POST"])
@require_login
def refine_project_deck(project_id):
    ensure_projects_table()
    with DB_ENGINE.connect() as conn:
        row = conn.execute(text(
            "SELECT output_dir FROM projects WHERE id = :id AND owner_user_id = :uid"
        ), {"id": project_id, "uid": session.get("user_id")}).mappings().first()
    if not row or not row["output_dir"]:
        return jsonify({"error": "Project not found"}), 404
    data = request.get_json(silent=True) or {}
    slides = data.get("slides", [])
    if not slides:
        return jsonify({"error": "No slides provided"}), 400
    proj_dir = BASE_DIR / row["output_dir"]
    manifest_path = proj_dir / "deck_manifest.json"
    if not manifest_path.exists():
        return jsonify({"error": "No deck to refine"}), 400
    try:
        result = rebuild_refined_deck(slides, latest_manifest_path=manifest_path, label="")
        if result.get("deck"):
            if LATEST_PPTX.exists():
                shutil.copy2(LATEST_PPTX, proj_dir / "deck.pptx")
            if LATEST_PDF.exists():
                shutil.copy2(LATEST_PDF, proj_dir / "deck.pdf")
            # manifest was already written to proj_dir by rebuild_refined_deck
        return jsonify(result)
    except Exception as e:
        print(f"⚠️ Project refine failed for {project_id}: {e}", flush=True)
        return jsonify({"error": str(e)}), 500


_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        pw = request.form.get("password", "")
        if _ADMIN_PASSWORD and pw == _ADMIN_PASSWORD:
            session["admin_authed"] = True
            return redirect("/admin")
        error = "Incorrect password." if _ADMIN_PASSWORD else "ADMIN_PASSWORD env var not set on this server."
    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_authed", None)
    return redirect("/admin/login")


@app.route("/admin/delete-event/<int:event_id>", methods=["POST"])
def admin_delete_event(event_id):
    if not session.get("admin_authed"):
        return "", 403
    if DB_ENGINE:
        try:
            with DB_ENGINE.connect() as conn:
                conn.execute(text("DELETE FROM activity_events WHERE id = :id"), {"id": event_id})
                conn.commit()
        except Exception:
            pass
    return redirect("/admin")


@app.route("/admin")
def admin():
    if not session.get("admin_authed"):
        return redirect("/admin/login")
    import shutil
    stats = {
        "users": 0, "projects": 0,
        "logins_total": 0, "logins_today": 0, "active_sessions": 0,
        "deck_runs": 0, "script_analyses": 0, "actor_prep": 0, "actor_booked": 0,
        "db_ok": False, "db_error": "", "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "disk_used_mb": 0, "disk_total_mb": 0, "disk_pct": 0,
    }
    users = []
    recent_activity = []
    messages = []

    try:
        projects_dir = BASE_DIR / "sessions"
        if projects_dir.exists():
            used_bytes = sum(f.stat().st_size for f in projects_dir.rglob("*") if f.is_file())
        else:
            used_bytes = 0
        limit_mb = 10 * 1024  # 10 GB limit
        stats["disk_total_mb"] = limit_mb
        stats["disk_used_mb"] = round(used_bytes / (1024 * 1024), 1)
        stats["disk_pct"] = round(stats["disk_used_mb"] / limit_mb * 100, 1)
    except Exception:
        pass

    if not DB_ENGINE:
        return render_template("admin.html", stats=stats, users=users,
                               recent_activity=recent_activity, messages=messages)
    try:
        with DB_ENGINE.connect() as conn:
            stats["db_ok"] = True

            stats["users"] = conn.execute(text("SELECT COUNT(*) FROM beta_users")).scalar() or 0
            stats["projects"] = conn.execute(text("SELECT COUNT(*) FROM projects")).scalar() or 0

            stats["logins_total"] = conn.execute(
                text("SELECT COUNT(*) FROM activity_events WHERE event_type='sign_in'")).scalar() or 0
            stats["logins_today"] = conn.execute(
                text("SELECT COUNT(*) FROM activity_events WHERE event_type='sign_in' AND created_at >= NOW() - INTERVAL '24 hours'")).scalar() or 0
            stats["active_sessions"] = conn.execute(
                text("SELECT COUNT(*) FROM activity_events WHERE event_type='sign_in' AND created_at >= NOW() - INTERVAL '30 minutes'")).scalar() or 0

            stats["deck_runs"] = conn.execute(
                text("SELECT COUNT(*) FROM activity_events WHERE event_type='deck_run'")).scalar() or 0
            stats["script_analyses"] = conn.execute(
                text("SELECT COUNT(*) FROM activity_events WHERE event_type='script_analysis'")).scalar() or 0
            stats["actor_prep"] = conn.execute(
                text("SELECT COUNT(*) FROM activity_events WHERE event_type='actor_prep'")).scalar() or 0
            stats["actor_booked"] = conn.execute(
                text("SELECT COUNT(*) FROM activity_events WHERE event_type='actor_booked'")).scalar() or 0

            rows = conn.execute(text(
                "SELECT id, email, name, created_at FROM beta_users ORDER BY created_at DESC"
            )).mappings().all()
            users = [dict(r) for r in rows]

            rows = conn.execute(text(
                "SELECT id, user_email, event_type, route, created_at FROM activity_events "
                "WHERE event_type NOT IN ('contact_message','feedback_message') "
                "ORDER BY created_at DESC LIMIT 50"
            )).mappings().all()
            recent_activity = [dict(r) for r in rows]

            rows = conn.execute(text(
                "SELECT id, user_email, event_type, metadata_json, created_at FROM activity_events "
                "WHERE event_type IN ('contact_message','feedback_message') "
                "ORDER BY created_at DESC LIMIT 100"
            )).mappings().all()
            messages = [dict(r) for r in rows]

    except Exception as e:
        stats["db_ok"] = False
        stats["db_error"] = str(e)[:120]

    log_lines = []
    try:
        log_path = BASE_DIR / "pipeline.log"
        if log_path.exists():
            raw = log_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
            log_lines = raw[-60:]
    except Exception:
        pass

    return render_template("admin.html", stats=stats, users=users,
                           recent_activity=recent_activity, messages=messages,
                           log_lines=log_lines)

@app.route("/status")
def status():
    return jsonify({
        "status": get_status(),
        "project_id": get_status_project_id() or session.get("active_project_id")
    })
    
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

@app.route("/debug-log")
def debug_log():
    log_path = BASE_DIR / "pipeline.log"
    if not log_path.exists():
        return "No pipeline.log found.", 200, {"Content-Type": "text/plain; charset=utf-8"}
    return log_path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/upload", methods=["POST"])
def upload():
    submitted_logline = (request.form.get("logline") or "").strip()
    submitted_synopsis = (request.form.get("synopsis") or "").strip()
    file = request.files.get("script")

    if not file or file.filename == "":
        return "No file uploaded", 400

    if not allowed_file(file.filename):
        return "Only .txt and .pdf supported", 400

    # Studio mode: create or reuse project record before pipeline starts
    project_title = (request.form.get("project_title") or "").strip()
    project_type = (request.form.get("project_type") or "").strip()
    existing_project_id = (request.form.get("project_id") or "").strip()
    # Auto-title from filename when none supplied
    if not project_title and file and file.filename:
        stem = Path(file.filename).stem
        project_title = stem.replace("_", " ").replace("-", " ").strip().title() or "Untitled Project"
    uid = session.get("user_id")
    if not uid and session.get("user_email") and DB_ENGINE:
        user = get_user_by_email(session["user_email"])
        if user:
            uid = str(user["id"])
            session["user_id"] = uid
    if existing_project_id and uid and DB_ENGINE:
        session["active_project_id"] = existing_project_id
        set_status("UPLOADED", project_id=existing_project_id)
    elif project_title and uid and DB_ENGINE:
        ensure_projects_table()
        with DB_ENGINE.begin() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM projects WHERE owner_user_id = :uid"
            ), {"uid": uid}).scalar()
            if count >= 6:
                return jsonify({"error": "Project limit reached (6 max). Delete an existing project first."}), 403
            result = conn.execute(text("""
                INSERT INTO projects (owner_user_id, title, type)
                VALUES (:uid, :title, :type) RETURNING id
            """), {
                "uid": uid,
                "title": project_title,
                "type": project_type or "Project"
            })
            new_pid = str(result.scalar())
            session["active_project_id"] = new_pid
            set_status("UPLOADED", project_id=new_pid)
    else:
        if not project_title and not existing_project_id:
            session.pop("active_project_id", None)

    clear_latest_targets()

    save_path = UPLOAD_DIR / Path(file.filename).name
    file.save(save_path)

    started_at = time.time()
    log_usage("generate_start", filename=file.filename)

    logline = (request.form.get("logline") or "").strip()
    synopsis = (request.form.get("synopsis") or "").strip()
    deck_mode = (request.form.get("deck_mode") or "full").strip().lower()
    if deck_mode not in {"producer", "full"}:
        deck_mode = "full"
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
        "deck_mode": deck_mode,
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


    # Capture project_id before pipeline overwrites STATUS_FILE with its own JSON
    saved_pid = session.get("active_project_id") or get_status_project_id()

    try:
        set_status("ANALYZING", project_id=saved_pid)
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

        set_status("BUILDING", project_id=saved_pid)
    except subprocess.CalledProcessError:
        set_status("ERROR")
        try:
            tail = log_path.read_text(encoding="utf-8").strip().split("\n")
            last_lines = "\n".join(tail[-40:])
        except Exception:
            last_lines = "(log unavailable)"
        return f"Engine failed\n\n{last_lines}", 500

    fresh_pptx = newest_generated_file(".pptx")
    fresh_pdf = newest_generated_file(".pdf")

    if not fresh_pptx or not fresh_pptx.exists():
        set_status("ERROR")
        return "No deck generated", 500

    publish_latest_outputs(fresh_pptx, fresh_pdf)

    # Also publish producer's deck if it was built
    producer_labeled = OUTPUT_DIR / "latest_producer.pptx"
    if not producer_labeled.exists():
        # Fallback: look for freshest pitch_deck_producer_v*.pptx
        producer_files = sorted(OUTPUT_DIR.glob("pitch_deck_producer_v*.pptx"), key=lambda p: p.stat().st_mtime)
        if producer_files:
            shutil.copy2(str(producer_files[-1]), str(producer_labeled))

    if not LATEST_PPTX.exists():
        set_status("ERROR")
        return "Latest deck publish failed", 500

    set_status("COMPLETE", project_id=saved_pid)
    elapsed = int(time.time() - started_at)
    log_usage("generate_complete", success=True, filename=file.filename, elapsed=f"{elapsed}s")
    log_activity_event("deck_run", route="/upload", user_email=session.get("user_email"))

    # Save deck to user-scoped project directory
    active_pid = saved_pid or get_status_project_id() or session.get("active_project_id")
    if active_pid and DB_ENGINE:
        try:
            uid = session.get("user_id", "anon")
            proj_out = BASE_DIR / "user_data" / str(uid) / str(active_pid)
            proj_out.mkdir(parents=True, exist_ok=True)
            if fresh_pptx and fresh_pptx.exists():
                shutil.copy2(fresh_pptx, proj_out / "deck.pptx")
            if fresh_pdf and fresh_pdf.exists():
                shutil.copy2(fresh_pdf, proj_out / "deck.pdf")
            if LATEST_DECK_MANIFEST_JSON.exists():
                shutil.copy2(LATEST_DECK_MANIFEST_JSON, proj_out / "deck_manifest.json")
            with DB_ENGINE.begin() as conn:
                conn.execute(text("""
                    UPDATE projects SET output_dir = :output_dir WHERE id = :id
                """), {"output_dir": f"user_data/{uid}/{active_pid}", "id": int(active_pid)})
        except Exception as e:
            print(f"⚠️ Failed to save project output: {e}", flush=True)

    return ("OK", 200)


# ===== DEMO ROUTES START =============================
@app.route("/demo", methods=["POST"])
def demo():
    if not DEMO_DECK.exists():
        return "Demo deck not found", 500
    return send_file(DEMO_DECK, as_attachment=False)


@app.route("/download/latest.pptx")
def download_latest_pptx():
    uid = session.get("user_id")
    pid = session.get("active_project_id") or get_status_project_id()
    if uid and pid:
        proj_path = BASE_DIR / "user_data" / str(uid) / str(pid) / "deck.pptx"
        if proj_path.exists():
            return send_file(proj_path, as_attachment=True)
    if not LATEST_PPTX.exists():
        abort(404)
    return send_file(LATEST_PPTX, as_attachment=True)


@app.route("/download/latest_producer.pptx")
def download_latest_producer_pptx():
    path = OUTPUT_DIR / "latest_producer.pptx"
    if not path.exists():
        abort(404)
    return send_file(path, as_attachment=True)


@app.route("/download/latest.pdf")
def download_latest_pdf():
    uid = session.get("user_id")
    pid = session.get("active_project_id") or get_status_project_id()
    if uid and pid:
        proj_path = BASE_DIR / "user_data" / str(uid) / str(pid) / "deck.pdf"
        if proj_path.exists():
            return send_file(proj_path, as_attachment=True)
    if not LATEST_PDF.exists():
        abort(404)
    return send_file(LATEST_PDF, as_attachment=True)


@app.route("/upload-slide-image", methods=["POST"])
@require_login
def upload_slide_image():
    file = request.files.get("image")
    if not file or not file.filename:
        return jsonify({"ok": False, "error": "No file"}), 400
    ext = Path(file.filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        return jsonify({"ok": False, "error": "Image files only"}), 400
    uid = session.get("user_id", "anon")
    dest = BASE_DIR / "user_data" / str(uid) / "slide_images"
    dest.mkdir(parents=True, exist_ok=True)
    import uuid as _uuid
    safe_name = f"{_uuid.uuid4().hex}{ext}"
    save_path = dest / safe_name
    file.save(save_path)
    return jsonify({"ok": True, "path": str(save_path), "url": f"/slide-image/{uid}/{safe_name}"})


@app.route("/slide-image/<uid>/<filename>")
def serve_slide_image(uid, filename):
    path = BASE_DIR / "user_data" / str(uid) / "slide_images" / filename
    if not path.exists():
        abort(404)
    return send_file(path)


# ===== ANALYZE ROUTES START ==========================
@app.route("/analyze-script-pass", methods=["POST"])
def analyze_script_pass():
    set_status("ANALYZING")
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


def fetch_tmdb_comps(genre_str: str, n: int = 4) -> list:
    if not TMDB_API_KEY or not genre_str:
        return []
    cache_key = genre_str.lower().strip()
    cached = _TMDB_CACHE.get(cache_key)
    if cached and (time.time() - cached["ts"] < 3600):
        return cached["data"]
    GENRE_MAP = {
        "crime": 80, "drama": 18, "thriller": 53, "horror": 27,
        "comedy": 35, "action": 28, "sci-fi": 878, "science fiction": 878,
        "documentary": 99, "animation": 16, "animated": 16, "romance": 10749,
        "adventure": 12, "mystery": 9648, "war": 10752, "western": 37,
        "fantasy": 14, "family": 10751, "biography": 36, "history": 36,
        "sport": 18, "sports": 18,
    }
    genre_lower = genre_str.lower()
    genre_ids = list({str(gid) for kw, gid in GENRE_MAP.items() if kw in genre_lower})
    try:
        import urllib.request, urllib.parse
        params = {
            "api_key": TMDB_API_KEY,
            "sort_by": "revenue.desc",
            "vote_average.gte": "6.5",
            "vote_count.gte": "500",
            "with_original_language": "en",
        }
        if genre_ids:
            params["with_genres"] = ",".join(genre_ids[:2])
        url = "https://api.themoviedb.org/3/discover/movie?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=6) as resp:
            data = json.loads(resp.read().decode())
        results = data.get("results", [])[:n]
        comps = [{
            "title": r.get("title", ""),
            "year": (r.get("release_date") or "")[:4],
            "overview": (r.get("overview") or "")[:180],
            "poster_url": f"https://image.tmdb.org/t/p/w200{r['poster_path']}" if r.get("poster_path") else "",
            "rating": round(r.get("vote_average", 0), 1),
        } for r in results]
        _TMDB_CACHE[cache_key] = {"data": comps, "ts": time.time()}
        return comps
    except Exception as e:
        print(f"⚠️ TMDB fetch failed: {e}", flush=True)
        return []


@app.route("/analysis-report")
def analysis_report_page():
    if not LATEST_ANALYSIS_JSON.exists():
        return redirect("/")
    try:
        report = json.loads(LATEST_ANALYSIS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return redirect("/")
    comps = fetch_tmdb_comps(report.get("genre", "drama"))
    return render_template("analysis_report.html", report=report, comps=comps)


@app.route("/actor-prep-report")
def actor_prep_report_page():
    if not LATEST_ACTOR_PREP_JSON.exists():
        return send_file(LATEST_ACTOR_PREP_PDF, as_attachment=False) if LATEST_ACTOR_PREP_PDF.exists() else redirect("/")
    try:
        report = json.loads(LATEST_ACTOR_PREP_JSON.read_text(encoding="utf-8"))
    except Exception:
        return redirect("/")
    return render_template("actor_prep_report.html", report=report)


@app.route("/actor-booked-report")
def actor_booked_report_page():
    if not LATEST_ACTOR_BOOKED_JSON.exists():
        return send_file(LATEST_ACTOR_BOOKED_PDF, as_attachment=False) if LATEST_ACTOR_BOOKED_PDF.exists() else redirect("/")
    try:
        report = json.loads(LATEST_ACTOR_BOOKED_JSON.read_text(encoding="utf-8"))
    except Exception:
        return redirect("/")
    return render_template("actor_booked_report.html", report=report)


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

    cleaned = str(raw_path).replace("\\", "/").strip()
    candidates = []

    rel = normalize_project_relative_path(cleaned)
    if rel:
        candidates.append((BASE_DIR / rel).resolve())

    try:
        p = Path(cleaned)
        if p.is_absolute():
            candidates.append(p.resolve())
    except Exception:
        pass

    if cleaned.startswith("opt/render/project/src/"):
        candidates.append(Path("/" + cleaned).resolve())
    elif cleaned.startswith("/opt/render/project/src/"):
        candidates.append(Path(cleaned).resolve())

    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if ensure_relative_to_base(candidate) and candidate.exists() and candidate.is_file():
            return send_file(candidate, as_attachment=False, conditional=True)

    abort(404)

@app.route("/generate-slide-options", methods=["POST"])
def generate_slide_options():
    try:
        if not FAL_API_KEY:
            return jsonify({"error": "FAL_API_KEY is not configured."}), 500
        data = request.get_json(silent=True) or {}
        slide_title = safe_text(data.get("slide_title"), "Slide")
        slide_body = safe_text(data.get("slide_body"), "")
        user_prompt = safe_text(data.get("user_prompt"), "")
        slide_number = int(data.get("slide_number") or 1)

        slide_plan_file = find_latest_slide_plan_file()
        if not slide_plan_file or not slide_plan_file.exists():
            return jsonify({"error": "No slide plan found."}), 404

        options = generate_slide_option_images(
            slide_plan_file=slide_plan_file,
            slide_title=slide_title,
            slide_body=slide_body,
            user_prompt=user_prompt,
            slide_number=slide_number,
        )
        if not options:
            return jsonify({"error": "Could not generate options. Try again."}), 500
        return jsonify({"options": options})
    except Exception as e:
        return jsonify({"error": f"Could not load new images: {e}"}), 500

@app.route("/regenerate-slide-image", methods=["POST"])
def regenerate_slide_image():
    try:
        if not FAL_API_KEY:
            return jsonify({"error": "FAL_API_KEY is not configured."}), 500
        data = request.get_json(silent=True) or {}
        slide_title = safe_text(data.get("slide_title"), "Slide")
        slide_body = safe_text(data.get("slide_body"), "")
        user_prompt = safe_text(data.get("user_prompt"), "")
        slide_number = int(data.get("slide_number") or 1)

        slide_plan_file = find_latest_slide_plan_file()
        if not slide_plan_file or not slide_plan_file.exists():
            return jsonify({"error": "No slide plan found."}), 404

        options = generate_slide_option_images(
            slide_plan_file=slide_plan_file,
            slide_title=slide_title,
            slide_body=slide_body,
            user_prompt=user_prompt,
            slide_number=slide_number,
        )
        if not options:
            return jsonify({"error": "Generation failed. Try again."}), 500
        best = options[0]
        return jsonify({
            "image_url": best.get("image_url", ""),
            "image_path": best.get("image_path", ""),
            "image_name": best.get("image_name", ""),
            "image_source": best.get("image_source", "fal_generated"),
        })
    except Exception as e:
        return jsonify({"error": f"Could not regenerate slide image: {e}"}), 500

@app.route("/refine-deck", methods=["POST"])
def refine_deck():
    data = request.get_json(silent=True) or {}
    slides = data.get("slides", [])
    deck_type = (data.get("deck_type") or "full").strip().lower()

    if deck_type == "producer":
        manifest_path = OUTPUT_DIR / "latest_deck_manifest_producer.json"
        label = "producer"
    else:
        manifest_path = LATEST_DECK_MANIFEST_JSON
        label = ""

    result = rebuild_refined_deck(slides, latest_manifest_path=manifest_path, label=label)

    if "error" in result:
        return jsonify(result), 400 if result["error"] == "No slide data provided." else 500

    _LATEST_SLIDE_PAYLOAD_CACHE["key"] = None
    _LATEST_SLIDE_PAYLOAD_CACHE["payload"] = None

    return jsonify({
        "message": "Your refined deck has been rebuilt successfully.",
        "deck": result["deck"],
    })

# ===== REGEN DECK ROUTE START =========================
@app.route("/regen-deck", methods=["POST"])
def regen_deck():
    data = request.get_json(silent=True) or {}
    direction = (data.get("prompt") or "").strip()
    if not direction:
        return jsonify({"error": "No direction provided."}), 400

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return jsonify({"error": "AI not configured."}), 500

    slide_plan_file = find_latest_slide_plan_file()
    if not slide_plan_file:
        return jsonify({"error": "No slide plan found. Generate a deck first."}), 404

    try:
        slide_plan = json.loads(Path(slide_plan_file).read_text(encoding="utf-8"))
    except Exception as e:
        return jsonify({"error": f"Could not read slide plan: {e}"}), 500

    try:
        import anthropic as _anthropic
        client = _anthropic.Anthropic(api_key=api_key)
        prompt_text = (
            "You are updating a pitch deck's slide content based on a new creative direction.\n\n"
            f"Current slide plan (JSON):\n{json.dumps(slide_plan, indent=2)}\n\n"
            f"New creative direction: \"{direction}\"\n\n"
            "Rewrite the \"title\" and \"body\" fields for every slide to reflect this direction. "
            "Keep the same number of slides and preserve all other fields exactly "
            "(stage, layout, image_path, image_name, image_url, image_source, image_options, "
            "selected_option_id, slide_count). Return ONLY valid JSON — no extra text, no markdown fences."
        )
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt_text}]
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        new_plan = json.loads(raw)
    except Exception as e:
        return jsonify({"error": f"AI rewrite failed: {e}"}), 500

    full_slides = new_plan.get("slides", [])
    result = rebuild_refined_deck(full_slides, label="")
    if "error" in result:
        return jsonify(result), 500

    # Update producer deck by matching stages from the rewritten full plan
    producer_plan_file = OUTPUT_DIR / "slide_plan_producer.json"
    if producer_plan_file.exists():
        try:
            producer_plan = json.loads(producer_plan_file.read_text(encoding="utf-8"))
            stage_map = {}
            for s in full_slides:
                stage = s.get("stage", "")
                if stage not in stage_map:
                    stage_map[stage] = s
            for ps in producer_plan.get("slides", []):
                matched = stage_map.get(ps.get("stage", ""))
                if matched:
                    ps["title"] = matched.get("title", ps["title"])
                    ps["body"] = matched.get("body", ps["body"])
            rebuild_refined_deck(producer_plan["slides"], label="producer")
        except Exception:
            pass

    _LATEST_SLIDE_PAYLOAD_CACHE["key"] = None
    _LATEST_SLIDE_PAYLOAD_CACHE["payload"] = None
    return jsonify({"ok": True})

# ===== REGEN DECK ROUTE END ===========================

# ===== ACTOR PREP ROUTES START =======================
@app.route("/actor-prep-pass", methods=["POST"])
def actor_prep_pass():
    character_name = (request.form.get("character_name") or "").strip()
    movie_title = (request.form.get("movie_title") or "").strip()
    pasted_text = (request.form.get("script_text") or "").strip()
    file = request.files.get("script")

    if not character_name:
        return jsonify({"error": "Please enter the role you are preparing."}), 400

    script_text = ""
    source_mode = "paste"

    if file and file.filename:
        source_mode = "upload"
        filename = file.filename.lower()

        if filename.endswith(".txt"):
            script_text = file.read().decode("utf-8", errors="ignore")
        elif filename.endswith(".pdf"):
            try:
                reader = PdfReader(file)
                script_text = "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
            except Exception:
                script_text = ""

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

    log_usage("actor_prep_start", role=character_name, mode=source_mode)

    brain_data = load_latest_brain_output() or {}
    if movie_title:
        brain_data.setdefault("title", movie_title)
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
    movie_title = (request.form.get("movie_title") or "").strip()
    pasted_text = (request.form.get("script_text") or "").strip()
    file = request.files.get("script")

    if not character_name:
        return jsonify({"error": "Please enter the role you are preparing."}), 400

    script_text = ""
    source_mode = "paste"

    if file and file.filename:
        source_mode = "upload"
        filename = file.filename.lower()

        if filename.endswith(".txt"):
            script_text = file.read().decode("utf-8", errors="ignore")
        elif filename.endswith(".pdf"):
            try:
                reader = PdfReader(file)
                script_text = "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
            except Exception:
                script_text = ""

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

    log_usage("actor_booked_start", role=character_name, mode=source_mode)

    brain_data = load_latest_brain_output() or {}
    if movie_title:
        brain_data.setdefault("title", movie_title)
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
        "summary_note": f"Your booked role analysis for {character_name} is ready.",
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

def ensure_projects_table():
    if not DB_ENGINE:
        return

    with DB_ENGINE.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                owner_user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                type TEXT,
                status TEXT DEFAULT 'Active',
                storage_used_mb INTEGER DEFAULT 0,
                output_dir TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        try:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS output_dir TEXT DEFAULT NULL"
            ))
        except Exception:
            pass

def ensure_collab_tables():
    if not DB_ENGINE:
        return
    with DB_ENGINE.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS project_invites (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                invite_code TEXT UNIQUE NOT NULL,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS project_collaborators (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                user_name TEXT,
                joined_via TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(project_id, user_id)
            )
        """))


def _generate_invite_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(6))


@app.route("/project/<project_id>/create-invite", methods=["POST"])
@require_login
def create_project_invite(project_id):
    ensure_projects_table()
    ensure_collab_tables()
    with DB_ENGINE.connect() as conn:
        proj = conn.execute(text(
            "SELECT id FROM projects WHERE id = :id AND owner_user_id = :uid"
        ), {"id": project_id, "uid": session.get("user_id")}).mappings().first()
    if not proj:
        return jsonify({"error": "Project not found"}), 404

    # Return existing invite if one already exists for this project
    with DB_ENGINE.connect() as conn:
        existing = conn.execute(text(
            "SELECT token, invite_code FROM project_invites WHERE project_id = :pid AND created_by = :uid"
        ), {"pid": project_id, "uid": session.get("user_id")}).mappings().first()

    if existing:
        token, code = existing["token"], existing["invite_code"]
    else:
        token = secrets.token_urlsafe(16)
        code = _generate_invite_code()
        with DB_ENGINE.begin() as conn:
            conn.execute(text("""
                INSERT INTO project_invites (project_id, token, invite_code, created_by)
                VALUES (:pid, :token, :code, :uid)
            """), {"pid": project_id, "token": token, "code": code, "uid": session.get("user_id")})

    base = request.host_url.rstrip("/")
    return jsonify({"token": token, "code": code, "link": f"{base}/join/{token}"})


@app.route("/join/<token>", methods=["GET", "POST"])
def join_project(token):
    ensure_collab_tables()
    with DB_ENGINE.connect() as conn:
        invite = conn.execute(text("""
            SELECT pi.project_id, p.title, p.type
            FROM project_invites pi
            JOIN projects p ON p.id = pi.project_id
            WHERE pi.token = :token
        """), {"token": token}).mappings().first()
    if not invite:
        return render_template("join.html", error="This invite link is invalid or has expired.", project=None)

    # Already logged in — auto-join without showing the form
    if session.get("user_id"):
        user_id = session["user_id"]
        name = session.get("user_name") or "Collaborator"
        with DB_ENGINE.begin() as conn:
            conn.execute(text("""
                INSERT INTO project_collaborators (project_id, user_id, user_name, joined_via)
                VALUES (:pid, :uid, :name, :token)
                ON CONFLICT (project_id, user_id) DO NOTHING
            """), {"pid": invite["project_id"], "uid": user_id, "name": name, "token": token})
        return redirect(f"/project/{invite['project_id']}")

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            return render_template("join.html", project=invite, token=token, error="Please enter your name.")
        user_id = f"collab_{secrets.token_hex(8)}"
        session["user_id"] = user_id
        session["user_name"] = name
        with DB_ENGINE.begin() as conn:
            conn.execute(text("""
                INSERT INTO project_collaborators (project_id, user_id, user_name, joined_via)
                VALUES (:pid, :uid, :name, :token)
                ON CONFLICT (project_id, user_id) DO NOTHING
            """), {"pid": invite["project_id"], "uid": user_id, "name": name, "token": token})
        return redirect(f"/project/{invite['project_id']}")

    return render_template("join.html", project=invite, token=token, error=None)


@app.route("/use-invite-code", methods=["POST"])
def use_invite_code():
    code = (request.form.get("code") or "").strip().upper()
    if not code:
        return redirect("/studio")
    ensure_collab_tables()
    with DB_ENGINE.connect() as conn:
        invite = conn.execute(text(
            "SELECT token FROM project_invites WHERE invite_code = :code"
        ), {"code": code}).mappings().first()
    if not invite:
        return redirect("/studio?code_error=1")
    return redirect(f"/join/{invite['token']}")


@app.route("/project/<project_id>/deck.<ext>")
@require_login
def project_deck_file(project_id, ext):
    if ext not in ("pdf", "pptx"):
        abort(404)
    ensure_projects_table()
    with DB_ENGINE.connect() as conn:
        row = conn.execute(text("""
            SELECT output_dir FROM projects WHERE id = :id AND owner_user_id = :uid
        """), {"id": project_id, "uid": session.get("user_id")}).mappings().first()
    if not row or not row["output_dir"]:
        abort(404)
    file_path = BASE_DIR / row["output_dir"] / f"deck.{ext}"
    if not file_path.exists():
        abort(404)
    return send_file(file_path, as_attachment=(ext == "pptx"))

@app.route("/db-check")
def db_check_route():
    try:
        ok = db_check()
        return jsonify({"ok": ok, "database_configured": bool(DATABASE_URL)})
    except Exception as e:
        return jsonify({"ok": False, "database_configured": bool(DATABASE_URL), "error": str(e)}), 500


@app.route("/db-init")
def db_init_route():
    try:
        db_init()
        return jsonify({"ok": True, "message": "database initialized"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ===== APP RUN START =================================
if __name__ == "__main__":
    try:
        if DB_ENGINE:
            db_init()
            print("✅ Database ready", flush=True)
        else:
            print("⚠️ DATABASE_URL not configured; database features disabled", flush=True)
    except Exception as e:
        print(f"⚠️ Database init skipped: {e}", flush=True)
    port = int(os.environ.get("PORT", 7000))
    app.run(host="0.0.0.0", port=port)


# ===== APP RUN END ===================================
