from flask import Flask, request, redirect, url_for, render_template, jsonify
import json
import os
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
MAIN_BETA_URL = os.environ.get("MAIN_BETA_URL", "http://127.0.0.1:5000")


def session_dir(session_id: str) -> Path:
    safe = "".join(ch for ch in session_id if ch.isalnum() or ch in ("-", "_")).strip() or "session"
    path = SESSIONS_DIR / safe
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_session_files(path: Path, session_id: str) -> dict:
    meta_file = path / "session_meta.json"
    manifest_file = path / "latest_deck_manifest.json"
    status_file = path / "status.json"

    if not meta_file.exists():
        meta = {
            "session_id": session_id,
            "password": "demo",
            "driver": "Session Host",
            "meeting_link": "Paste Zoom or Google Meet link here",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    else:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))

    if not status_file.exists():
        status_file.write_text(json.dumps({"status": "READY"}, indent=2), encoding="utf-8")

    if not manifest_file.exists():
        manifest = [
            {"title": "Title Slide", "body": "Shared deck session preview starts here."},
            {"title": "Logline", "body": "A collaboration room where creators review and refine decks together."},
            {"title": "Why This Matters", "body": "Preview, refine, and session control now live in one shared space."},
        ]
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return meta


@app.route("/")
def root():
    return redirect(url_for("session_gate"))


@app.route("/session-gate", methods=["GET"])
def session_gate():
    return render_template("session_gate.html")


@app.route("/enter-beta", methods=["GET"])
def enter_beta():
    return redirect(MAIN_BETA_URL)


@app.route("/join-session", methods=["POST"])
def join_session():
    session_id = (request.form.get("session_id") or "").strip()
    password = (request.form.get("session_password") or "").strip()

    path = session_dir(session_id)
    meta = ensure_session_files(path, session_id)

    if password != meta.get("password", "demo"):
        return "Wrong session password for prototype room.", 403

    return redirect(url_for("room", session_id=session_id))


@app.route("/room/<session_id>", methods=["GET"])
def room(session_id):
    path = session_dir(session_id)
    meta = ensure_session_files(path, session_id)

    manifest = json.loads((path / "latest_deck_manifest.json").read_text(encoding="utf-8"))
    status = json.loads((path / "status.json").read_text(encoding="utf-8")).get("status", "READY")

    slides = []
    for item in manifest:
        slides.append({
            "title": item.get("title", "Slide"),
            "body": item.get("body", item.get("content", "")),
        })

    return render_template(
        "room.html",
        session_id=session_id,
        driver=meta.get("driver", "Session Host"),
        meeting_link=meta.get("meeting_link", "Paste meeting link here"),
        status=status,
        slides=slides,
    )


@app.route("/save-slide/<session_id>", methods=["POST"])
def save_slide(session_id):
    path = session_dir(session_id)
    manifest_file = path / "latest_deck_manifest.json"
    if not manifest_file.exists():
        return jsonify({"error": "Manifest not found"}), 404

    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception:
        return jsonify({"error": "Manifest could not be read"}), 500

    data = request.get_json(silent=True) or {}
    slide_index = int(data.get("slide_index", 0))
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()

    if not isinstance(manifest, list) or not manifest:
        return jsonify({"error": "Manifest is empty"}), 400
    if slide_index < 0 or slide_index >= len(manifest):
        return jsonify({"error": "Slide index out of range"}), 400

    slide = manifest[slide_index]
    slide["title"] = title or slide.get("title", "Slide")
    slide["body"] = body

    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return jsonify({"ok": True, "slide_index": slide_index})


@app.route("/session-meta/<session_id>", methods=["GET"])
def session_meta(session_id):
    path = session_dir(session_id)
    meta = ensure_session_files(path, session_id)
    return jsonify(meta)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5055"))
    app.run(host="0.0.0.0", port=port, debug=False)
