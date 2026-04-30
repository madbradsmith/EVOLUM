from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import simpleSplit, ImageReader
from reportlab.pdfgen import canvas

# ── PATH CONSTANTS ────────────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).resolve().parent
_OUTPUT_DIR = _BASE_DIR / "visuals" / "output"  # persistent disk mount
_LATEST_PPTX = _OUTPUT_DIR / "latest.pptx"
_LATEST_PDF = _OUTPUT_DIR / "latest.pdf"


# ── DECK UTILITY HELPERS ──────────────────────────────────────────────────────

def normalize_project_relative_path(raw_path: str) -> str:
    cleaned = str(raw_path or "").strip().replace("\\", "/")
    if not cleaned:
        return ""
    prefixes = [
        str(_BASE_DIR).replace("\\", "/").rstrip("/") + "/",
        "/opt/render/project/src/",
        "opt/render/project/src/",
    ]
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    return cleaned.lstrip("/")


def project_file_url_for_path(raw_path: str) -> str:
    rel = normalize_project_relative_path(raw_path)
    if not rel:
        return ""
    return "/project-file?path=" + quote(rel)


def normalize_manifest_image_options(options) -> list:
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


def newest_generated_file(ext: str):
    excluded = {_LATEST_PPTX.name, _LATEST_PDF.name}
    files = [p for p in _OUTPUT_DIR.glob(f"pitch_deck_v*{ext}") if p.name not in excluded]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def _next_labeled_pptx(label: str):
    """Return the most recently written pitch_deck_{label}_v*.pptx file."""
    files = list(_OUTPUT_DIR.glob(f"pitch_deck_{label}_v*.pptx"))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def publish_latest_outputs(pptx_source, pdf_source) -> None:
    if pptx_source and pptx_source.exists():
        shutil.copy2(pptx_source, _LATEST_PPTX)
    if pdf_source and pdf_source.exists():
        shutil.copy2(pdf_source, _LATEST_PDF)


def rebuild_refined_deck(slides: list, latest_manifest_path=None, label: str = "", user_id: str = "") -> dict:
    """Build a new deck from refined slide data. Returns {'deck': name} or {'error': msg}."""
    if not slides or not isinstance(slides, list):
        return {"error": "No slide data provided."}

    try:
        slide_plan_payload = {
            "title": slides[0].get("title", "Refined Deck") if slides else "Refined Deck",
            "slides": [
                {
                    "title": str(s.get("title", "") or "").strip(),
                    "body": str(s.get("body", "") or "").strip(),
                    "layout": str(s.get("layout", "") or "text").strip(),
                    "stage": str(s.get("stage", "") or "refine").strip(),
                    "subtitle": str(s.get("subtitle", "") or "").strip(),
                    "image_path": normalize_project_relative_path(s.get("image_path", "") or ""),
                    "image_name": str(s.get("image_name", "") or "").strip(),
                    "image_url": str(s.get("image_url", "") or "").strip(),
                    "image_source": str(s.get("image_source", "") or "").strip(),
                    "image_options": normalize_manifest_image_options(s.get("image_options", [])),
                    "selected_option_id": str(s.get("selected_option_id", "") or "").strip(),
                }
                for s in slides
            ],
            "slide_count": len(slides),
        }

        slide_plan_path = _BASE_DIR / "slide_plan.json"
        temp_path = _BASE_DIR / "slide_plan.tmp.json"
        temp_path.write_text(json.dumps(slide_plan_payload, indent=2), encoding="utf-8")
        temp_path.replace(slide_plan_path)

        manifest_payload = [
            {
                "slide_number": i,
                "title": str(s.get("title", "") or "").strip(),
                "body": str(s.get("body", "") or "").strip(),
                "layout": str(s.get("layout", "") or "").strip(),
                "stage": str(s.get("stage", "") or "").strip(),
                "image_path": normalize_project_relative_path(s.get("image_path", "") or ""),
                "image_name": str(s.get("image_name", "") or "").strip(),
                "image_url": str(s.get("image_url", "") or "").strip(),
                "image_source": str(s.get("image_source", "") or "").strip(),
                "image_options": normalize_manifest_image_options(s.get("image_options", [])),
                "selected_option_id": str(s.get("selected_option_id", "") or "").strip(),
            }
            for i, s in enumerate(slides, start=1)
        ]

        if latest_manifest_path:
            manifest_out = Path(latest_manifest_path)
        elif user_id:
            prefix = f"{user_id}_"
            name = f"{prefix}latest_deck_manifest_{label}.json" if label else f"{prefix}latest_deck_manifest.json"
            manifest_out = _OUTPUT_DIR / name
        else:
            manifest_out = _OUTPUT_DIR / "latest_deck_manifest.json"
        manifest_out.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

        cmd = ["python3", str(_BASE_DIR / "deck_builder.py"), str(slide_plan_path)]
        if label:
            cmd += ["--label", label]
        if user_id:
            cmd += ["--uid", user_id]
        env = os.environ.copy()
        if user_id:
            env["EVOLUM_SESSION_ID"] = user_id
        subprocess.run(cmd, cwd=str(_BASE_DIR), env=env, check=True)

        fresh_pptx = newest_generated_file(".pptx") if not label else _next_labeled_pptx(label)
        fresh_pdf = newest_generated_file(".pdf") if not label else None
        publish_latest_outputs(fresh_pptx, fresh_pdf)

        return {"deck": fresh_pptx.name if fresh_pptx else _LATEST_PPTX.name}

    except Exception as e:
        return {"error": f"Refine rebuild failed: {e}"}


# ── SHARED DATA STRUCTURES ────────────────────────────────────────────────────

@dataclass
class BeatEntry:
    reference: str
    scene_heading: str
    cue_line: str
    dialogue: str
    beat: str
    subtext: str
    playable_note: str
    category: str = "TACTICAL"


# ── AI HELPERS (OPTIONAL / SAFE FALLBACKS) ───────────────────────────────────

def _call_text_ai(system_prompt: str, user_prompt: str, max_tokens: int = 350) -> str:
    """Best-effort text AI helper. Falls back silently if API/package isn't available."""
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("D_AI_OPENAI_API_KEY")
    model = os.getenv("D_AI_TEXT_MODEL", "gpt-4.1-mini")
    if not api_key:
        return ""
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            temperature=0.4,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return ""


def _methodology_lines() -> List[str]:
    return [
        "Uploaded script or sides supplied by the user.",
        "Developum AI extraction and scene/character parsing.",
        "Manifest / brain-derived story fields already available in the system.",
        "AI editorial assistance for concise summaries, framing, and report language when available.",
        "Public market-reference metadata only when already supplied to the system.",
    ]


# ── SHARED SCRIPT PARSING UTILITIES ──────────────────────────────────────────

def normalize_character_name(name: str) -> str:
    name = (name or "").strip().upper()
    name = re.sub(r"\s+", " ", name)
    return name


def _clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\x0c", "\n")
    text = text.replace("\ufffe", " ")
    # common transfer / OCR junk
    text = re.sub(r'\d{4,}\s*-\s*\w+ \d{1,2},\s*\d{4}\s*\d{1,2}:\d{2}\s*[AP]M\s*-?\s*', '', text)
    text = re.sub(r'([A-Z]{2,6}-){3,}[A-Z]{2,6}', '', text)
    text = re.sub(r'\b(TYPE|FILTER|LENGTH|RESOURCES|CONTENTS)\b(?=\s|$)', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def _is_scene_heading(line: str) -> bool:
    s = line.strip().upper()
    # Strip leading scene numbers like "1.", "4A.", "12B." before checking
    s = re.sub(r'^\d+[A-Z]?\.\s*', '', s)
    return (s.startswith("INT.") or s.startswith("EXT.") or
            s.startswith("INT ") or s.startswith("EXT ") or
            s.startswith("INT/EXT") or s.startswith("I/E "))


def _is_parenthetical(line: str) -> bool:
    s = line.strip()
    return s.startswith("(") and s.endswith(")")


def _looks_like_character_cue(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 40 or _is_scene_heading(s) or s.startswith("("):
        return False
    letters = [ch for ch in s if ch.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(1 for ch in letters if ch.isupper()) / max(1, len(letters))
    return upper_ratio > 0.85


def _normalize_cue(line: str) -> str:
    s = line.strip().upper()
    s = re.sub(r"\(.*?\)", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _estimate_page_no(global_line_index: int, lines_per_page: int = 55) -> int:
    return max(1, (global_line_index // lines_per_page) + 1)


def _infer_beat(dialogue: str, scene_heading: str) -> Tuple[str, str, str, str]:
    """Returns (beat_name, subtext, playable_note, category)."""
    lower = dialogue.strip().lower()

    # --- EMOTIONAL beats ---
    if any(k in lower for k in ["i'm sorry", "i am sorry", "forgive", "i never told", "truth is",
                                  "i have to tell", "i need you to know", "i lied", "the truth is",
                                  "i should have", "i was afraid", "i was wrong"]):
        return (
            "Reveal Something True",
            "The character is dropping a guard they've been holding the whole scene.",
            "Let the vulnerability come from the body, not just the words.",
            "EMOTIONAL",
        )
    if any(k in lower for k in ["please", "i need you", "i need this", "help me", "you have to",
                                  "you've got to", "i'm begging", "don't leave", "don't go",
                                  "i can't do this without"]):
        return (
            "Make a Plea",
            "The character is asking from a place of genuine need, not strategy.",
            "Earn this beat. The ask only lands when the stakes are completely visible.",
            "EMOTIONAL",
        )
    if any(k in lower for k in ["it's okay", "it'll be", "i'm here", "you're safe", "don't worry",
                                  "i've got you", "everything's going to be", "nothing's going to happen",
                                  "i'll take care", "you're going to be fine"]):
        return (
            "Offer Comfort",
            "The character is softening — choosing connection over self-protection.",
            "Let the care be specific. Generic comfort is just noise. Find the real thing they're soothing.",
            "EMOTIONAL",
        )
    if any(k in lower for k in ["i am", "i know who i am", "this is who", "i've always been",
                                  "i believe", "i stand by", "my whole life", "i was born",
                                  "this is what i do", "i'm not that", "i'm a", "that's who i am"]):
        return (
            "Assert Identity",
            "The character is claiming who they are — often under pressure to be something else.",
            "Don't perform it. Let the certainty land like a fact, not a speech.",
            "EMOTIONAL",
        )

    # --- RELATIONAL beats ---
    if any(k in lower for k in ["what if", "hear me out", "let's say", "suppose",
                                  "what would it take", "i'll give you", "how about",
                                  "deal", "i can offer", "let's make a deal", "i propose"]):
        return (
            "Negotiate",
            "The character is in problem-solving mode — offering terms, testing possibilities.",
            "Stay two steps ahead. Every offer has something held back.",
            "RELATIONAL",
        )
    if any(k in lower for k in ["that's not true", "you're wrong", "i don't believe",
                                  "that's a lie", "you never", "that's ridiculous",
                                  "that's not what", "you said", "you told me"]):
        return (
            "Challenge",
            "The character is pushing back and forcing the other person to justify themselves.",
            "Make it feel like a real refusal, not a reaction. The character chose this.",
            "RELATIONAL",
        )

    # --- CONCEALMENT beats ---
    if any(k in lower for k in ["nothing", "nothing's wrong", "never happened", "forget it",
                                  "nobody needs to know", "doesn't matter", "i don't know what you're talking",
                                  "you imagined", "you're confused", "that never", "drop it",
                                  "leave it alone", "it's nothing", "i don't want to talk about"]):
        return (
            "Protect a Secret",
            "The character is concealing something — from the other person or from themselves.",
            "Play what's being hidden, not the deflection. The audience should feel the weight behind the nothing.",
            "CONCEALMENT",
        )

    # --- TACTICAL beats ---
    if any(k in lower for k in ["be careful", "watch yourself", "you don't want to",
                                  "last chance", "i'm warning you", "don't make me",
                                  "you'll regret", "think about what you're doing",
                                  "i suggest you", "tread carefully"]):
        return (
            "Deliver a Warning",
            "The character is making consequences clear without fully committing to them yet.",
            "Keep it quiet. The most effective warnings land like facts, not threats.",
            "TACTICAL",
        )
    if any(k in lower for k in ["kill", "hurt you", "destroy", "finish you", "end this",
                                  "going to get you", "going to make you", "you'll pay",
                                  "punishment", "i'll make sure", "you're dead", "bash your"]):
        return (
            "Express Threat",
            "The character has crossed from warning into open aggression.",
            "Don't rush to volume. The menace lives in the specificity, not the size.",
            "TACTICAL",
        )
    if any(k in lower for k in ["who", "what", "where", "why", "how", "tell me",
                                  "i need to know", "what happened", "where were you",
                                  "explain", "what do you mean"]):
        return (
            "Pressure for Information",
            "The character is trying to get clarity while still keeping leverage.",
            "Ask like it matters. Curiosity is not enough here.",
            "TACTICAL",
        )
    if any(k in lower for k in ["calm down", "sit down", "listen", "hold on", "wait",
                                  "easy", "relax", "everybody", "settle", "take a breath",
                                  "let me finish", "let me explain"]):
        return (
            "Control the Room",
            "The character is slowing the chaos down and forcing the scene back under control.",
            "Use calm authority. The power is in the certainty, not the volume.",
            "TACTICAL",
        )
    if any(k in lower for k in ["don't", "do not", "can't", "cannot", "won't", "stop",
                                  "not going to", "never again", "that's enough", "enough"]):
        return (
            "Set a Boundary",
            "The character is drawing a line and making the other person feel the limit.",
            "Keep it clear and definite. This beat lands when the line feels real.",
            "TACTICAL",
        )
    if scene_heading and any(k in scene_heading.upper() for k in
                              ["OFFICE", "INTERROGATION", "BAR", "LOUNGE", "MEETING"]):
        return (
            "Apply Pressure",
            "The character is reading the other person and leaning in for leverage.",
            "Push with intelligence. Let the pressure come from focus, not force.",
            "TACTICAL",
        )

    # --- OBSERVATIONAL beats ---
    if any(k in lower for k in ["that means", "which means", "those are", "this is",
                                  "that's a", "it looks like", "notice", "clearly",
                                  "something's", "this means", "if.*is happening",
                                  "connect", "map", "symbol", "route", "coup", "planted",
                                  "that has to be", "that must be", "that would be",
                                  "is moving", "is looking for", "are looking for",
                                  "you know about", "so the entire", "the entire"]):
        return (
            "Read the Situation",
            "The character is processing information and forming a picture. Their intelligence is the weapon here.",
            "Let the thinking show. The audience should feel them assembling the truth in real time.",
            "OBSERVATIONAL",
        )
    if any(k in lower for k in ["i know", "i run", "i've seen", "i've heard", "i've been",
                                  "you should know", "here's what", "here's the thing",
                                  "two things", "one thing", "the thing is",
                                  "in this castle", "in this place", "around here",
                                  "dozens", "hundreds", "everyone knows", "nobody knows",
                                  "happens every", "every year", "days away", "two days",
                                  "we bring", "bring news", "stay with the"]):
        return (
            "Share Intelligence",
            "The character has information the other person needs. They control the room through what they know.",
            "Don't over-explain. Drop the intel with the confidence of someone who's been watching for a long time.",
            "OBSERVATIONAL",
        )
    if any(k in lower for k in ["didn't you", "isn't it", "wasn't it", "aren't you",
                                  "i think", "probably", "i'd guess", "my guess",
                                  "look at it this way", "congratulations", "at least",
                                  "you're now", "welcome to", "interesting", "fascinating",
                                  "look festive", "look busy", "carry something"]):
        return (
            "Test and Probe",
            "The character is reading the other person — using wit or indirect questions to surface a reaction.",
            "Stay light. The probe only works if the other person doesn't feel it coming.",
            "RELATIONAL",
        )
    if any(k in lower for k in ["just stay", "just keep", "just move", "time to go",
                                  "we have been", "they are gaining", "they are chasing",
                                  "we've been discovered", "run", "move fast", "better move",
                                  "stay on the", "just carry", "bolt", "go go", "get out",
                                  "left!", "right!", "down!", "up!", "jump!", "now!"]):
        return (
            "Navigate Danger",
            "The character is executing under pressure — managing an escape, a pursuit, or a critical real-time decision.",
            "These beats are instinct, not strategy. Stay in the body. Thought slows the scene down.",
            "TACTICAL",
        )

    # --- TRANSITIONAL beats ---
    if any(k in lower for k in ["good", "okay", "alright", "cool", "fine", "right",
                                  "understood", "got it", "move on", "let's move", "fair enough"]):
        return (
            "Reset and Move Forward",
            "The character absorbs the moment and redirects the energy instead of sitting in it.",
            "Treat it like a pivot, not relief.",
            "TRANSITIONAL",
        )

    return (
        "Hold Authority",
        "The character is managing the scene from a position of control.",
        "Stay grounded and specific. Quiet command usually wins this beat.",
        "TACTICAL",
    )


def extract_beats(script_text: str, character_name: str) -> List[BeatEntry]:
    script_text = _clean_text(script_text)
    lines = script_text.split("\n")
    target = normalize_character_name(character_name)

    beats: List[BeatEntry] = []
    current_scene = "SCENE NOT DETECTED"

    i = 0
    global_line_index = 0
    while i < len(lines):
        line = lines[i].strip()

        if _is_scene_heading(line):
            current_scene = line

        if _looks_like_character_cue(line):
            cue = _normalize_cue(line)
            if cue == target:
                page_no = _estimate_page_no(global_line_index)
                j = i + 1
                dialogue_lines: List[str] = []

                while j < len(lines):
                    nxt = lines[j].strip()
                    if not nxt:
                        if dialogue_lines:
                            break
                        j += 1
                        continue
                    if _is_scene_heading(nxt) or (_looks_like_character_cue(nxt) and not _is_parenthetical(nxt)):
                        break
                    if not _is_parenthetical(nxt):
                        dialogue_lines.append(nxt)
                    j += 1

                dialogue = " ".join(dialogue_lines).strip()
                dialogue = re.sub(r'\s{2,}', ' ', dialogue)
                if dialogue:
                    beat, subtext, playable, category = _infer_beat(dialogue, current_scene)
                    beats.append(
                        BeatEntry(
                            reference=f"Page {page_no}",
                            scene_heading=current_scene,
                            cue_line=line,
                            dialogue=dialogue,
                            beat=beat,
                            subtext=subtext,
                            playable_note=playable,
                            category=category,
                        )
                    )
                i = max(i + 1, j)
                global_line_index = i
                continue

        i += 1
        global_line_index += 1

    return beats


# ── FRIENDLIER CUSTOMER-FACING LANGUAGE ──────────────────────────────────────

_FRIENDLY_BEAT_TITLES: Dict[str, List[str]] = {
    "Reveal Something True":   ["Drop the Guard", "Let It Out", "Tell the Truth"],
    "Make a Plea":             ["Ask from Need", "Reach Out", "The Real Ask"],
    "Offer Comfort":           ["Steady the Other", "Hold Space", "Be Present"],
    "Assert Identity":         ["Stand Your Ground", "Claim Your Space", "This Is Who I Am"],
    "Negotiate":               ["Find the Deal", "Make the Offer", "Work the Room"],
    "Challenge":               ["Push Back", "Refuse the Reality", "Hold the Line"],
    "Protect a Secret":        ["Cover the Ground", "Deflect and Hold", "Nothing to See"],
    "Deliver a Warning":       ["Make It Clear", "Last Warning", "State the Consequence"],
    "Express Threat":          ["Show the Edge", "Let Them Feel It", "Full Menace"],
    "Pressure for Information":["Push for Answers", "Get the Truth", "Lean In for Clarity"],
    "Control the Room":        ["Take Control", "Steady the Room", "Own the Moment"],
    "Set a Boundary":          ["Draw the Line", "Hold Your Ground", "Make the Limit Clear"],
    "Apply Pressure":          ["Turn Up the Pressure", "Lean In", "Press the Point"],
    "Read the Situation":      ["Piece It Together", "See What's There", "Work the Picture"],
    "Share Intelligence":      ["Drop the Intel", "Show What You Know", "Brief the Room"],
    "Test and Probe":          ["Read the Reaction", "Feel Them Out", "Try the Line"],
    "Navigate Danger":         ["Execute Now", "Make the Move", "Stay in Motion"],
    "Reset and Move Forward":  ["Shift the Energy", "Reset and Move On", "Pivot Cleanly"],
    "Hold Authority":          ["Stay in Command", "Lead Quietly", "Keep Control"],
}


def _friendly_beat_title(beat: str, index: int) -> str:
    options = _FRIENDLY_BEAT_TITLES.get(beat, [beat])
    return options[(index - 1) % len(options)]


_GROUP_COACHING: Dict[str, str] = {
    "Reveal Something True":    "This is the role's most exposed beat. What gets revealed here should visibly cost the character. Find the moment the guard actually drops — it's in the body, not the words.",
    "Make a Plea":              "The character is operating without armor. Earn the need. If the stakes aren't visible before the ask, the plea reads as manipulation, not desperation.",
    "Offer Comfort":            "The character is choosing someone else over their own self-protection. Play what they're giving up to give this. That's where the scene lives.",
    "Assert Identity":          "These beats are declarations under pressure. Don't let them become speeches. The certainty should land like a closed door, not an open argument.",
    "Negotiate":                "The character is always thinking two moves ahead. Every offer conceals what they're actually protecting. Find the thing they won't give, and play from there.",
    "Challenge":                "The character refuses to accept the other person's version of reality. Anchor the refusal — this was a choice, not a reaction.",
    "Protect a Secret":         "The most textured beats in the role. Play what's underneath the deflection — the weight of what can't be said is what the audience reads. Let it be effortful.",
    "Deliver a Warning":        "The most effective warnings are stated like facts. Strip the emotion out. The consequence is real — say it like something that's already decided.",
    "Express Threat":           "Don't go to volume. The menace lives in specificity. The character knows exactly what they're capable of and wants the other person to feel that certainty.",
    "Pressure for Information": "The character isn't just asking — they're tracking what the other person gives away with each answer. Play the listening as much as the questioning.",
    "Control the Room":         "Calm is the weapon here. The character is slowing the scene down on purpose. Every steady breath is an assertion of power.",
    "Set a Boundary":           "Play the clarity, not the anger. The line is already drawn. The beat is making the other person feel where it is.",
    "Apply Pressure":           "The character is leaning in with a read on the other person. Intelligence drives this beat, not force. Let the pressure be precise.",
    "Read the Situation":       "The character is assembling a picture in real time. Intelligence is the weapon. Let the audience watch the pieces connect.",
    "Share Intelligence":       "The character controls through what they know. Each detail shared is a deliberate choice about what to reveal and when.",
    "Test and Probe":           "This beat is a read. The character is listening for something in the response. The probe only works if it doesn't feel like one.",
    "Navigate Danger":          "These are instinct beats. The character acts before they think. Stay in the body — deliberation kills the urgency of these scenes.",
    "Reset and Move Forward":   "This is a pivot beat. The character absorbs what just happened and redirects — it should feel like a choice, not a collapse.",
    "Hold Authority":           "The baseline state of this role. The danger is flatness — keep it textured. Authority that never wavers reads as bored, not powerful.",
}
_DEFAULT_GROUP_COACHING = "Protect the role's internal logic on these beats. Find the specific thing the character wants in each scene and let that drive the line."


def group_beats_by_type(beats: List[BeatEntry]) -> List[dict]:
    """Groups beats by type. Returns list ordered by frequency, each entry has coaching + up to 3 sample beats."""
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for b in beats:
        groups[b.beat].append(b)

    result = []
    for beat_type, group in sorted(groups.items(), key=lambda x: -len(x[1])):
        pages = sorted(set(b.reference for b in group), key=lambda r: int(re.sub(r'\D', '', r) or 0))
        samples = group[:3]
        result.append({
            "beat_type": beat_type,
            "label": _friendly_beat_title(beat_type, 1),
            "coaching": _GROUP_COACHING.get(beat_type, _DEFAULT_GROUP_COACHING),
            "count": len(group),
            "pages": pages,
            "samples": samples,
        })
    return result


# ── SHARED PDF DRAWING UTILITIES ──────────────────────────────────────────────

def _split_lines(pdf: canvas.Canvas, text: str, font_name: str, font_size: int, max_width: int) -> List[str]:
    return simpleSplit(text or "", font_name, font_size, max_width)


def _draw_lines(pdf: canvas.Canvas, lines: List[str], x: float, y: float, leading: int, font_name: str, font_size: int, color=colors.white) -> float:
    pdf.setFont(font_name, font_size)
    pdf.setFillColor(color)
    for line in lines:
        pdf.drawString(x, y, line)
        y -= leading
    return y


def _footer(pdf: canvas.Canvas, width: float, page_no: int) -> None:
    pdf.setStrokeColor(colors.HexColor("#2b2b2b"))
    pdf.line(42, 28, width - 42, 28)
    pdf.setFillColor(colors.HexColor("#8f8f8f"))
    pdf.setFont("Helvetica", 8)
    pdf.drawString(42, 16, "Powered by Developum AI Engine")
    pdf.drawRightString(width - 42, 16, f"Page {page_no}")


def _new_page(pdf: canvas.Canvas, width: float, height: float, page_no: int, bg_color) -> float:
    _footer(pdf, width, page_no)
    pdf.showPage()
    pdf.setFillColor(bg_color)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    return height - 56


def _ensure_space(pdf: canvas.Canvas, width: float, height: float, y: float, needed: float, page_no: int, bg_color) -> Tuple[float, int]:
    if y - needed < 48:
        y = _new_page(pdf, width, height, page_no, bg_color)
        page_no += 1
        pdf.setFillColor(colors.white)
    return y, page_no


def _safe(val, fallback: str = "") -> str:
    if val is None:
        return fallback
    if isinstance(val, list):
        return ", ".join(str(v) for v in val if str(v).strip())
    return str(val).strip() or fallback


def _clean_characters(chars: List) -> List[str]:
    bad = {"TYPE", "FILTER", "LENGTH", "RESOURCES", "CONTENTS"}
    out = []
    for c in chars or []:
        s = str(c).strip()
        if not s or s.upper() in bad:
            continue
        if len(s) > 40:
            continue
        out.append(s)
    return out


class _PDFCtx:
    def __init__(self, pdf: canvas.Canvas, width: float, height: float, left: float,
                 usable_width: float, charcoal, gold, blue, white, muted, soft, panel):
        self.pdf = pdf
        self.width = width
        self.height = height
        self.left = left
        self.uw = usable_width
        self.charcoal = charcoal
        self.gold = gold
        self.blue = blue
        self.white = white
        self.muted = muted
        self.soft = soft
        self.panel = panel
        self.y = height - 56
        self.page_no = 2

    def new_page(self):
        self.y = _new_page(self.pdf, self.width, self.height, self.page_no, self.charcoal)
        self.page_no += 1
        self.pdf.setFillColor(self.white)

    def section_header(self, title: str, subtitle: str = ""):
        self.y, self.page_no = _ensure_space(self.pdf, self.width, self.height, self.y, 44, self.page_no, self.charcoal)
        self.pdf.setFillColor(self.gold)
        self.pdf.setFont("Helvetica-Bold", 15)
        self.pdf.drawString(self.left, self.y, title)
        self.y -= 18
        if subtitle:
            self.y = _draw_lines(self.pdf,
                                 _split_lines(self.pdf, subtitle, "Helvetica", 10, self.uw),
                                 self.left, self.y, 12, "Helvetica", 10, self.soft)
            self.y -= 6

    def text_block(self, text: str, color=None, font_name: str = "Helvetica", font_size: int = 11, leading: int = 14, inset: int = 0):
        color = color if color is not None else self.muted
        lines = _split_lines(self.pdf, text, font_name, font_size, self.uw - inset)
        self.y, self.page_no = _ensure_space(self.pdf, self.width, self.height, self.y,
                                             max(40, len(lines) * leading + 10), self.page_no, self.charcoal)
        self.y = _draw_lines(self.pdf, lines, self.left + inset, self.y, leading, font_name, font_size, color)

    def bullet_list(self, items: List[str], bullet_color=None):
        bc = bullet_color or self.blue
        for item in items:
            lines = _split_lines(self.pdf, item, "Helvetica", 10, self.uw - 26)
            self.y, self.page_no = _ensure_space(self.pdf, self.width, self.height, self.y,
                                                 len(lines) * 13 + 14, self.page_no, self.charcoal)
            self.pdf.setFillColor(bc)
            self.pdf.setFont("Helvetica-Bold", 12)
            self.pdf.drawString(self.left, self.y, "•")
            self.y = _draw_lines(self.pdf, lines, self.left + 14, self.y, 13, "Helvetica", 10, self.muted)
            self.y -= 3

    def chip_row(self, items: List[str], chip_color=None):
        color = chip_color or self.blue
        x = self.left
        y = self.y
        max_h = 22
        for item in items:
            label = str(item).strip()
            if not label:
                continue
            w = min(max(54, 8 + len(label) * 5.6), self.uw)
            if x + w > self.left + self.uw:
                x = self.left
                y -= max_h + 6
                self.y, self.page_no = _ensure_space(self.pdf, self.width, self.height, y, max_h + 10, self.page_no, self.charcoal)
            self.pdf.setFillColor(self.panel)
            self.pdf.roundRect(x, y - 16, w, max_h, 8, stroke=0, fill=1)
            self.pdf.setStrokeColor(color)
            self.pdf.roundRect(x, y - 16, w, max_h, 8, stroke=1, fill=0)
            self.pdf.setFillColor(color)
            self.pdf.setFont("Helvetica-Bold", 9)
            self.pdf.drawString(x + 8, y - 4, label[:26])
            x += w + 6
        self.y = y - max_h - 8

    def info_row(self, label: str, value: str):
        lines = simpleSplit(str(value or "-"), "Helvetica", 10.5, self.uw - 120)
        self.y, self.page_no = _ensure_space(self.pdf, self.width, self.height, self.y,
                                             len(lines) * 14 + 10, self.page_no, self.charcoal)
        self.pdf.setFillColor(self.white)
        self.pdf.setFont("Helvetica-Bold", 10.5)
        self.pdf.drawString(self.left, self.y, label)
        self.pdf.setFillColor(self.muted)
        self.pdf.setFont("Helvetica", 10.5)
        yy = self.y
        for line in lines:
            self.pdf.drawString(self.left + 120, yy, line)
            yy -= 14
        self.y = yy - 4

    def methodology_box(self):
        lines: List[str] = []
        for item in _methodology_lines():
            lines.extend(_split_lines(self.pdf, item, "Helvetica", 9, self.uw - 26))
        box_h = max(84, len(lines) * 11 + 34)
        self.y, self.page_no = _ensure_space(self.pdf, self.width, self.height, self.y, box_h + 10, self.page_no, self.charcoal)
        self.pdf.setFillColor(self.panel)
        self.pdf.roundRect(self.left, self.y - box_h + 10, self.uw, box_h, 12, stroke=0, fill=1)
        self.pdf.setFillColor(self.gold)
        self.pdf.setFont("Helvetica-Bold", 12)
        self.pdf.drawString(self.left + 14, self.y - 10, "Sources & Methodology")
        yy = self.y - 28
        for item in _methodology_lines():
            self.pdf.setFillColor(self.gold)
            self.pdf.setFont("Helvetica-Bold", 10)
            self.pdf.drawString(self.left + 14, yy, "•")
            block = _split_lines(self.pdf, item, "Helvetica", 9, self.uw - 34)
            yy = _draw_lines(self.pdf, block, self.left + 28, yy, 11, "Helvetica", 9, self.muted)
            yy -= 2
        self.y -= box_h + 10


# ── LIGHT SYNTHESIS HELPERS ───────────────────────────────────────────────────

def _fallback_audition_snapshot(character_name: str, beats: List[BeatEntry]) -> str:
    top = beats[0].beat if beats else "Hold Authority"
    return (
        f"{character_name.title()} reads as a role carried by pressure, control, and quick decisions. "
        f"Across the current sides, the material most often asks for '{top}'. "
        f"The strongest audition choice is usually specific, contained, and alive in the listening."
    )


def _fallback_booked_snapshot(character_name: str, beats: List[BeatEntry]) -> str:
    top = beats[0].beat if beats else "Hold Authority"
    scene_count = len(list(dict.fromkeys([b.scene_heading for b in beats if b.scene_heading])))
    return (
        f"{character_name.title()} currently reads like a role shaped by control, timing, and scene pressure. "
        f"The present extraction finds {len(beats)} speaking beats across {scene_count or 1} scene(s), with the role most often living inside '{top}'. "
        f"The job in booked-mode is continuity: keep the core behavior stable while allowing pressure to change pace, patience, and openness."
    )


def _fallback_exec_summary(title: str, genre: str, tone: str, logline: str) -> str:
    return (
        f"{title.title()} currently presents as {genre or 'a feature screenplay'} with a tone that leans {tone or 'grounded and commercial'}. "
        f"At its best, the material works because the central pressure line is easy to understand and the story engine is clear. "
        f"The clearest commercial hook remains: {logline or 'the protagonist is forced into a high-pressure situation that escalates toward a reversal.'}"
    )


def _smart_summary(mode: str, title: str, character_name: str, logline: str, synopsis: str, beats: List[BeatEntry], extra: str = "") -> str:
    if mode == "audition":
        user = (
            f"Write a 90-word actor-facing audition snapshot for the role {character_name}. "
            f"Conversational, concise, helpful for a novice actor. No fluff. "
            f"Use this context: logline={logline}; synopsis={synopsis}; top beats={[b.beat for b in beats[:5]]}; extra={extra}."
        )
        out = _call_text_ai(
            "You write concise, conversational actor prep copy for audition packets. Avoid robotic labels. Do not mention AI.",
            user,
            max_tokens=180,
        )
        return out or _fallback_audition_snapshot(character_name, beats)
    if mode == "booked":
        user = (
            f"Write a 110-word booked-role overview for the role {character_name}. "
            f"Conversational but professional. Focus on continuity, pressure, and role behavior. "
            f"Use: logline={logline}; synopsis={synopsis}; beats={[b.beat for b in beats[:8]]}; extra={extra}."
        )
        out = _call_text_ai(
            "You write clear, practical actor continuity notes. Avoid jargon overload. Do not mention AI.",
            user,
            max_tokens=220,
        )
        return out or _fallback_booked_snapshot(character_name, beats)
    user = (
        f"Write a 110-word executive summary for the screenplay {title}. Professional, concise, market-aware, novice-friendly. "
        f"Use only this info: genre={extra}; logline={logline}; synopsis={synopsis}."
    )
    out = _call_text_ai(
        "You write concise, professional script analysis summaries for development reports. No hype. No fluff. Do not mention AI.",
        user,
        max_tokens=220,
    )
    return out or _fallback_exec_summary(title, extra, "", logline)


def _unique_scenes(beats: List[BeatEntry]) -> List[str]:
    return list(dict.fromkeys([b.scene_heading for b in beats if b.scene_heading]))


# ── ACTOR V2 DYNAMIC INTELLIGENCE + IMAGE HELPERS ────────────────────────────

def _as_list(value, fallback: Optional[List[str]] = None) -> List[str]:
    if value is None:
        return fallback or []
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                joined = " — ".join(str(v).strip() for v in item.values() if str(v).strip())
                if joined:
                    out.append(joined)
            else:
                s = str(item).strip()
                if s:
                    out.append(s)
        return out or (fallback or [])
    s = str(value).strip()
    if not s:
        return fallback or []
    parts = [x.strip(" •-\n\t") for x in re.split(r"\n+|;|\|", s) if x.strip(" •-\n\t")]
    return parts or [s]


def _project_title(brain_data: Dict) -> str:
    for key in ["title", "project_title", "script_title", "name"]:
        v = _safe(brain_data.get(key))
        if v:
            return v
    return "Untitled"


def _world_value(brain_data: Dict) -> str:
    return _safe(brain_data.get("world") or brain_data.get("genre") or brain_data.get("setting"), "Script world")


def _actor_ai_json(character_name: str, title: str, mode: str, brain_data: Dict, beats: List[BeatEntry]) -> Dict:
    """Returns actor-specific copy blocks. Uses API when available; otherwise strong local fallbacks."""
    logline = _safe(brain_data.get("logline"))
    synopsis = _safe(brain_data.get("synopsis"))[:1800]
    top_dialogue = [f"{b.scene_heading}: {b.dialogue[:160]}" for b in beats[:8]]
    system = (
        "You create premium, practical actor preparation reports from screenplay data. "
        "Be specific to the role and script. Do not use generic filler. Do not mention AI. "
        "Return ONLY valid JSON."
    )
    user = f"""
Create concise actor-report copy for {character_name} in {title}.
Mode: {mode}
Logline: {logline}
Synopsis: {synopsis}
Detected beat types: {[b.beat for b in beats[:12]]}
Sample dialogue beats: {top_dialogue}
Existing brain fields:
objective={brain_data.get('actor_objective')}
tactics={brain_data.get('playable_tactics')}
triggers={brain_data.get('emotional_triggers')}
danger_zones={brain_data.get('audition_danger_zones')}
reader_tips={brain_data.get('reader_chemistry_tips')}
memorization={brain_data.get('memorization_beats')}
continuity={brain_data.get('emotional_continuity')}
set_ready={brain_data.get('set_ready_checklist')}

Return JSON with these keys:
summary: string, 60-90 words
casting_read: list of 4 specific bullets
playable_tactics: list of 4 specific bullets
emotional_triggers: list of 4 specific bullets
danger_zones: list of 4 specific bullets
memorization_beats: list of 4 specific bullets
reader_chemistry: list of 4 specific bullets
look_presence: list of 4 specific bullets
booked_continuity: list of 5 specific bullets
scene_priorities: list of 6 specific bullets
"""
    raw = _call_text_ai(system, user, max_tokens=850)
    if raw:
        try:
            import json
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
                cleaned = re.sub(r"```$", "", cleaned).strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    top = beats[0].beat if beats else "Hold Authority"
    role = character_name.title()
    return {
        "summary": _fallback_audition_snapshot(character_name, beats) if mode == "audition" else _fallback_booked_snapshot(character_name, beats),
        "casting_read": [
            f"See whether {role} can enter the scene with a clear want, not just a mood.",
            "Test how well the actor listens before pushing the next line.",
            "Protect the role's pressure without turning every beat into volume.",
            f"Let the {top.lower()} energy shape timing, stillness, and eye contact.",
        ],
        "playable_tactics": _as_list(brain_data.get("playable_tactics"), [
            "Hold authority quietly before raising pressure.",
            "Use the other person's reaction as fuel for the next choice.",
            "Let the thought land before moving to the next line.",
            "Play the objective, not the emotion label.",
        ]),
        "emotional_triggers": _as_list(brain_data.get("emotional_triggers"), [
            "Loss of control", "Being doubted", "Time pressure", "A truth being withheld"
        ]),
        "danger_zones": _as_list(brain_data.get("audition_danger_zones"), [
            "Do not overplay intention before the scene earns it.",
            "Do not mistake authority for loudness.",
            "Do not flatten listening beats into waiting time.",
            "Do not rush the turn just because the dialogue is familiar.",
        ]),
        "memorization_beats": _as_list(brain_data.get("memorization_beats"), [
            "Mark the first line where the character needs something specific.",
            "Circle the line where the power balance changes.",
            "Protect the silence before the biggest choice.",
            "Know the final emotional temperature of the scene.",
        ]),
        "reader_chemistry": _as_list(brain_data.get("reader_chemistry_tips"), [
            "Give the reader exact eyelines and let interruptions feel live.",
            "Use the reader to sharpen pressure changes, not flatten rhythm.",
            "Let reactions answer before dialogue does.",
            "Stay available to pace shifts instead of locking one rhythm.",
        ]),
        "look_presence": _as_list(brain_data.get("costume_behavior_clues"), [
            "Dress to suggest the world without wearing a costume.",
            "Let posture show status before dialogue explains it.",
            "Choose one physical habit that tightens under pressure.",
            "Keep movement economical unless the scene forces release.",
        ]),
        "booked_continuity": _as_list(brain_data.get("emotional_continuity"), [
            "Track where confidence cracks even when behavior stays controlled.",
            "Let pressure affect pace before it affects volume.",
            "Carry unresolved tension into the next scene instead of resetting.",
            "Protect listening behavior across takes.",
            "Know what the character learned in the previous scene.",
        ]),
        "scene_priorities": [
            f"{b.reference}: {_friendly_beat_title(b.beat, i+1)} — {b.playable_note}" for i, b in enumerate(beats[:6])
        ] or ["No specific scene priorities were detected for this character name."],
    }


def _find_actor_report_image(brain_data: Dict, mode: str, character_name: str, title: str) -> Optional[Path]:
    """Find existing image first; optionally generate one with FAL if configured."""
    candidates: List[Path] = []

    # 1. Explicit paths from brain image_plan (local_path/image_path keys)
    for item in brain_data.get("image_plan") or []:
        if isinstance(item, dict):
            for key in ["local_path", "image_path", "path", "selected_image_path"]:
                val = str(item.get(key) or "").strip()
                if val and not val.startswith("http"):
                    p = Path(val)
                    if p.exists() and p.is_file():
                        candidates.append(p)

    # 2. Scan generated_images/ recursively — sort newest first so current session wins
    gen_dir = _BASE_DIR / "generated_images"
    if gen_dir.exists():
        found = []
        for pat in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
            found.extend(gen_dir.rglob(pat))
        found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        candidates.extend(found)

    # 3. Fallback: visuals/user_uploaded
    for base in ["visuals/user_uploaded", "static/generated"]:
        bp = _BASE_DIR / base
        if bp.exists():
            for pat in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
                hits = sorted(bp.rglob(pat), key=lambda p: p.stat().st_mtime, reverse=True)
                candidates.extend(hits)

    for path in candidates:
        if path.exists() and path.is_file() and path.stat().st_size > 1000:
            return path

    fal_key = os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY")
    if not fal_key:
        return None
    try:
        import urllib.request
        import fal_client  # type: ignore
        out_dir = Path("output/actor_report_images")
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", f"{title}_{character_name}_{mode}").strip("_").lower()[:80]
        out_path = out_dir / f"{safe_name}.png"
        if out_path.exists():
            return out_path
        world = _world_value(brain_data)
        tone = _safe(brain_data.get("tone"), "cinematic, grounded")
        prompt = (
            f"Cinematic actor preparation report image for {character_name} in {title}. "
            f"World: {world}. Tone: {tone}. Professional film still, dramatic but tasteful, "
            f"no text, no logos, no watermark, shallow depth of field, premium streaming drama look, 16:9."
        )
        result = fal_client.subscribe(
            os.getenv("FAL_IMAGE_MODEL", "fal-ai/flux/dev"),
            arguments={"prompt": prompt, "image_size": "landscape_16_9", "num_images": 1},
        )
        url = None
        images = result.get("images") if isinstance(result, dict) else None
        if images and isinstance(images, list):
            first = images[0]
            if isinstance(first, dict):
                url = first.get("url")
        if url:
            urllib.request.urlretrieve(url, out_path)
            return out_path if out_path.exists() else None
    except Exception:
        return None
    return None


def _draw_cover_image(pdf: canvas.Canvas, image_path: Optional[Path], x: float, y: float, w: float, h: float, stroke_color) -> None:
    pdf.setFillColor(colors.HexColor("#0b0b0b"))
    pdf.roundRect(x, y, w, h, 14, stroke=0, fill=1)
    if image_path and image_path.exists():
        try:
            pdf.drawImage(ImageReader(str(image_path)), x, y, width=w, height=h, preserveAspectRatio=True, anchor="c", mask="auto")
        except Exception:
            pass
    pdf.setStrokeColor(stroke_color)
    pdf.roundRect(x, y, w, h, 14, stroke=1, fill=0)


def _draw_card(pdf: canvas.Canvas, x: float, y: float, w: float, h: float, title: str, lines: List[str], gold, panel, white, muted) -> None:
    pdf.setFillColor(panel)
    pdf.roundRect(x, y - h, w, h, 12, stroke=0, fill=1)
    pdf.setFillColor(gold)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(x + 12, y - 18, title.upper()[:34])
    yy = y - 38
    for item in lines[:6]:
        chunks = simpleSplit(str(item), "Helvetica", 9, w - 34)
        if yy - len(chunks)*11 < y - h + 10:
            break
        pdf.setFillColor(gold)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(x + 12, yy, "•")
        yy = _draw_lines(pdf, chunks, x + 24, yy, 11, "Helvetica", 9, muted)
        yy -= 3


def _page_bg(pdf: canvas.Canvas, width: float, height: float, charcoal, gold):
    pdf.setFillColor(charcoal)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    pdf.setFillColor(gold)
    pdf.rect(0, height - 6, width, 6, stroke=0, fill=1)



# ── MODE 1: AUDITION QUICKPACK ───────────────────────────────────────────────

def build_actor_prep_pdf(script_text: str, character_name: str, output_path: str | Path, brain_data: Optional[Dict] = None) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    beats = extract_beats(script_text, character_name)
    brain_data = brain_data or {}

    pdf = canvas.Canvas(str(output_path), pagesize=LETTER)
    pdf.setTitle(f"{character_name.title()} — Actor Prep V2")
    width, height = LETTER
    left, right = 42, width - 42
    usable_width = right - left

    charcoal = colors.HexColor("#111111")
    panel = colors.HexColor("#1b1f23")
    gold = colors.HexColor("#f0c15d")
    white = colors.white
    muted = colors.HexColor("#d8d8d8")

    title = _project_title(brain_data)
    tone = _safe(brain_data.get("tone"), "Performance-driven")
    world = _world_value(brain_data)
    intelligence = _actor_ai_json(character_name, title, "audition", brain_data, beats)
    image_path = _find_actor_report_image(brain_data, "actor_prep", character_name, title)

    # Save JSON for HTML report page
    try:
        json_path = output_path.with_suffix(".json")
        json_path.write_text(json.dumps({
            "character_name": character_name,
            "title": title,
            "tone": _safe(brain_data.get("tone"), ""),
            "world": world,
            "genre": _safe(brain_data.get("genre"), ""),
            "beat_count": len(beats),
            "intelligence": intelligence,
        }, indent=2), encoding="utf-8")
    except Exception:
        pass

    _page_bg(pdf, width, height, charcoal, gold)
    pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(left, height - 54, "ACTOR PREP REPORT")
    pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 39)
    pdf.drawString(left, height - 100, character_name.upper()[:24])
    pdf.setFillColor(muted); pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(left, height - 126, title.upper()[:42])
    pdf.setStrokeColor(gold); pdf.line(left, height - 152, right, height - 152)
    _draw_cover_image(pdf, image_path, left, height - 390, usable_width, 180, gold)

    snap = _safe(intelligence.get("summary"), _fallback_audition_snapshot(character_name, beats))
    lines = simpleSplit(snap, "Helvetica-Bold", 11, usable_width - 36)
    box_h = max(92, len(lines)*14 + 36)
    y = height - 430
    pdf.setFillColor(panel); pdf.roundRect(left, y - box_h, usable_width, box_h, 12, stroke=0, fill=1)
    pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 9); pdf.drawString(left + 14, y - 20, "ROLE SNAPSHOT")
    _draw_lines(pdf, lines, left + 14, y - 40, 14, "Helvetica-Bold", 11, white)

    card_y = y - box_h - 42
    card_w = (usable_width - 24) / 3
    for i, (label, vals) in enumerate([
        ("TONE", [tone]),
        ("WORLD", [world]),
        ("DETECTED BEATS", [f"{len(beats)} playable beats", f"{len(_unique_scenes(beats)) or 1} scene zones"]),
    ]):
        _draw_card(pdf, left + i*(card_w+12), card_y, card_w, 86, label, vals, gold, panel, white, muted)
    _footer(pdf, width, 1); pdf.showPage()

    _page_bg(pdf, width, height, charcoal, gold)
    pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 25)
    pdf.drawString(left, height - 62, "AUDITION COMMAND CENTER")
    pdf.setFillColor(muted); pdf.setFont("Helvetica", 11)
    pdf.drawString(left, height - 82, "What the actor should play, protect, and avoid in the room.")
    grid_y = height - 140
    col_w = (usable_width - 18) / 2
    row_h = 170
    data_cards = [
        ("Casting Read", _as_list(intelligence.get("casting_read"))),
        ("Playable Tactics", _as_list(intelligence.get("playable_tactics"))),
        ("Emotional Triggers", _as_list(intelligence.get("emotional_triggers"))),
        ("Danger Zones", _as_list(intelligence.get("danger_zones"))),
    ]
    for idx, (label, vals) in enumerate(data_cards):
        x = left + (idx % 2) * (col_w + 18)
        yy = grid_y - (idx // 2) * (row_h + 24)
        _draw_card(pdf, x, yy, col_w, row_h, label, vals, gold, panel, white, muted)
    _footer(pdf, width, 2); pdf.showPage()

    _page_bg(pdf, width, height, charcoal, gold)
    pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 25)
    pdf.drawString(left, height - 62, "TAPE ROOM STRATEGY")
    pdf.setFillColor(muted); pdf.setFont("Helvetica", 11)
    pdf.drawString(left, height - 82, "A practical pass for self-tape, reader work, and performance choices.")
    _draw_card(pdf, left, height - 130, col_w, 215, "Memorization Beats", _as_list(intelligence.get("memorization_beats")), gold, panel, white, muted)
    _draw_card(pdf, left + col_w + 18, height - 130, col_w, 215, "Reader Chemistry", _as_list(intelligence.get("reader_chemistry")), gold, panel, white, muted)
    _draw_card(pdf, left, height - 375, usable_width, 185, "Look / Presence", _as_list(intelligence.get("look_presence")), gold, panel, white, muted)
    _footer(pdf, width, 3); pdf.showPage()

    _page_bg(pdf, width, height, charcoal, gold)
    page_no = 4
    y = height - 62
    pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 25)
    pdf.drawString(left, y, "BEAT PATTERN BREAKDOWN")
    y -= 26
    pdf.setFillColor(muted); pdf.setFont("Helvetica", 10)
    pdf.drawString(left, y, f"{len(beats)} beats grouped by type. Each group shows coaching and 3 pulled scenes.")
    y -= 22
    if not beats:
        _draw_card(pdf, left, y, usable_width, 140, "No matching dialogue found", ["Try entering the character name exactly as it appears in the script."], gold, panel, white, muted)
        _footer(pdf, width, page_no); pdf.save(); return output_path
    groups = group_beats_by_type(beats)
    for grp in groups:
        # header card height: label + count + pages + coaching = ~110, plus up to 3 sample cards ~80 each
        header_h = 110
        sample_h = 82
        total_h = header_h + len(grp["samples"]) * (sample_h + 8)
        if y - total_h < 54:
            _footer(pdf, width, page_no); pdf.showPage(); page_no += 1
            _page_bg(pdf, width, height, charcoal, gold)
            y = height - 54
            pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 20)
            pdf.drawString(left, y, "BEAT PATTERN BREAKDOWN")
            y -= 34
        page_range = f"{grp['pages'][0]} – {grp['pages'][-1]}" if len(grp['pages']) > 1 else grp['pages'][0] if grp['pages'] else ""
        header_lines = [
            f"{grp['count']} beat{'s' if grp['count'] != 1 else ''}  ·  {page_range}",
            grp["coaching"],
        ]
        _draw_card(pdf, left, y, usable_width, header_h, grp["beat_type"].upper(), header_lines, gold, panel, white, muted)
        y -= header_h + 8
        for sample in grp["samples"]:
            if y - sample_h < 54:
                _footer(pdf, width, page_no); pdf.showPage(); page_no += 1
                _page_bg(pdf, width, height, charcoal, gold)
                y = height - 54
            scene_label = sample.scene_heading if sample.scene_heading and sample.scene_heading != "SCENE NOT DETECTED" else sample.reference
            slines = [f"{scene_label}", f'"{sample.dialogue[:200]}"']
            _draw_card(pdf, left + 20, y, usable_width - 20, sample_h, f"↳  {sample.reference}", slines, muted, charcoal, white, muted)
            y -= sample_h + 8
        y -= 14
    _footer(pdf, width, page_no); pdf.showPage(); page_no += 1

    _page_bg(pdf, width, height, charcoal, gold)
    pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 25)
    pdf.drawString(left, height - 62, "FINAL AUDITION CHECKLIST")
    checklist = [
        "Lead with the objective, not the emotion.",
        "Protect listening beats; that is where the role breathes.",
        "Choose one clean physical life for the character and keep it consistent.",
        "Let pressure alter pace before it alters volume.",
        "Check framing, sound, file name, and instructions before upload.",
    ]
    _draw_card(pdf, left, height - 115, usable_width, 250, "Before You Send", checklist, gold, panel, white, muted)
    _footer(pdf, width, page_no)
    pdf.save()
    return output_path



# ── MODE 2: BOOKED ROLE PREP ─────────────────────────────────────────────────

_CONTINUITY_NOTES: Dict[str, str] = {
    "Reveal Something True":    "What the character reveals here must carry through every subsequent scene. Track the weight of exposure.",
    "Make a Plea":              "The character is exposed here. Track the moment the need overcomes the defense.",
    "Offer Comfort":            "The role is giving something away. Track the cost so it reads as real, not performed.",
    "Assert Identity":          "This declaration anchors the role. Every later scene should echo back to this moment.",
    "Negotiate":                "The character is thinking ahead. Let each offer cost them something or it feels free.",
    "Challenge":                "The character refuses to accept the other person's reality. Keep the refusal grounded.",
    "Protect a Secret":         "What's being concealed must remain consistent — never let the audience forget it's there.",
    "Deliver a Warning":        "The consequence stated here is a promise. If the character doesn't follow through later, the warning felt hollow.",
    "Express Threat":           "The level of menace established here is the ceiling for every threat that follows.",
    "Pressure for Information": "Track what the character learns here and let that new information change the next beat.",
    "Control the Room":         "This is a control beat. Keep the body and pace consistent so the authority feels earned.",
    "Set a Boundary":           "This is where the line gets drawn. Play the clarity, not the anger.",
    "Apply Pressure":           "The role is leaning in here. The scene changes because the character chooses to press.",
    "Read the Situation":       "Track what the character now knows after this beat. Every subsequent scene inherits this new information.",
    "Share Intelligence":       "Protect what the character chose NOT to share here — that's as important as what they did reveal.",
    "Test and Probe":           "Track what the character learned from the reaction. The probe is only useful if they carry the read forward.",
    "Navigate Danger":          "Physical state continuity matters here — injuries, exhaustion, adrenaline. Track what the body carries out of these scenes.",
    "Reset and Move Forward":   "This beat shifts the energy. Let it feel like a clean redirect, not a full emotional reset.",
    "Hold Authority":           "This is the baseline control state. Keep it textured so it does not flatten.",
}
_DEFAULT_CONTINUITY = "Protect continuity first. Let pressure change pace and patience while core identity stays recognizable."


def build_actor_booked_pdf(script_text: str, character_name: str, output_path: str | Path, brain_data: Optional[Dict] = None) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    beats = extract_beats(script_text, character_name)
    brain_data = brain_data or {}

    pdf = canvas.Canvas(str(output_path), pagesize=LETTER)
    pdf.setTitle(f"{character_name.title()} — Booked Role V2")
    width, height = LETTER
    left, right = 42, width - 42
    usable_width = right - left

    charcoal = colors.HexColor("#111111")
    panel = colors.HexColor("#1b1f23")
    gold = colors.HexColor("#f0c15d")
    white = colors.white
    muted = colors.HexColor("#d8d8d8")

    title = _project_title(brain_data)
    world = _world_value(brain_data)
    tone = _safe(brain_data.get("tone"), "")
    intelligence = _actor_ai_json(character_name, title, "booked", brain_data, beats)
    image_path = _find_actor_report_image(brain_data, "actor_booked", character_name, title)
    scene_count = len(_unique_scenes(beats)) or 1

    # Save JSON for HTML report page
    try:
        json_path = output_path.with_suffix(".json")
        groups = group_beats_by_type(beats)
        beat_groups_data = [
            {
                "beat_type": g["beat_type"],
                "label": g["label"],
                "coaching": g["coaching"],
                "count": g["count"],
                "pages": g["pages"],
                "samples": [
                    {
                        "reference": s.reference,
                        "scene_heading": s.scene_heading,
                        "dialogue": s.dialogue[:300],
                    }
                    for s in g["samples"]
                ],
            }
            for g in groups
        ]
        set_ready = _as_list(brain_data.get("set_ready_checklist"), [
            "Know the scene pressure level before the first take.",
            "Track what changed from the previous scene.",
            "Protect body language and listening continuity.",
            "Mark where status rises, slips, or resets.",
            "Keep novelty second to continuity.",
        ])
        json_path.write_text(json.dumps({
            "character_name": character_name,
            "title": title,
            "tone": _safe(brain_data.get("tone"), ""),
            "world": world,
            "genre": _safe(brain_data.get("genre"), ""),
            "beat_count": len(beats),
            "scene_count": scene_count,
            "intelligence": intelligence,
            "beat_groups": beat_groups_data,
            "set_ready_checklist": set_ready,
        }, indent=2), encoding="utf-8")
    except Exception:
        pass

    _page_bg(pdf, width, height, charcoal, gold)
    pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 15); pdf.drawString(left, height - 54, "BOOKED ROLE REPORT")
    pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 38); pdf.drawString(left, height - 100, character_name.upper()[:24])
    pdf.setFillColor(muted); pdf.setFont("Helvetica-Bold", 14); pdf.drawString(left, height - 126, title.upper()[:42])
    pdf.setStrokeColor(gold); pdf.line(left, height - 152, right, height - 152)
    _draw_cover_image(pdf, image_path, left, height - 390, usable_width, 180, gold)
    summary = _safe(intelligence.get("summary"), _fallback_booked_snapshot(character_name, beats))
    lines = simpleSplit(summary, "Helvetica-Bold", 11, usable_width - 36)
    box_h = max(96, len(lines)*14 + 38)
    y = height - 430
    pdf.setFillColor(panel); pdf.roundRect(left, y - box_h, usable_width, box_h, 12, stroke=0, fill=1)
    pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 9); pdf.drawString(left + 14, y - 20, "FULL ROLE SNAPSHOT")
    _draw_lines(pdf, lines, left + 14, y - 40, 14, "Helvetica-Bold", 11, white)
    card_y = y - box_h - 42
    card_w = (usable_width - 24) / 3
    for i, (label, vals) in enumerate([
        ("BEATS", [f"{len(beats)} speaking beats"]),
        ("WORLD", [world]),
        ("TONE", [tone[:28] if tone else "—"]),
    ]):
        _draw_card(pdf, left + i*(card_w+12), card_y, card_w, 86, label, vals, gold, panel, white, muted)
    _footer(pdf, width, 1); pdf.showPage()

    _page_bg(pdf, width, height, charcoal, gold)
    pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 25); pdf.drawString(left, height - 62, "ROLE CONTINUITY CENTER")
    pdf.setFillColor(muted); pdf.setFont("Helvetica", 11); pdf.drawString(left, height - 82, "What must stay consistent across scenes, takes, and shooting days.")
    col_w = (usable_width - 18) / 2
    row_h = 176
    data_cards = [
        ("Booked Continuity", _as_list(intelligence.get("booked_continuity"))),
        ("Scene Priorities", _as_list(intelligence.get("scene_priorities"))),
        ("Emotional Triggers", _as_list(intelligence.get("emotional_triggers"))),
        ("Look / Behavior", _as_list(intelligence.get("look_presence"))),
    ]
    grid_y = height - 140
    for idx, (label, vals) in enumerate(data_cards):
        x = left + (idx % 2)*(col_w+18)
        yy = grid_y - (idx//2)*(row_h+24)
        _draw_card(pdf, x, yy, col_w, row_h, label, vals, gold, panel, white, muted)
    _footer(pdf, width, 2); pdf.showPage()

    _page_bg(pdf, width, height, charcoal, gold)
    page_no = 3
    y = height - 62
    pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 25); pdf.drawString(left, y, "SCENE JOURNEY MAP")
    y -= 26
    pdf.setFillColor(muted); pdf.setFont("Helvetica", 10)
    pdf.drawString(left, y, f"{len(beats)} beats grouped by type. Coaching note + 3 pulled scenes per pattern.")
    y -= 22
    if not beats:
        _draw_card(pdf, left, y, usable_width, 140, "No matching dialogue found", ["Try entering the character name exactly as it appears in the script."], gold, panel, white, muted)
        _footer(pdf, width, page_no); pdf.save(); return output_path
    groups = group_beats_by_type(beats)
    for grp in groups:
        header_h = 110
        sample_h = 82
        total_h = header_h + len(grp["samples"]) * (sample_h + 8)
        if y - total_h < 54:
            _footer(pdf, width, page_no); pdf.showPage(); page_no += 1
            _page_bg(pdf, width, height, charcoal, gold)
            y = height - 54
            pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 20)
            pdf.drawString(left, y, "SCENE JOURNEY MAP")
            y -= 34
        page_range = f"{grp['pages'][0]} – {grp['pages'][-1]}" if len(grp['pages']) > 1 else grp['pages'][0] if grp['pages'] else ""
        continuity = _CONTINUITY_NOTES.get(grp["beat_type"], _DEFAULT_CONTINUITY)
        header_lines = [
            f"{grp['count']} beat{'s' if grp['count'] != 1 else ''}  ·  {page_range}",
            grp["coaching"],
            f"Continuity: {continuity}",
        ]
        _draw_card(pdf, left, y, usable_width, header_h + 20, grp["beat_type"].upper(), header_lines, gold, panel, white, muted)
        y -= header_h + 28
        for sample in grp["samples"]:
            if y - sample_h < 54:
                _footer(pdf, width, page_no); pdf.showPage(); page_no += 1
                _page_bg(pdf, width, height, charcoal, gold)
                y = height - 54
            scene_label = sample.scene_heading if sample.scene_heading and sample.scene_heading != "SCENE NOT DETECTED" else sample.reference
            slines = [f"{scene_label}", f'"{sample.dialogue[:200]}"']
            _draw_card(pdf, left + 20, y, usable_width - 20, sample_h, f"↳  {sample.reference}", slines, muted, charcoal, white, muted)
            y -= sample_h + 8
        y -= 14
    _footer(pdf, width, page_no); pdf.showPage(); page_no += 1

    _page_bg(pdf, width, height, charcoal, gold)
    pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 25); pdf.drawString(left, height - 62, "SET-READY CHECKLIST")
    set_ready = _as_list(brain_data.get("set_ready_checklist"), [
        "Know the scene pressure level before the first take.",
        "Track what changed from the previous scene.",
        "Protect body language and listening continuity.",
        "Mark where status rises, slips, or resets.",
        "Keep novelty second to continuity.",
    ])
    _draw_card(pdf, left, height - 115, usable_width, 260, "Before Camera", set_ready, gold, panel, white, muted)
    _footer(pdf, width, page_no)
    pdf.save()
    return output_path



# ── MODE 3: SCRIPT ANALYSIS REPORT ───────────────────────────────────────────

def build_simple_analysis_pdf(report_output: dict, out_path: Path):
    W, H = LETTER
    L, R = 42, W - 42
    UW = R - L

    charcoal = colors.HexColor("#111111")
    panel = colors.HexColor("#1a1a1a")
    gold = colors.HexColor("#f0c15d")
    blue = colors.HexColor("#4C88C7")
    white = colors.white
    muted = colors.HexColor("#cfcfcf")
    soft = colors.HexColor("#8f8f8f")

    title = _safe(report_output.get("title"), "UNTITLED PROJECT")
    genre = _safe(report_output.get("genre") or report_output.get("world"))
    tone = _safe(report_output.get("tone"))
    logline = _safe(report_output.get("logline"))
    synopsis = _safe(report_output.get("synopsis"))
    theme = _safe(report_output.get("theme"))
    world = _safe(report_output.get("world"))
    setting = _safe(report_output.get("setting"))
    time_frame = _safe(report_output.get("time_frame"))
    core = _safe(report_output.get("core_conflict"))
    engine = _safe(report_output.get("story_engine"))
    reversal = _safe(report_output.get("reversal"))
    lead = _safe(report_output.get("lead_character") or report_output.get("protagonist"))
    protagonist_sum = _safe(report_output.get("protagonist_summary"))
    char_leverage = _safe(report_output.get("character_leverage"))
    top_chars_raw = (report_output.get("character_analysis") or {}).get("top_characters", [])
    if not top_chars_raw:
        top_chars_raw = report_output.get("characters") or []
    top_chars = _clean_characters(top_chars_raw)

    comparables_raw = report_output.get("tone_comparables") or []
    if not comparables_raw:
        comparables_raw = [c.get("title") for c in (report_output.get("comparable_films") or []) if isinstance(c, dict)]
    comparables = _clean_characters(comparables_raw)

    market_projections = report_output.get("market_projections") or {}
    strength = report_output.get("strength_index") or {}
    commercial = _safe(report_output.get("commercial_positioning"))
    audience = _clean_characters(report_output.get("audience_profile") or [])
    packaging = _safe(report_output.get("packaging_potential"))
    executive_summary = _safe(report_output.get("executive_summary"))
    summary_note = _safe(report_output.get("summary_note"))
    story_insights = report_output.get("story_insights") or []
    rewrite_priorities = report_output.get("rewrite_priorities") or report_output.get("next_draft_priorities") or []
    strengths_list = report_output.get("strengths") or []
    risks_list = report_output.get("risks") or report_output.get("development_risks") or []
    budget_lane = _safe(market_projections.get("budget_range") or market_projections.get("estimated_budget_tier") or report_output.get("budget_lane") or report_output.get("estimated_budget"))
    streamer_fit = _safe(market_projections.get("streamer_fit") or market_projections.get("distribution_angle") or report_output.get("streamer_fit"))
    awards_lane = _safe(market_projections.get("awards_lane") or market_projections.get("awards_potential") or report_output.get("awards_lane"))
    franchise = _safe(market_projections.get("franchise_potential") or report_output.get("franchise_potential"))
    sales_hook = _safe(market_projections.get("sales_hook"))

    actor_objective = _safe(report_output.get("actor_objective"))
    playable_tactics = _clean_characters(report_output.get("playable_tactics") or [])
    emotional_triggers = _clean_characters(report_output.get("emotional_triggers") or [])
    audition_danger_zones = _clean_characters(report_output.get("audition_danger_zones") or [])
    reader_chemistry_tips = [str(x).strip() for x in (report_output.get("reader_chemistry_tips") or []) if str(x).strip()]
    memorization_beats = _clean_characters(report_output.get("memorization_beats") or [])
    role_arc_map = _clean_characters(report_output.get("role_arc_map") or [])
    pressure_ladder = _clean_characters(report_output.get("pressure_ladder") or [])
    emotional_continuity = [str(x).strip() for x in (report_output.get("emotional_continuity") or []) if str(x).strip()]
    costume_behavior_clues = [str(x).strip() for x in (report_output.get("costume_behavior_clues") or []) if str(x).strip()]
    set_ready_checklist = [str(x).strip() for x in (report_output.get("set_ready_checklist") or []) if str(x).strip()]
    relationship_map = report_output.get("relationship_leverage_map") or []
    image_plan = report_output.get("image_plan") or []

    layout_strategy = report_output.get("layout_strategy") or {}
    slide_blueprint = report_output.get("slide_blueprint") or {}
    document_layouts = report_output.get("document_layouts") or {}
    analysis_layout = document_layouts.get("analysis_report") or {}

    if not executive_summary:
        executive_summary = _smart_summary("analysis", title, "", logline, synopsis, [], extra=genre)

    if not strengths_list:
        strengths_list = [s for s in [theme, engine, commercial, packaging, actor_objective] if s][:5]
    if not rewrite_priorities:
        rewrite_priorities = [
            "Clarify the protagonist's pressure line even further.",
            "Make the reversal land with maximum clarity.",
            "Sharpen supporting roles so they do more than serve plot.",
        ]
    if not story_insights:
        story_insights = [
            f"Lead role currently reads strongest through {lead or 'the protagonist'}.",
            "The reversal is doing real structural work and should stay visible in the pitch.",
            "The project feels strongest when the audience is tracking pressure, not exposition.",
        ]

    score_parts = []
    for key, label in [("concept", "Concept"), ("character", "Character"), ("marketability", "Market"), ("originality", "Originality")]:
        val = strength.get(key)
        if val:
            score_parts.append(f"{label}: {val}/10")
    strength_line = "  ·  ".join(score_parts)

    comparable_details = []
    for comp in (report_output.get("comparable_films") or []):
        if isinstance(comp, dict):
            title_part = str(comp.get("title") or "").strip()
            why_part = str(comp.get("why") or "").strip()
            box_part = str(comp.get("box_office") or "").strip()
            pieces = [p for p in [title_part, why_part, box_part] if p]
            if pieces:
                comparable_details.append(" — ".join(pieces[:2]) if len(pieces) < 3 else f"{title_part} — {why_part} ({box_part})")

    relationship_lines = []
    for row in relationship_map:
        if isinstance(row, dict):
            character = str(row.get("character") or "").strip()
            dynamic = str(row.get("dynamic") or "").strip()
            function = str(row.get("function") or "").strip()
            parts = [p for p in [character, dynamic, function] if p]
            if parts:
                relationship_lines.append(" — ".join(parts[:2]) if len(parts) < 3 else f"{character} — {dynamic} — {function}")

    image_summary = []
    for item in image_plan[:5]:
        if isinstance(item, dict):
            slide_title = str(item.get("slide_title") or item.get("slide_number") or "").strip()
            visual_family = str(item.get("visual_family") or "").strip()
            query = str(item.get("image_query") or "").strip()
            parts = [slide_title]
            if visual_family:
                parts.append(visual_family)
            if query:
                parts.append(query[:90] + ("…" if len(query) > 90 else ""))
            image_summary.append(" — ".join([p for p in parts if p]))

    cover_image = _find_actor_report_image(report_output, "analysis", lead or title, title)

    pdf = canvas.Canvas(str(out_path), pagesize=LETTER)
    pdf.setTitle(f"{title} — Script Analysis Report")

    pdf.setFillColor(charcoal)
    pdf.rect(0, 0, W, H, stroke=0, fill=1)
    pdf.setFillColor(gold)
    pdf.rect(0, H - 6, W, 6, stroke=0, fill=1)
    pdf.setFillColor(soft); pdf.setFont("Helvetica", 9)
    pdf.drawString(L, H - 30, "EVOLUM  ·  DEVELOPUM AI ENGINE")
    pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 40)
    pdf.drawString(L, H - 80, "SCRIPT")
    pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(L, H - 116, "ANALYSIS REPORT")
    pdf.setStrokeColor(gold); pdf.line(L, H - 132, R, H - 132)
    pdf.setFillColor(soft); pdf.setFont("Helvetica", 10)
    pdf.drawString(L, H - 154, "PROJECT")
    pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 20)
    ty = H - 174
    for tl in simpleSplit(title.upper(), "Helvetica-Bold", 20, UW):
        pdf.drawString(L, ty, tl); ty -= 26
    cy = ty - 10
    meta = "  ·  ".join([p for p in [genre, tone, time_frame] if p])
    if meta:
        pdf.setFillColor(muted); pdf.setFont("Helvetica", 11)
        for ml in simpleSplit(meta, "Helvetica", 11, UW):
            pdf.drawString(L, cy, ml); cy -= 13
        cy -= 4

    summary_lines = simpleSplit(executive_summary, "Helvetica", 11, UW - 32)
    box_h = len(summary_lines) * 15 + 30
    pdf.setFillColor(panel)
    pdf.roundRect(L, cy - box_h + 10, UW, box_h, 12, stroke=0, fill=1)
    pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(L + 16, cy - 6, "EXECUTIVE SNAPSHOT")
    sy = cy - 22
    pdf.setFillColor(white); pdf.setFont("Helvetica", 11)
    for line in summary_lines:
        pdf.drawString(L + 16, sy, line); sy -= 15
    cy -= box_h + 10

    contents = [
        "Executive snapshot",
        "Story engine",
        "Market position",
        "Actor-ready intelligence",
        "Relationship leverage",
        "Visual strategy",
    ]
    pdf.setFillColor(soft); pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(L, cy, "THIS REPORT INCLUDES"); cy -= 14
    for item in contents:
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 10); pdf.drawString(L, cy, "—")
        pdf.setFillColor(muted); pdf.setFont("Helvetica", 10); pdf.drawString(L + 16, cy, item); cy -= 14

    if cy > 80:
        _draw_cover_image(pdf, cover_image, L, max(54, cy - 140), UW, min(120, cy - 60), gold)

    pdf.setFillColor(gold)
    pdf.rect(0, 0, W, 4, stroke=0, fill=1)
    _footer(pdf, W, 1)
    pdf.showPage()

    pdf.setFillColor(charcoal)
    pdf.rect(0, 0, W, H, stroke=0, fill=1)
    ctx = _PDFCtx(pdf, W, H, L, UW, charcoal, gold, blue, white, muted, soft, panel)

    ctx.section_header("Story Engine", "The plain-English version of what is driving the movie.")
    if logline:
        ctx.info_row("Logline", logline)
    if synopsis:
        ctx.info_row("Synopsis", synopsis)
    if lead:
        ctx.info_row("Lead", lead)
    if world:
        ctx.info_row("World", world)
    if setting:
        ctx.info_row("Setting", setting)
    if core:
        ctx.info_row("Core conflict", core)
    if engine:
        ctx.info_row("Story engine", engine)
    if reversal:
        ctx.info_row("Reversal", reversal)
    if theme:
        ctx.info_row("Theme", theme)
    ctx.y -= 8

    ctx.section_header("Character Value", "Why the roles matter and what the cast landscape looks like.")
    if protagonist_sum:
        ctx.info_row("Lead role read", protagonist_sum)
    if char_leverage:
        ctx.info_row("Character leverage", char_leverage)
    if top_chars:
        ctx.info_row("Top characters", ", ".join(top_chars[:10]))
    if role_arc_map:
        ctx.info_row("Role arc map", "  →  ".join(role_arc_map[:6]))
    ctx.y -= 8

    ctx.section_header("Market Position", "The commercial lane this project appears to be in right now.")
    if comparables:
        ctx.info_row("Comparable titles", ", ".join(comparables[:6]))
    if audience:
        ctx.info_row("Audience profile", ", ".join(audience[:6]))
    if budget_lane:
        ctx.info_row("Budget lane", budget_lane)
    if streamer_fit:
        ctx.info_row("Distribution / buyer fit", streamer_fit)
    if awards_lane:
        ctx.info_row("Awards lane", awards_lane)
    if commercial:
        ctx.info_row("Commercial positioning", commercial)
    if packaging:
        ctx.info_row("Packaging potential", packaging)
    if franchise:
        ctx.info_row("Franchise potential", franchise)
    if strength_line:
        ctx.info_row("Strength index", strength_line)

    ctx.new_page()
    ctx.section_header("Executive & Producer Gold", "The material already carries stronger development-facing value than a basic summary report shows.")
    if executive_summary:
        ctx.info_row("Executive summary", executive_summary)
    if sales_hook:
        ctx.info_row("Sales hook", sales_hook)
    if comparable_details:
        ctx.bullet_list(comparable_details[:5], bullet_color=gold)
    if market_projections:
        projection_lines = []
        for label, key in [
            ("Budget", "estimated_budget_tier"),
            ("Distribution", "distribution_angle"),
            ("Awards", "awards_potential"),
            ("Audience reach", "audience_reach"),
            ("Franchise", "franchise_potential"),
        ]:
            val = _safe(market_projections.get(key))
            if val:
                projection_lines.append(f"{label}: {val}")
        if projection_lines:
            ctx.bullet_list(projection_lines[:6], bullet_color=blue)

    ctx.section_header("Actor Intelligence", "This is where the report starts behaving like an actual prep tool.")
    if actor_objective:
        ctx.info_row("Actor objective", actor_objective)
    if playable_tactics:
        ctx.info_row("Playable tactics", ", ".join(playable_tactics[:8]))
    if emotional_triggers:
        ctx.info_row("Emotional triggers", ", ".join(emotional_triggers[:8]))
    if memorization_beats:
        ctx.info_row("Memorization beats", "  ·  ".join(memorization_beats[:8]))
    if pressure_ladder:
        ctx.info_row("Pressure ladder", "  →  ".join(pressure_ladder[:8]))
    if audition_danger_zones:
        ctx.bullet_list(audition_danger_zones[:6], bullet_color=gold)

    ctx.new_page()
    ctx.section_header("Reader & Set Readiness", "The brain is already creating practical prep value for performers and directors.")
    if reader_chemistry_tips:
        ctx.bullet_list(reader_chemistry_tips[:6], bullet_color=blue)
    if emotional_continuity:
        ctx.section_header("Emotional continuity")
        ctx.bullet_list(emotional_continuity[:6], bullet_color=gold)
    if costume_behavior_clues:
        ctx.section_header("Costume & behavior clues")
        ctx.bullet_list(costume_behavior_clues[:5], bullet_color=blue)
    if set_ready_checklist:
        ctx.section_header("Set-ready checklist")
        ctx.bullet_list(set_ready_checklist[:6], bullet_color=gold)
    if relationship_lines:
        ctx.section_header("Relationship leverage map")
        ctx.bullet_list(relationship_lines[:6], bullet_color=blue)

    ctx.new_page()
    ctx.section_header("What Is Working", "The report should not just criticize. It should identify value.")
    ctx.bullet_list([str(x) for x in strengths_list[:8] if str(x).strip()] or [
        "The central pressure line is easy to pitch.",
        "The material has a clean story engine and a usable reversal.",
        "The lead role appears to carry real performance opportunity.",
    ], bullet_color=gold)
    ctx.y -= 8

    ctx.section_header("Rewrite Priorities", "Where the next draft can create the fastest value.")
    ctx.bullet_list([str(x) for x in rewrite_priorities[:8] if str(x).strip()], bullet_color=blue)
    ctx.y -= 8

    if risks_list:
        ctx.section_header("Things To Watch")
        ctx.bullet_list([str(x) for x in risks_list[:8] if str(x).strip()], bullet_color=gold)
        ctx.y -= 8

    ctx.section_header("Visual & Presentation Strategy", "This is the part of the brain that can feed decks, reports, and creative direction.")
    if layout_strategy:
        strat = []
        for k in ["layout_style", "text_density", "image_priority", "pacing", "visual_energy", "headline_style"]:
            v = _safe(layout_strategy.get(k))
            if v:
                strat.append(f"{k.replace('_', ' ').title()}: {v}")
        if strat:
            ctx.bullet_list(strat[:8], bullet_color=gold)
    if slide_blueprint:
        blueprint = []
        for k in ["recommended_slide_count", "opening_style", "mid_deck_focus", "closing_style"]:
            v = _safe(slide_blueprint.get(k))
            if v:
                blueprint.append(f"{k.replace('_', ' ').title()}: {v}")
        if blueprint:
            ctx.bullet_list(blueprint[:6], bullet_color=blue)
    if analysis_layout:
        layout_lines = []
        for k in ["layout_family", "cover_style", "chart_style", "section_density"]:
            v = _safe(analysis_layout.get(k))
            if v:
                layout_lines.append(f"{k.replace('_', ' ').title()}: {v}")
        if layout_lines:
            ctx.bullet_list(layout_lines[:6], bullet_color=gold)
    if image_summary:
        ctx.section_header("Image-plan highlights")
        ctx.bullet_list(image_summary[:5], bullet_color=blue)

    ctx.section_header("Why This Project Matters", "The part a novice user, creative producer, or investor can understand quickly.")
    ctx.bullet_list([str(x) for x in story_insights[:8] if str(x).strip()], bullet_color=gold)
    if summary_note:
        ctx.info_row("Final note", summary_note)

    ctx.methodology_box()
    _footer(pdf, W, ctx.page_no)
    pdf.save()

#========== DAI DECK PIPELINE ==============
def run_deck_pipeline(script_path=None, project_id=None, user_id=None):
    """
    Main DAI deck lane.
    Central wrapper for deck generation flow.
    Safe first bridge step.
    """

    import subprocess
    import os
    from pathlib import Path

    base_dir = Path(__file__).resolve().parent

    cmd = ["python3", str(base_dir / "run_pipeline.py")]

    env = os.environ.copy()

    if script_path:
        env["DAI_SCRIPT_PATH"] = str(script_path)

    if project_id:
        env["DAI_PROJECT_ID"] = str(project_id)

    if user_id:
        env["DAI_USER_ID"] = str(user_id)

    result = subprocess.run(
        cmd,
        cwd=str(base_dir),
        env=env,
        capture_output=True,
        text=True
    )

    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }

