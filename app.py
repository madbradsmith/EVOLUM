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
from dai_tools import build_actor_prep_pdf, build_actor_booked_pdf


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
            SELECT id, email, name, password_hash, created_at
            FROM beta_users
            WHERE lower(email) = :email
            LIMIT 1
        """), {"email": email}).mappings().first()
    return dict(row) if row else None

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
LATEST_ACTOR_PREP_PDF = OUTPUT_DIR / "latest_actor_prep_report.pdf"
LATEST_ACTOR_BOOKED_PDF = OUTPUT_DIR / "latest_actor_booked_report.pdf"
LATEST_DECK_MANIFEST_JSON = OUTPUT_DIR / "latest_deck_manifest.json"

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
    return session.get("beta_access") is True or bool(session.get("user_email"))


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


def normalize_project_relative_path(raw_path: str) -> str:
    cleaned = str(raw_path or "").strip().replace("\\", "/")
    if not cleaned:
        return ""
    prefixes = [
        str(BASE_DIR).replace("\\", "/").rstrip("/") + "/",
        "/opt/render/project/src/",
        "opt/render/project/src/",
    ]
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    return cleaned.lstrip("/")

def normalize_project_path_string(raw_path: str) -> str:
    return normalize_project_relative_path(raw_path)

def project_file_url_for_path(raw_path: str) -> str:
    rel = normalize_project_relative_path(raw_path)
    if not rel:
        return ""
    return "/project-file?path=" + quote(rel)

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

def normalize_manifest_image_options(options):
    normalized = []
    if not isinstance(options, list):
        return normalized
    for item in options:
        if not isinstance(item, dict):
            continue
        entry = dict(item)
        entry["image_path"] = normalize_project_relative_path(entry.get("image_path", "") or "")
        if not entry.get("image_url"):
            entry["image_url"] = project_file_url_for_path(entry.get("image_path", "") or "")
        normalized.append(entry)
    return normalized


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


def build_simple_analysis_pdf(report_output: dict, out_path):
    """Build the premium Evolum Script Analysis PDF.

    This version keeps the report in the current dark/gold product family,
    fixes text-in-number-card issues, and upgrades the generic key moments
    by using API enrichment when available with strong local fallbacks.
    """
    from pathlib import Path
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib import colors
    import json
    import os
    import re
    import textwrap
    import urllib.request

    pdf = canvas.Canvas(str(out_path), pagesize=letter)
    width, height = letter

    BG = colors.HexColor("#070707")
    PANEL = colors.HexColor("#111111")
    PANEL_2 = colors.HexColor("#171717")
    GOLD = colors.HexColor("#D4AF37")
    MUTED_GOLD = colors.HexColor("#A8842D")
    WHITE = colors.HexColor("#F4F1E8")
    MUTED = colors.HexColor("#BDB7A8")
    LINE = colors.HexColor("#3A2E16")

    def val(key, default=""):
        value = report_output.get(key, default)
        if value is None:
            return default
        return value

    def clean_text(value):
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return ", ".join(clean_text(v) for v in value if v)
        if isinstance(value, dict):
            return "; ".join(f"{k}: {clean_text(v)}" for k, v in value.items() if v)
        value = str(value)
        value = value.replace("\u25a0", " ").replace("■", " ")
        value = re.sub(r"\s+", " ", value).strip()
        return value

    def as_list(value, limit=None):
        if value is None or value == "":
            items = []
        elif isinstance(value, list):
            items = value
        elif isinstance(value, tuple):
            items = list(value)
        else:
            items = [v.strip() for v in re.split(r"[\n;]+", str(value)) if v.strip()]
        items = [clean_text(i) for i in items if clean_text(i)]
        return items[:limit] if limit else items

    def wrap_lines(text, max_chars=78, max_lines=None):
        text = clean_text(text)
        if not text:
            return []
        lines = []
        for para in re.split(r"\n+", text):
            para = clean_text(para)
            if not para:
                continue
            lines.extend(textwrap.wrap(para, width=max_chars, break_long_words=False, break_on_hyphens=False))
        return lines[:max_lines] if max_lines else lines

    def draw_bg():
        pdf.setFillColor(BG)
        pdf.rect(0, 0, width, height, fill=1, stroke=0)

    def footer(page_num):
        pdf.setStrokeColor(LINE)
        pdf.setLineWidth(0.7)
        pdf.line(36, 34, width - 36, 34)
        pdf.setFont("Helvetica-Bold", 7.3)
        pdf.setFillColor(GOLD)
        pdf.drawCentredString(width / 2, 18, f"EVOLUM AI SCRIPT INTELLIGENCE THAT MOVES STORIES FORWARD   PAGE {page_num}")

    def draw_heading(title, y, eyebrow=None):
        if eyebrow:
            pdf.setFont("Helvetica-Bold", 7.5)
            pdf.setFillColor(MUTED_GOLD)
            pdf.drawString(40, y + 22, eyebrow.upper())
        pdf.setFont("Helvetica-Bold", 21)
        pdf.setFillColor(WHITE)
        pdf.drawString(40, y, title.upper())
        pdf.setStrokeColor(GOLD)
        pdf.setLineWidth(1)
        pdf.line(40, y - 9, 155, y - 9)
        return y - 34

    def draw_label_value(x, y, label, value, w=160, max_chars=28):
        pdf.setFont("Helvetica-Bold", 7.2)
        pdf.setFillColor(GOLD)
        pdf.drawString(x, y, clean_text(label).upper())
        pdf.setFont("Helvetica", 9.2)
        pdf.setFillColor(WHITE)
        yy = y - 14
        for line in wrap_lines(value, max_chars=max_chars, max_lines=4):
            pdf.drawString(x, yy, line)
            yy -= 11
        return yy

    def draw_text_block(x, y, title, body, w=520, chars=88, font_size=9.4, leading=12, max_lines=None):
        pdf.setFont("Helvetica-Bold", 10.5)
        pdf.setFillColor(GOLD)
        pdf.drawString(x, y, clean_text(title).upper())
        y -= 16
        pdf.setFont("Helvetica", font_size)
        pdf.setFillColor(WHITE)
        for line in wrap_lines(body, chars, max_lines=max_lines):
            if y < 52:
                return y
            pdf.drawString(x, y, line)
            y -= leading
        return y - 8

    def draw_panel(x, y, w, h, title=None, fill=PANEL):
        pdf.setFillColor(fill)
        pdf.roundRect(x, y - h, w, h, 8, fill=1, stroke=0)
        pdf.setStrokeColor(LINE)
        pdf.setLineWidth(0.6)
        pdf.roundRect(x, y - h, w, h, 8, fill=0, stroke=1)
        if title:
            pdf.setFillColor(GOLD)
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawString(x + 12, y - 18, clean_text(title).upper())
        return y - h

    def draw_metric_card(x, y, w, h, label, value, subtitle=""):
        draw_panel(x, y, w, h, fill=PANEL_2)
        pdf.setFont("Helvetica-Bold", 7)
        pdf.setFillColor(GOLD)
        pdf.drawString(x + 10, y - 15, clean_text(label).upper())
        pdf.setFont("Helvetica-Bold", 23)
        pdf.setFillColor(WHITE)
        pdf.drawString(x + 10, y - 43, clean_text(value)[:5])
        if subtitle:
            pdf.setFont("Helvetica", 7.3)
            pdf.setFillColor(MUTED)
            yy = y - 58
            for line in wrap_lines(subtitle, 19, max_lines=2):
                pdf.drawString(x + 10, yy, line)
                yy -= 9

    def draw_list(x, y, title, items, chars=78, bullet=True, max_items=None):
        items = as_list(items, max_items)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.setFillColor(GOLD)
        pdf.drawString(x, y, clean_text(title).upper())
        y -= 17
        pdf.setFont("Helvetica", 9.2)
        pdf.setFillColor(WHITE)
        for item in items:
            prefix = "• " if bullet else ""
            lines = wrap_lines(item, chars)
            for i, line in enumerate(lines):
                if y < 52:
                    return y
                pdf.drawString(x, y, (prefix if i == 0 else "  ") + line)
                y -= 12
            y -= 4
        return y

    def find_report_image(prefer_slide=None):
        candidates = []
        # Prefer generated images that already exist from the deck run.
        if prefer_slide:
            candidates.extend(Path(".").glob(f"generated_images/**/*{int(prefer_slide):02d}_*.jpg"))
            candidates.extend(Path(".").glob(f"generated_images/**/*{int(prefer_slide):02d}_*.png"))
        candidates.extend(Path(".").glob("generated_images/**/*.jpg"))
        candidates.extend(Path(".").glob("generated_images/**/*.png"))
        candidates.extend(Path(".").glob("static/**/*.jpg"))
        candidates.extend(Path(".").glob("static/**/*.png"))
        for p in candidates:
            name = p.name.lower()
            if p.exists() and p.is_file() and not name.startswith("logo"):
                return str(p)
        return None

    def draw_image_band(path, x, y, w, h, alpha_overlay=True):
        if not path:
            return False
        try:
            pdf.drawImage(ImageReader(path), x, y - h, width=w, height=h, preserveAspectRatio=True, anchor="c", mask="auto")
            if alpha_overlay:
                pdf.setFillColor(colors.Color(0, 0, 0, alpha=0.35))
                pdf.rect(x, y - h, w, h, fill=1, stroke=0)
            return True
        except Exception:
            return False

    def generate_specific_key_moments():
        existing = as_list(report_output.get("key_moments"), 4)
        generic = {"opening power move", "first pressure turn", "status shift or reveal", "control reset"}
        if existing and not all(e.lower() in generic for e in existing):
            return existing[:4]

        title = clean_text(val("title", "Untitled"))
        protagonist = clean_text(val("protagonist", val("lead", "the protagonist")))
        logline = clean_text(val("logline", ""))
        synopsis = clean_text(val("synopsis", ""))
        conflict = clean_text(val("core_conflict", ""))
        reversal = clean_text(val("reversal", ""))
        theme = clean_text(val("theme", ""))

        # Optional API enrichment. Safe fallback below if no key or if request fails.
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_APIKEY")
        if api_key:
            prompt = (
                "Generate exactly 4 script-specific key story moments for a screenplay analysis report. "
                "Do not use generic labels. Each item should be 8-16 words, concrete, and tied to the story. "
                "Return only a JSON array of strings.\n\n"
                f"Title: {title}\nProtagonist: {protagonist}\nLogline: {logline}\n"
                f"Synopsis: {synopsis[:1400]}\nConflict: {conflict}\nReversal: {reversal}\nTheme: {theme}"
            )
            try:
                payload = json.dumps({
                    "model": os.environ.get("OPENAI_TEXT_MODEL", "gpt-4o-mini"),
                    "messages": [
                        {"role": "system", "content": "You write concise screenplay development report copy."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.35,
                    "max_tokens": 220,
                }).encode("utf-8")
                req = urllib.request.Request(
                    "https://api.openai.com/v1/chat/completions",
                    data=payload,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"].strip()
                parsed = json.loads(content)
                items = [clean_text(x) for x in parsed if clean_text(x)]
                if len(items) >= 4:
                    return items[:4]
            except Exception as e:
                print(f"⚠️ Key moment API enrichment skipped: {e}")

        # Local story-specific fallback generated from available brain fields.
        parts = []
        if logline:
            parts.append(logline)
        for sent in re.split(r"(?<=[.!?])\s+", synopsis):
            sent = clean_text(sent)
            if sent and len(sent) > 35:
                parts.append(sent)
        if conflict:
            parts.append(conflict)
        if reversal:
            parts.append(reversal)
        if theme:
            parts.append(theme)

        moments = []
        for p in parts:
            p = re.sub(r"^(When|As|After|Before)\s+", "", p, flags=re.I)
            if protagonist and protagonist.lower() not in p.lower() and len(moments) < 2:
                p = f"{protagonist} faces " + p[0].lower() + p[1:]
            p = p.strip(" .")
            if p and p not in moments:
                moments.append(p[:115])
            if len(moments) == 4:
                break
        while len(moments) < 4:
            fallback = [
                f"{protagonist} is pulled into the central pressure of the story",
                f"{protagonist} misreads or confronts the force driving the conflict",
                "The hidden truth shifts the meaning of the central situation",
                f"{protagonist} must choose integrity, survival, or consequence",
            ][len(moments)]
            moments.append(fallback)
        return moments[:4]

    title = clean_text(val("title", "Untitled"))
    lead = clean_text(val("protagonist", val("lead", "Unknown")))
    world = clean_text(val("world", "Feature"))
    genre = clean_text(val("genre", world))
    tone = clean_text(val("tone", ""))
    tagline = clean_text(val("tagline", val("logline", "")))
    logline = clean_text(val("logline", ""))
    synopsis = clean_text(val("synopsis", ""))
    theme = clean_text(val("theme", ""))
    conflict = clean_text(val("core_conflict", ""))
    engine = clean_text(val("story_engine", ""))
    reversal = clean_text(val("reversal", ""))
    setting = clean_text(val("setting", world))
    commercial = clean_text(val("commercial_positioning", ""))
    packaging = clean_text(val("packaging_potential", ""))
    character_leverage = clean_text(val("character_leverage", ""))
    audience = as_list(val("audience_profile", []), 5)
    comparables = as_list(val("tone_comparables", val("comparable_films", [])), 5)
    if comparables and isinstance(report_output.get("comparable_films"), list):
        comparables = [clean_text(c.get("title", c)) if isinstance(c, dict) else clean_text(c) for c in report_output.get("comparable_films", [])[:5]]
    strength = val("strength_index", {}) or {}
    market = val("market_projections", {}) or {}
    moments = generate_specific_key_moments()

    # PAGE 1 — Cover / snapshot
    draw_bg()
    hero = find_report_image(1)
    if hero:
        draw_image_band(hero, 305, height - 42, 265, 188, alpha_overlay=True)
    pdf.setFont("Helvetica-Bold", 28)
    pdf.setFillColor(WHITE)
    pdf.drawString(40, height - 64, title.upper()[:28])
    pdf.setFont("Helvetica-Bold", 14)
    pdf.setFillColor(GOLD)
    pdf.drawString(40, height - 91, "EVOLUM Full Script Analysis Report")
    y = height - 123
    intro = f"{title} puts {lead} at the center of {world}, with a tone that feels {tone}."
    pdf.setFont("Helvetica", 10.6)
    pdf.setFillColor(WHITE)
    for line in wrap_lines(intro, 54, 4):
        pdf.drawString(40, y, line)
        y -= 13

    y -= 12
    # Open text fields, not fake numeric cards.
    x1, x2 = 40, 210
    yrow = y
    draw_label_value(x1, yrow, "Lead", lead, max_chars=20)
    draw_label_value(x2, yrow, "Genre / World", world, max_chars=34)
    yrow -= 67
    draw_label_value(x1, yrow, "Tone", tone, max_chars=28)
    draw_label_value(x2, yrow, "Tagline", tagline, max_chars=42)

    y = 335
    draw_text_block(40, y, "Story Snapshot", "", chars=70)
    y -= 22
    snapshot_items = [
        ("Theme", theme),
        ("Core Conflict", conflict),
        ("Story Engine", engine),
        ("Reversal", reversal),
    ]
    for label, body in snapshot_items:
        pdf.setFont("Helvetica-Bold", 7.5)
        pdf.setFillColor(GOLD)
        pdf.drawString(40, y, label.upper())
        pdf.setFont("Helvetica", 8.9)
        pdf.setFillColor(WHITE)
        yy = y
        for line in wrap_lines(body, 70, 3):
            pdf.drawString(150, yy, line)
            yy -= 10.5
        y = min(y - 39, yy - 5)
    footer(1)
    pdf.showPage()

    # PAGE 2 — Executive / commercial value
    draw_bg()
    y = draw_heading("Executive Summary", height - 54, "Producer Read")
    y = draw_text_block(40, y, "Summary", val("executive_summary", synopsis), chars=92, max_lines=7)

    metric_y = y - 8
    draw_metric_card(40, metric_y, 88, 66, "Commercial", clean_text(strength.get("marketability", market.get("commercial_potential", "—"))), "market signal")
    draw_metric_card(142, metric_y, 88, 66, "Concept", clean_text(strength.get("concept", "—")), "hook strength")
    draw_metric_card(244, metric_y, 88, 66, "Character", clean_text(strength.get("character", "—")), "role engine")
    draw_metric_card(346, metric_y, 88, 66, "Originality", clean_text(strength.get("originality", "—")), "freshness")

    y = metric_y - 92
    y = draw_text_block(40, y, "At A Glance", commercial or packaging, chars=92, max_lines=5)
    y = draw_text_block(40, y, "Packaging Potential", packaging, chars=92, max_lines=4)
    if market:
        budget = market.get("estimated_budget_tier", "")
        dist = market.get("distribution_angle", "")
        franchise = market.get("franchise_potential", "")
        y = draw_text_block(40, y, "Market Path", f"Budget: {budget}\nDistribution: {dist}\nFranchise: {franchise}", chars=92, max_lines=5)
    if comparables:
        draw_list(40, y, "Tone & Comparables", comparables, chars=80, max_items=4)
    draw_list(330, 213, "Audience Profile", audience, chars=34, max_items=5)
    footer(2)
    pdf.showPage()

    # PAGE 3 — Story snapshot
    draw_bg()
    y = draw_heading("Story Snapshot", height - 54, "Narrative Engine")
    for label, body in [("World", setting), ("Setup", intro), ("Conflict", conflict), ("Turn", reversal), ("Resolution", theme)]:
        y = draw_text_block(40, y, label, body, chars=88, max_lines=4)
        y -= 2
    y = draw_text_block(40, y, "Logline", logline, chars=92, max_lines=4)
    draw_text_block(40, y, "Synopsis", synopsis, chars=92, max_lines=12)
    footer(3)
    pdf.showPage()

    # PAGE 4 — Character and actor value
    draw_bg()
    y = draw_heading("Character & Arc", height - 54, "Performance Read")
    profile = val("protagonist_profile", {}) or {}
    who = clean_text(profile.get("summary") if isinstance(profile, dict) else "") or clean_text(val("protagonist_summary", "")) or f"{lead} carries the central pressure of the story."
    y = draw_text_block(40, y, "Who They Are", who, chars=60, max_lines=4)
    y = draw_text_block(40, y, "What They Want", val("actor_objective", ""), chars=60, max_lines=3)
    y = draw_text_block(40, y, "What Stands In The Way", conflict, chars=60, max_lines=4)
    arc = as_list(val("role_arc_map", []), 6)
    if arc:
        y = draw_list(40, y, "Arc", [" → ".join(arc)], chars=70, bullet=False, max_items=1)

    # Metric cards only for numbers, not text like theme.
    sy = height - 238
    draw_metric_card(370, sy, 70, 58, "Concept", clean_text(strength.get("concept", "—")), "")
    draw_metric_card(455, sy, 70, 58, "Character", clean_text(strength.get("character", "—")), "")
    draw_metric_card(370, sy - 76, 70, 58, "Market", clean_text(strength.get("marketability", "—")), "")
    draw_metric_card(455, sy - 76, 70, 58, "Original", clean_text(strength.get("originality", "—")), "")
    draw_text_block(370, sy - 160, "Core Theme", theme, chars=33, max_lines=5)

    y = 202
    y = draw_text_block(40, y, "Actor Prep Insights", f"Objective: {val('actor_objective', '')}", chars=92, max_lines=3)
    y = draw_list(40, y, "Tactics", val("playable_tactics", []), chars=85, max_items=5)
    draw_list(310, 170, "Danger Zones", val("audition_danger_zones", []), chars=42, max_items=4)
    footer(4)
    pdf.showPage()

    # PAGE 5 — Relationship dynamics / continuity
    draw_bg()
    y = draw_heading("Relationship Dynamics", height - 54, "Actor + Story Leverage")
    relationships = val("relationship_leverage_map", [])
    if isinstance(relationships, list) and relationships:
        pdf.setFont("Helvetica-Bold", 8)
        pdf.setFillColor(GOLD)
        pdf.drawString(40, y, "CHARACTER")
        pdf.drawString(155, y, "DYNAMIC")
        pdf.drawString(300, y, "FUNCTION")
        y -= 16
        pdf.setFont("Helvetica", 8.2)
        pdf.setFillColor(WHITE)
        for rel in relationships[:5]:
            if not isinstance(rel, dict):
                continue
            char = clean_text(rel.get("character", ""))[:18]
            dyn = clean_text(rel.get("dynamic", ""))[:28]
            func = clean_text(rel.get("function", ""))
            pdf.drawString(40, y, char)
            pdf.drawString(155, y, dyn)
            for line in wrap_lines(func, 45, 2):
                pdf.drawString(300, y, line)
                y -= 10
            y -= 8
    else:
        y = draw_text_block(40, y, "Character Leverage", character_leverage or "Pressure relationships shape the story.", chars=88, max_lines=5)

    y = min(y, 380)
    y = draw_list(40, y, "Emotional Continuity", val("emotional_continuity", []), chars=86, max_items=4)
    y = draw_list(40, y, "Reader Chemistry Tips", val("reader_chemistry_tips", []), chars=86, max_items=4)
    draw_list(330, 225, "Set Ready Checklist", val("set_ready_checklist", []), chars=38, max_items=5)
    footer(5)
    pdf.showPage()

    # PAGE 6 — Key moments / visual mood
    draw_bg()
    hero = find_report_image(6)
    if hero:
        draw_image_band(hero, 330, height - 54, 220, 150, alpha_overlay=True)
    y = draw_heading("Key Scenes & Moments", height - 54, "Specific Story Beats")
    y = draw_list(40, y, "Moments", moments, chars=76, max_items=4)
    y -= 8
    y = draw_text_block(40, y, "Commercial Positioning", "\n".join([commercial, packaging, character_leverage, clean_text(market.get("audience_reach", "")) if isinstance(market, dict) else ""]), chars=92, max_lines=9)
    layout_strategy = val("layout_strategy", {}) or {}
    document_layouts = val("document_layouts", {}) or {}
    analysis_layout = document_layouts.get("analysis_report", {}) if isinstance(document_layouts, dict) else {}
    visual_family = ""
    image_plan = val("image_plan", [])
    if isinstance(image_plan, list) and image_plan:
        visual_family = clean_text(image_plan[0].get("visual_family", "")) if isinstance(image_plan[0], dict) else ""
    mood_lines = [
        f"Layout Family: {analysis_layout.get('layout_family', layout_strategy.get('layout_style', ''))}",
        f"Cover Style: {analysis_layout.get('cover_style', '')}",
        f"Callout Style: {analysis_layout.get('callout_style', '')}",
        f"Visual Family: {visual_family}",
    ]
    draw_text_block(40, 150, "Visual Mood & Inspiration", "\n".join([m for m in mood_lines if not m.endswith(': ')]), chars=80, max_lines=5)
    footer(6)
    pdf.showPage()

    pdf.save()

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
    return render_template(
        "index.html",
        is_render=is_render_env(),
        gate_locked=True,
        gate_error="Incorrect access code. Please try again.",
    )


@app.route("/create-account", methods=["POST"])
def create_account():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = (request.form.get("password") or "").strip()
    access_code = (request.form.get("access_code") or "").strip()

    if not name or not email or not password or not access_code:
        return render_template("index.html", is_render=is_render_env(), gate_locked=True, gate_error="Please complete all Create Account fields, including your access code.")

    if access_code not in ACCESS_CODES:
        log_beta_access(access_code or "blank", "CREATE ACCOUNT ACCESS FAILED")
        return render_template("index.html", is_render=is_render_env(), gate_locked=True, gate_error="That access code is not approved yet.")

    try:
        db_init()
        existing = get_user_by_email(email)
        if existing:
            return render_template("index.html", is_render=is_render_env(), gate_locked=True, gate_error="That email already has an account. Please sign in instead.")

        password_hash = generate_password_hash(password)
        with DB_ENGINE.begin() as conn:
            conn.execute(text("""
                INSERT INTO beta_users (email, name, password_hash)
                VALUES (:email, :name, :password_hash)
            """), {"email": email, "name": name, "password_hash": password_hash})

        session["user_email"] = email
        session["user_name"] = name
        session["beta_access"] = True
        session["beta_code"] = access_code

        log_beta_access(access_code, "ACCOUNT CREATED")
        log_activity_event("account_created", route="/create-account", user_email=email, metadata={"name": name})
        return redirect(url_for("index"))
    except Exception as e:
        return render_template("index.html", is_render=is_render_env(), gate_locked=True, gate_error=f"Create account failed: {e}")


@app.route("/sign-in", methods=["POST"])
def sign_in():
    email = (request.form.get("email") or "").strip().lower()
    password = (request.form.get("password") or "").strip()

    if not email or not password:
        return render_template("index.html", is_render=is_render_env(), gate_locked=True, gate_error="Please enter your email and password to sign in.")

    try:
        db_init()
        user = get_user_by_email(email)
        if not user or not user.get("password_hash") or not check_password_hash(user["password_hash"], password):
            log_activity_event("sign_in_failed", route="/sign-in", user_email=email)
            return render_template("index.html", is_render=is_render_env(), gate_locked=True, gate_error="We couldn't sign you in with those credentials.")

        session["user_email"] = user["email"]
        session["user_name"] = user.get("name") or ""
        session["beta_access"] = True

        log_activity_event("sign_in", route="/sign-in", user_email=user["email"])
        return redirect(url_for("index"))
    except Exception as e:
        return render_template("index.html", is_render=is_render_env(), gate_locked=True, gate_error=f"Sign in failed: {e}")


@app.route("/logout")
def logout():
    email = get_current_user_email()
    if email:
        log_activity_event("sign_out", route="/logout", user_email=email)
    session.clear()
    return redirect(url_for("index"))


# ===== CORE ROUTES START =============================
@app.route("/")
def index():
    if get_current_user_email():
        log_activity_event("page_view", route="/", user_email=get_current_user_email(), metadata={"name": get_current_user_name()})
    return render_template(
        "index.html",
        is_render=is_render_env(),
        gate_locked=not has_beta_access(),
        gate_error=None,
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
                    "image_path": normalize_project_relative_path(slide_data.get("image_path", "") or ""),
                    "image_name": str(slide_data.get("image_name", "") or "").strip(),
                    "image_url": str(slide_data.get("image_url", "") or "").strip(),
                    "image_source": str(slide_data.get("image_source", "") or "").strip(),
                    "image_options": normalize_manifest_image_options(slide_data.get("image_options", [])),
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
                "image_path": normalize_project_relative_path(slide_data.get("image_path", "") or ""),

                "image_name": str(slide_data.get("image_name", "") or "").strip(),
                "image_url": str(slide_data.get("image_url", "") or "").strip(),
                "image_source": str(slide_data.get("image_source", "") or "").strip(),
                "image_options": normalize_manifest_image_options(slide_data.get("image_options", [])),
                "selected_option_id": str(slide_data.get("selected_option_id", "") or "").strip(),
            })

        LATEST_DECK_MANIFEST_JSON.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

        subprocess.run(
            ["python3", str(BASE_DIR / "deck_builder.py"), str(slide_plan_path)],
            cwd=str(BASE_DIR),
            check=True,
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

    try:
        build_actor_prep_pdf(script_text, character_name, LATEST_ACTOR_PREP_PDF)
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

    try:
        build_actor_booked_pdf(script_text, character_name, LATEST_ACTOR_BOOKED_PDF)
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
