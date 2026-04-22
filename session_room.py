from flask import Flask, request, redirect, url_for, render_template_string, jsonify
import json
import os
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
MAIN_BETA_URL = os.environ.get("MAIN_BETA_URL", "http://127.0.0.1:5000")

GATE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EVOLUM Session Gate</title>
<style>
body{
    margin:0;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    background:linear-gradient(135deg,#0b0b0b,#1a1a1a);
    color:#fff;
    min-height:100vh;
    display:flex;
    align-items:center;
    justify-content:center;
}
.card{
    width:min(92vw,460px);
    background:#151515;
    border:1px solid rgba(255,255,255,0.12);
    border-radius:18px;
    padding:28px;
    box-shadow:0 14px 34px rgba(0,0,0,0.34);
    text-align:center;
}
h1{
    margin:0 0 8px 0;
    font-size:28px;
}
.sub{
    color:#cfcfcf;
    font-size:14px;
    line-height:1.45;
    margin-bottom:18px;
}
.toggle-row{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:10px;
    margin-bottom:18px;
}
.toggle{
    padding:12px 14px;
    border-radius:12px;
    border:1px solid rgba(255,255,255,0.12);
    background:#0f0f0f;
    color:#d8d8d8;
    font-weight:700;
    cursor:pointer;
}
.toggle.active{
    border-color:#ff7a00;
    color:#fff;
}
.panel{
    display:none;
    text-align:left;
}
.panel.active{
    display:block;
}
label{
    display:block;
    font-size:11px;
    color:#e6b800;
    margin:0 0 6px 0;
    font-weight:700;
    letter-spacing:.03em;
}
input{
    width:100%;
    box-sizing:border-box;
    padding:12px;
    margin:0 0 14px 0;
    border-radius:8px;
    border:1px solid rgba(255,255,255,0.14);
    background:#0c0c0c;
    color:white;
}
button.primary{
    width:100%;
    padding:12px 16px;
    background:#ff7a00;
    border:none;
    border-radius:10px;
    color:white;
    font-weight:800;
    cursor:pointer;
}
.helper{
    color:#9f9f9f;
    font-size:12px;
    line-height:1.4;
    margin-top:10px;
}
.note{
    margin-top:14px;
    color:#8f8f8f;
    font-size:11px;
}
</style>
</head>
<body>
    <div class="card">
        <h1>EVOLUM</h1>
        <div class="sub">Choose your lane. Enter the beta as normal, or join a live deck collaboration session.</div>

        <div class="toggle-row">
            <button class="toggle active" id="betaTab" type="button" onclick="showPanel('beta')">Enter Beta</button>
            <button class="toggle" id="sessionTab" type="button" onclick="showPanel('session')">Join Session</button>
        </div>

        <div class="panel active" id="betaPanel">
            <form action="/enter-beta" method="get">
                <button class="primary" type="submit">Go To Main Beta</button>
            </form>
            <div class="helper">This keeps your current beta flow untouched.</div>
        </div>

        <div class="panel" id="sessionPanel">
            <form action="/join-session" method="post">
                <label for="session_id">Session ID</label>
                <input id="session_id" name="session_id" placeholder="e.g. courtjester-v1" required>

                <label for="session_password">Session Password</label>
                <input id="session_password" name="session_password" type="password" placeholder="Enter session password" required>

                <button class="primary" type="submit">Join Collaboration Room</button>
            </form>
            <div class="helper">This opens the shared room with Preview, Refine, and Session Control panels.</div>
        </div>

        <div class="note">Standalone collaboration prototype — separate from app.py</div>
    </div>

<script>
function showPanel(mode){
    document.getElementById("betaPanel").classList.toggle("active", mode === "beta");
    document.getElementById("sessionPanel").classList.toggle("active", mode === "session");
    document.getElementById("betaTab").classList.toggle("active", mode === "beta");
    document.getElementById("sessionTab").classList.toggle("active", mode === "session");
}
</script>
</body>
</html>
"""

ROOM_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EVOLUM Collaboration Room</title>
<style>
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:linear-gradient(135deg,#0b0b0b,#1a1a1a);color:#fff;}
.header{padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.10);display:flex;justify-content:space-between;align-items:center;gap:12px;background:#111;}
.title{font-size:20px;font-weight:800;}
.sub{color:#cfcfcf;font-size:12px;}
.shell{display:grid;grid-template-columns:1.05fr 1.05fr 0.9fr;gap:12px;padding:12px;height:calc(100vh - 74px);box-sizing:border-box;}
.panel{background:#141414;border:1px solid rgba(255,255,255,0.12);border-radius:16px;padding:14px;overflow:hidden;display:flex;flex-direction:column;min-height:0;}
.panel h2{margin:0 0 6px 0;font-size:16px;}
.panel-copy{color:#bfbfbf;font-size:12px;line-height:1.4;margin-bottom:10px;}
.preview-strip{flex:1;overflow:auto;display:flex;flex-direction:column;gap:10px;padding-right:4px;}
.slide{background:#0d0d0d;border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:10px;}
.slide-title{font-weight:800;margin-bottom:6px;}
.slide-body{color:#d6d6d6;font-size:13px;line-height:1.45;}
.field{margin-bottom:10px;}
label{display:block;font-size:10px;color:#e6b800;margin-bottom:4px;font-weight:700;}
input, textarea{width:100%;box-sizing:border-box;padding:10px;background:#0c0c0c;border:1px solid rgba(255,255,255,0.12);color:#fff;border-radius:8px;}
textarea{min-height:160px;resize:vertical;}
.actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:auto;}
button{padding:11px 14px;border:none;border-radius:10px;font-weight:800;cursor:pointer;}
.primary{background:#ff7a00;color:white;}
.secondary{background:#0f0f0f;color:#d8d8d8;border:1px solid rgba(255,255,255,0.12);}
.status-card{background:#0d0d0d;border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:10px;margin-bottom:10px;}
.status-label{color:#8f8f8f;font-size:10px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px;}
.status-value{font-size:14px;font-weight:800;}
.driver{color:#52a8ff;}
.small{color:#bfbfbf;font-size:12px;line-height:1.45;}
.linkbox{background:#0c0c0c;border:1px solid rgba(255,255,255,0.10);border-radius:10px;padding:10px;word-break:break-all;color:#d9d9d9;margin-top:6px;}
.flash{display:none;margin-top:10px;padding:10px;border-radius:10px;font-size:12px;font-weight:700;}
.flash.show{display:block;}
.flash.ok{background:rgba(66, 184, 131, .15);color:#9ff0c5;border:1px solid rgba(66, 184, 131, .25);}
.flash.err{background:rgba(255, 122, 0, .12);color:#ffc78d;border:1px solid rgba(255, 122, 0, .25);}
@media (max-width: 1100px){ .shell{grid-template-columns:1fr;height:auto;} }
</style>
</head>
<body>
    <div class="header">
        <div>
            <div class="title">Collaboration Room</div>
            <div class="sub">Session: {{ session_id }} · Shared deck room prototype</div>
        </div>
        <div class="sub">Driver: <span class="driver">{{ driver }}</span></div>
    </div>

    <div class="shell">
        <section class="panel">
            <h2>Preview Panel</h2>
            <div class="panel-copy">Shared live preview of the current deck state.</div>
            <div class="preview-strip" id="previewStrip">
                {% for slide in slides %}
                <div class="slide">
                    <div class="slide-title">{{ loop.index }}. {{ slide.title }}</div>
                    <div class="slide-body">{{ slide.body }}</div>
                </div>
                {% endfor %}
            </div>
        </section>

        <section class="panel">
            <h2>Refine Panel</h2>
            <div class="panel-copy">Single-driver editing area for slide text and rebuild actions.</div>

            <div class="field">
                <label>Slide Title</label>
                <input id="slideTitleInput" value="{{ slides[0].title if slides else 'Title Slide' }}">
            </div>

            <div class="field">
                <label>Slide Body</label>
                <textarea id="slideBodyInput">{{ slides[0].body if slides else 'Refine content here.' }}</textarea>
            </div>

            <div id="saveFlash" class="flash"></div>

            <div class="actions">
                <button class="primary" type="button" onclick="saveCurrentSlide()">Save Changes</button>
                <button class="primary" type="button">Rebuild Deck</button>
                <button class="secondary" type="button" onclick="window.location.reload()">Preview Mode</button>
                <button class="secondary" type="button">Pass Control</button>
            </div>
        </section>

        <section class="panel">
            <h2>Session Control</h2>
            <div class="panel-copy">Shared room controls, collaborator info, and meeting link area.</div>

            <div class="status-card">
                <div class="status-label">Session Status</div>
                <div class="status-value">{{ status }}</div>
            </div>

            <div class="status-card">
                <div class="status-label">Current Driver</div>
                <div class="status-value driver">{{ driver }}</div>
            </div>

            <div class="status-card">
                <div class="status-label">Meeting Link</div>
                <div class="small">Paste a Zoom or Google Meet link here for the room.</div>
                <div class="linkbox">{{ meeting_link }}</div>
            </div>

            <div class="status-card">
                <div class="status-label">How This Works</div>
                <div class="small">
                    Multiple collaborators can join the same room. One person drives edits at a time.
                    Others review, discuss, and pass control when needed.
                </div>
            </div>

            <div class="actions">
                <button class="primary" type="button">Copy Invite</button>
                <button class="secondary" type="button">Leave Room</button>
            </div>
        </section>
    </div>

<script>
async function saveCurrentSlide(){
    const title = document.getElementById("slideTitleInput").value;
    const body = document.getElementById("slideBodyInput").value;
    const flash = document.getElementById("saveFlash");
    flash.className = "flash show ok";
    flash.textContent = "Saving...";
    try{
        const resp = await fetch("/save-slide/{{ session_id }}", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({slide_index: 0, title, body})
        });
        const data = await resp.json();
        if(!resp.ok){
            flash.className = "flash show err";
            flash.textContent = data.error || "Save failed.";
            return;
        }
        flash.className = "flash show ok";
        flash.textContent = "Saved. Refresh the other device to see the update.";
        setTimeout(() => { window.location.reload(); }, 300);
    }catch(err){
        flash.className = "flash show err";
        flash.textContent = "Save failed.";
    }
}
</script>
</body>
</html>
""""""


def session_dir(session_id: str) -> Path:
    safe = "".join(ch for ch in session_id if ch.isalnum() or ch in ("-", "_")).strip() or "session"
    path = SESSIONS_DIR / safe
    path.mkdir(exist_ok=True)
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


@app.route("/session-gate", methods=["GET"])
def session_gate():
    return render_template_string(GATE_HTML)




@app.route("/enter-beta", methods=["GET"])
def enter_beta():
    return redirect(MAIN_BETA_URL)

@app.route("/join-session", methods=["POST"])
def join_session():
    session_id = (request.form.get("session_id") or "").strip()
    password = (request.form.get("session_password") or "").strip()

    path = session_dir(session_id)
    meta = ensure_session_files(path, session_id)

    # lightweight prototype behavior
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

    return render_template_string(
        ROOM_HTML,
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
