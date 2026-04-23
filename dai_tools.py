from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas


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
    return s.startswith("INT.") or s.startswith("EXT.") or s.startswith("INT ") or s.startswith("EXT ")


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


def _infer_beat(dialogue: str, scene_heading: str) -> Tuple[str, str, str]:
    lower = dialogue.strip().lower()

    if any(k in lower for k in ["who", "what", "where", "why", "how"]):
        return (
            "Pressure for Information",
            "The character is trying to get clarity while still keeping leverage.",
            "Ask like it matters. Curiosity is not enough here.",
        )
    if any(k in lower for k in ["calm down", "sit down", "listen", "hold on", "wait"]):
        return (
            "Control the Room",
            "The character is slowing the chaos down and forcing the scene back under control.",
            "Use calm authority. The power is in the certainty, not the volume.",
        )
    if any(k in lower for k in ["don't", "do not", "can't", "cannot", "won't", "stop"]):
        return (
            "Set a Boundary",
            "The character is drawing a line and making the other person feel the limit.",
            "Keep it clear and definite. This beat lands when the line feels real.",
        )
    if any(k in lower for k in ["good", "okay", "alright", "cool"]):
        return (
            "Reset and Move Forward",
            "The character absorbs the moment and redirects the energy instead of sitting in it.",
            "Treat it like a pivot, not relief.",
        )
    if scene_heading and ("OFFICE" in scene_heading.upper() or "INTERROGATION" in scene_heading.upper()):
        return (
            "Apply Pressure",
            "The character is reading the other person and leaning in for leverage.",
            "Push with intelligence. Let the pressure come from focus, not force.",
        )
    return (
        "Hold Authority",
        "The character is managing the scene from a position of control.",
        "Stay grounded and specific. Quiet command usually wins this beat.",
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
                    beat, subtext, playable = _infer_beat(dialogue, current_scene)
                    beats.append(
                        BeatEntry(
                            reference=f"Page {page_no}",
                            scene_heading=current_scene,
                            cue_line=line,
                            dialogue=dialogue,
                            beat=beat,
                            subtext=subtext,
                            playable_note=playable,
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
    "Pressure for Information": ["Push for Answers", "Get the Truth", "Lean In for Clarity"],
    "Control the Room": ["Take Control", "Steady the Room", "Own the Moment"],
    "Set a Boundary": ["Draw the Line", "Hold Your Ground", "Make the Limit Clear"],
    "Reset and Move Forward": ["Shift the Energy", "Reset and Move On", "Pivot Cleanly"],
    "Apply Pressure": ["Turn Up the Pressure", "Lean In", "Press the Point"],
    "Hold Authority": ["Stay in Command", "Lead Quietly", "Keep Control"],
}


def _friendly_beat_title(beat: str, index: int) -> str:
    options = _FRIENDLY_BEAT_TITLES.get(beat, [beat])
    return options[(index - 1) % len(options)]


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


# ── MODE 1: AUDITION QUICKPACK ───────────────────────────────────────────────

def build_actor_prep_pdf(script_text: str, character_name: str, output_path: str | Path, brain_data: Optional[Dict] = None) -> Path:
    output_path = Path(output_path)
    beats = extract_beats(script_text, character_name)
    brain_data = brain_data or {}

    pdf = canvas.Canvas(str(output_path), pagesize=LETTER)
    pdf.setTitle(f"{character_name.title()} — Audition Prep Packet")
    width, height = LETTER
    left = 42
    right = width - 42
    usable_width = right - left

    charcoal = colors.HexColor("#111111")
    panel = colors.HexColor("#1a1a1a")
    gold = colors.HexColor("#f0c15d")
    blue = colors.HexColor("#52a8ff")
    white = colors.white
    muted = colors.HexColor("#cfcfcf")
    soft = colors.HexColor("#8f8f8f")

    tone = _safe(brain_data.get("tone"))
    logline = _safe(brain_data.get("logline"))
    synopsis = _safe(brain_data.get("synopsis"))
    actor_objective = _safe(brain_data.get("actor_objective"))
    danger_zones = brain_data.get("audition_danger_zones") or []
    tactics = brain_data.get("playable_tactics") or []
    triggers = brain_data.get("emotional_triggers") or []
    chemistry_tips = brain_data.get("reader_chemistry_tips") or []
    casting_tests = brain_data.get("casting_tests") or []
    role_essence = _safe(brain_data.get("role_essence"))
    ai_snapshot = _smart_summary("audition", "", character_name, logline, synopsis, beats, extra=role_essence)

    pdf.setFillColor(charcoal)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    pdf.setFillColor(gold)
    pdf.rect(0, height - 6, width, 6, stroke=0, fill=1)
    pdf.setFillColor(soft)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(left, height - 30, "EVOLUM  ·  ACTOR PREPARATION")
    pdf.setFillColor(gold)
    pdf.setFont("Helvetica-Bold", 40)
    pdf.drawString(left, height - 80, "AUDITION")
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(left, height - 116, "QUICKPACK")
    pdf.setStrokeColor(gold)
    pdf.line(left, height - 132, right, height - 132)
    pdf.setFillColor(soft)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, height - 154, "ROLE")
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(left, height - 174, character_name.title())

    cy = height - 202
    beat_label = f"{len(beats)} playable beat{'s' if len(beats) != 1 else ''} detected" if beats else "No beats detected"
    pdf.setFillColor(soft)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, cy, beat_label)
    cy -= 18
    if tone:
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 10)
        for tl in simpleSplit(tone, "Helvetica", 10, usable_width):
            pdf.drawString(left, cy, tl)
            cy -= 12
        cy -= 4

    snap_lines = simpleSplit(ai_snapshot, "Helvetica", 11, usable_width - 32)
    snap_h = len(snap_lines) * 15 + 30
    pdf.setFillColor(panel)
    pdf.roundRect(left, cy - snap_h + 10, usable_width, snap_h, 12, stroke=0, fill=1)
    pdf.setFillColor(gold)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(left + 16, cy - 6, "60-SECOND ROLE SNAPSHOT")
    sy = cy - 22
    pdf.setFillColor(white)
    pdf.setFont("Helvetica", 11)
    for line in snap_lines:
        pdf.drawString(left + 16, sy, line)
        sy -= 15
    cy -= snap_h + 10

    contents = [
        "Role snapshot",
        "What casting is likely testing",
        "What the sides are telling you",
        f"Beat breakdown ({len(beats)} beats)",
        "Self-tape checklist",
    ]
    pdf.setFillColor(soft); pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(left, cy, "THIS PACKET INCLUDES"); cy -= 14
    for item in contents:
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, cy, "—")
        pdf.setFillColor(muted); pdf.setFont("Helvetica", 10)
        pdf.drawString(left + 16, cy, item); cy -= 14

    pdf.setFillColor(gold)
    pdf.rect(0, 0, width, 4, stroke=0, fill=1)
    _footer(pdf, width, 1)
    pdf.showPage()

    pdf.setFillColor(charcoal)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    ctx = _PDFCtx(pdf, width, height, left, usable_width, charcoal, gold, blue, white, muted, soft, panel)

    if not beats:
        ctx.section_header("No matching dialogue found")
        ctx.text_block("The extraction did not detect dialogue for this role. Try entering the character name exactly as it appears in the script.")
        ctx.methodology_box()
        _footer(pdf, width, ctx.page_no)
        pdf.save()
        return output_path

    ctx.section_header("What Casting Is Likely Testing", "Plain English notes for actors on a deadline.")
    tests = casting_tests if casting_tests else [
        "Can you establish the role quickly without over-explaining it?",
        "Can you hold pressure without forcing the performance?",
        "Can you let pauses, reactions, and listening do some of the work?",
    ]
    ctx.bullet_list(tests, bullet_color=blue)
    ctx.y -= 8

    ctx.section_header("What the Sides Are Really Telling You", "This is the conversational read of the moment.")
    if actor_objective:
        ctx.info_row("Main objective", actor_objective)
    if role_essence:
        ctx.info_row("Role essence", role_essence)
    if triggers:
        ctx.info_row("What gets under the skin", ", ".join(map(str, triggers)))
    if tactics:
        ctx.info_row("Useful playable choices", ", ".join(map(str, tactics)))
    if chemistry_tips:
        ctx.bullet_list(chemistry_tips, bullet_color=gold)
    ctx.y -= 8

    ctx.new_page()
    ctx.section_header("Beat Breakdown", f"All {len(beats)} detected beat{'s' if len(beats) != 1 else ''} from the current sides.")
    for idx, beat in enumerate(beats, start=1):
        title = _friendly_beat_title(beat.beat, idx)
        d_lines = _split_lines(pdf, f"{beat.cue_line}: {beat.dialogue}", "Helvetica", 9, usable_width - 28)
        n_lines = _split_lines(pdf, beat.playable_note, "Helvetica", 9, usable_width - 28)
        card_h = max(46 + len(d_lines) * 11 + len(n_lines) * 11 + 14, 104)
        ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, card_h + 10, ctx.page_no, charcoal)
        pdf.setFillColor(panel)
        pdf.roundRect(left, ctx.y - card_h + 10, usable_width, card_h, 12, stroke=0, fill=1)
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(left + 14, ctx.y - 8, f"Beat {idx} — {title}")
        pdf.setFillColor(soft); pdf.setFont("Helvetica", 9)
        pdf.drawString(left + 14, ctx.y - 22, f"{beat.reference} | {beat.scene_heading}")
        by = ctx.y - 40
        pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left + 14, by, "Script line"); by -= 12
        by = _draw_lines(pdf, d_lines, left + 14, by, 11, "Helvetica", 9, muted)
        pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left + 14, by - 2, "How to play it"); by -= 14
        _draw_lines(pdf, n_lines, left + 14, by, 11, "Helvetica", 9, muted)
        ctx.y -= card_h + 10

    ctx.section_header("Self-Tape Success Checklist", "Short, practical, and beginner-friendly.")
    ctx.bullet_list([
        "Frame chest-up or mid-shot unless casting says otherwise.",
        "Pick exact eyeline marks and tape them before recording.",
        "Keep the background clean and the sound easy to understand.",
        "Do not rush the pauses. Let the thought finish before the next line.",
        "Dress in a way that hints at the role without turning it into costume.",
        "Check file name, instructions, and upload deadline before sending.",
    ], bullet_color=gold)
    ctx.methodology_box()
    _footer(pdf, width, ctx.page_no)
    pdf.save()
    return output_path


# ── MODE 2: BOOKED ROLE PREP ─────────────────────────────────────────────────

_CONTINUITY_NOTES: Dict[str, str] = {
    "Pressure for Information": "Track what the character learns here and let that new information change the next beat.",
    "Control the Room": "This is a control beat. Keep the body and pace consistent so the authority feels earned.",
    "Set a Boundary": "This is where the line gets drawn. Play the clarity, not the anger.",
    "Reset and Move Forward": "This beat shifts the energy. Let it feel like a clean redirect, not a full emotional reset.",
    "Apply Pressure": "The role is leaning in here. The scene changes because the character chooses to press.",
    "Hold Authority": "This is the baseline control state. Keep it textured so it does not flatten.",
}
_DEFAULT_CONTINUITY = "Protect continuity first. Let pressure change pace and patience while core identity stays recognizable."


def build_actor_booked_pdf(script_text: str, character_name: str, output_path: str | Path, brain_data: Optional[Dict] = None) -> Path:
    output_path = Path(output_path)
    beats = extract_beats(script_text, character_name)
    brain_data = brain_data or {}

    pdf = canvas.Canvas(str(output_path), pagesize=LETTER)
    pdf.setTitle(f"{character_name.title()} — Full Role Prep")
    width, height = LETTER
    left = 42
    right = width - 42
    usable_width = right - left

    charcoal = colors.HexColor("#111111")
    panel = colors.HexColor("#1a1a1a")
    gold = colors.HexColor("#f0c15d")
    blue = colors.HexColor("#52a8ff")
    white = colors.white
    muted = colors.HexColor("#cfcfcf")
    soft = colors.HexColor("#8f8f8f")

    tone = _safe(brain_data.get("tone"))
    logline = _safe(brain_data.get("logline"))
    synopsis = _safe(brain_data.get("synopsis"))
    actor_objective = _safe(brain_data.get("actor_objective"))
    tactics = brain_data.get("playable_tactics") or []
    triggers = brain_data.get("emotional_triggers") or []
    role_arc = brain_data.get("role_arc_map") or []
    pressure_ladder = brain_data.get("pressure_ladder") or []
    em_continuity = brain_data.get("emotional_continuity") or []
    rel_map = brain_data.get("relationship_leverage_map") or []
    costume_clues = brain_data.get("costume_behavior_clues") or []
    memo_beats = brain_data.get("memorization_beats") or []
    set_checklist = brain_data.get("set_ready_checklist") or []
    relationship_summary = _safe(brain_data.get("relationship_summary"))
    ai_snapshot = _smart_summary("booked", "", character_name, logline, synopsis, beats, extra=relationship_summary)
    scene_count = len(_unique_scenes(beats))

    pdf.setFillColor(charcoal)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    pdf.setFillColor(gold)
    pdf.rect(0, height - 6, width, 6, stroke=0, fill=1)
    pdf.setFillColor(soft)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(left, height - 30, "EVOLUM  ·  ACTOR PREPARATION")
    pdf.setFillColor(gold)
    pdf.setFont("Helvetica-Bold", 40)
    pdf.drawString(left, height - 80, "FULL ROLE")
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(left, height - 116, "PREP")
    pdf.setStrokeColor(gold)
    pdf.line(left, height - 132, right, height - 132)
    pdf.setFillColor(soft)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, height - 154, "ROLE")
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(left, height - 174, character_name.title())

    cy = height - 202
    beat_label = (f"{len(beats)} speaking beat{'s' if len(beats) != 1 else ''} across {scene_count or 1} scene{'s' if (scene_count or 1) != 1 else ''}") if beats else "No beats detected"
    pdf.setFillColor(soft); pdf.setFont("Helvetica", 10)
    pdf.drawString(left, cy, beat_label); cy -= 18
    if tone:
        pdf.setFillColor(muted); pdf.setFont("Helvetica", 10)
        for tl in simpleSplit(tone, "Helvetica", 10, usable_width):
            pdf.drawString(left, cy, tl); cy -= 12
        cy -= 4

    snap_lines = simpleSplit(ai_snapshot, "Helvetica", 11, usable_width - 32)
    snap_h = len(snap_lines) * 15 + 30
    pdf.setFillColor(panel)
    pdf.roundRect(left, cy - snap_h + 10, usable_width, snap_h, 12, stroke=0, fill=1)
    pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(left + 16, cy - 6, "FULL ROLE SNAPSHOT")
    sy = cy - 22
    pdf.setFillColor(white); pdf.setFont("Helvetica", 11)
    for line in snap_lines:
        pdf.drawString(left + 16, sy, line); sy -= 15
    cy -= snap_h + 10

    contents = [
        "Role overview",
        "Actor objective",
        "Role arc & pressure ladder",
        "Relationships & behavior",
        "Physical / costume clues",
        f"Full scene journey ({len(beats)} beats)",
        "Set-ready checklist",
    ]
    pdf.setFillColor(soft); pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(left, cy, "THIS PACKET INCLUDES"); cy -= 14
    for item in contents:
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, cy, "—")
        pdf.setFillColor(muted); pdf.setFont("Helvetica", 10)
        pdf.drawString(left + 16, cy, item); cy -= 14

    pdf.setFillColor(gold)
    pdf.rect(0, 0, width, 4, stroke=0, fill=1)
    _footer(pdf, width, 1)
    pdf.showPage()

    pdf.setFillColor(charcoal)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    ctx = _PDFCtx(pdf, width, height, left, usable_width, charcoal, gold, blue, white, muted, soft, panel)

    if not beats:
        ctx.section_header("No matching dialogue found")
        ctx.text_block("The extraction did not detect dialogue for this role. Try entering the character name exactly as it appears in the script.")
        ctx.methodology_box()
        _footer(pdf, width, ctx.page_no)
        pdf.save()
        return output_path

    ctx.section_header("Actor Objective", "The clearest through-line to protect from scene to scene.")
    if actor_objective:
        ctx.info_row("Main objective", actor_objective)
    else:
        ctx.info_row("Main objective", "Protect the core behavior of the role while pressure changes the pace and tactics.")
    if relationship_summary:
        ctx.info_row("Relationship dynamic", relationship_summary)
    ctx.y -= 8

    if role_arc or pressure_ladder:
        ctx.section_header("Role Arc & Pressure Ladder", "How the role evolves and where the pressure rises.")
        if role_arc:
            ctx.info_row("Arc progression", ", ".join(map(str, role_arc)))
        if pressure_ladder:
            ctx.info_row("Pressure line", ", ".join(map(str, pressure_ladder)))
        ctx.y -= 8

    ctx.section_header("Behavior, Relationships, and Continuity")
    if tactics:
        ctx.info_row("Useful tactics", ", ".join(map(str, tactics)))
    if triggers:
        ctx.info_row("Emotional triggers", ", ".join(map(str, triggers)))
    if em_continuity:
        ctx.bullet_list(em_continuity, bullet_color=gold)
    if rel_map:
        for rel in rel_map:
            char = _safe(rel.get("character"))
            dynamic = _safe(rel.get("dynamic"))
            func = _safe(rel.get("function"))
            if char:
                ctx.info_row(char, "; ".join([p for p in [dynamic, func] if p]))
    if costume_clues:
        ctx.bullet_list(costume_clues, bullet_color=blue)
    if memo_beats:
        ctx.bullet_list(memo_beats, bullet_color=gold)
    ctx.y -= 8

    ctx.new_page()
    ctx.section_header("Full Scene Journey", f"All {len(beats)} detected beat{'s' if len(beats) != 1 else ''} reorganized as role-prep cards.")
    for idx, beat in enumerate(beats, start=1):
        continuity = _CONTINUITY_NOTES.get(beat.beat, _DEFAULT_CONTINUITY)
        title = _friendly_beat_title(beat.beat, idx)
        d_lines = _split_lines(pdf, f"{beat.cue_line}: {beat.dialogue}", "Helvetica", 9, usable_width - 28)
        c_lines = _split_lines(pdf, continuity, "Helvetica", 9, usable_width - 28)
        card_h = max(46 + len(d_lines) * 11 + len(c_lines) * 11 + 14, 104)
        ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, card_h + 10, ctx.page_no, charcoal)
        pdf.setFillColor(panel)
        pdf.roundRect(left, ctx.y - card_h + 10, usable_width, card_h, 12, stroke=0, fill=1)
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(left + 14, ctx.y - 8, f"Scene Beat {idx} — {title}")
        pdf.setFillColor(soft); pdf.setFont("Helvetica", 9)
        pdf.drawString(left + 14, ctx.y - 22, f"{beat.reference} | {beat.scene_heading}")
        by = ctx.y - 40
        pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left + 14, by, "Script line"); by -= 12
        by = _draw_lines(pdf, d_lines, left + 14, by, 11, "Helvetica", 9, muted)
        pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left + 14, by - 2, "Continuity note"); by -= 14
        _draw_lines(pdf, c_lines, left + 14, by, 11, "Helvetica", 9, muted)
        ctx.y -= card_h + 10

    ctx.section_header("Set-Ready Checklist")
    checklist = set_checklist if set_checklist else [
        "Know where the scene sits in the role's pressure line before you play it.",
        "Track whether the character is entering hot, steady, or already compromised.",
        "Hold body language, voice rhythm, and listening behavior consistently across takes.",
        "Mark any scene where the role's pressure clearly rises or drops.",
        "Protect continuity more than novelty.",
    ]
    ctx.bullet_list(checklist, bullet_color=gold)
    ctx.methodology_box()
    _footer(pdf, width, ctx.page_no)
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
    core = _safe(report_output.get("core_conflict"))
    engine = _safe(report_output.get("story_engine"))
    reversal = _safe(report_output.get("reversal"))
    lead = _safe(report_output.get("lead_character") or report_output.get("protagonist"))
    protagonist_sum = _safe(report_output.get("protagonist_summary"))
    char_leverage = _safe(report_output.get("character_leverage"))
    top_chars_raw = (report_output.get("character_analysis") or {}).get("top_characters", [])
    top_chars = _clean_characters(top_chars_raw)
    comparables = report_output.get("tone_comparables") or report_output.get("comparable_films") or []
    comparables = _clean_characters(comparables)
    market_projections = report_output.get("market_projections") or {}
    strength = report_output.get("strength_index") or {}
    commercial = _safe(report_output.get("commercial_positioning"))
    audience = report_output.get("audience_profile") or []
    audience = _clean_characters(audience)
    packaging = _safe(report_output.get("packaging_potential"))
    executive_summary = _safe(report_output.get("executive_summary"))
    summary_note = _safe(report_output.get("summary_note"))
    story_insights = report_output.get("story_insights") or []
    rewrite_priorities = report_output.get("rewrite_priorities") or report_output.get("next_draft_priorities") or []
    strengths_list = report_output.get("strengths") or []
    risks_list = report_output.get("risks") or report_output.get("development_risks") or []
    budget_lane = _safe(market_projections.get("budget_range") or report_output.get("budget_lane") or report_output.get("estimated_budget"))
    streamer_fit = _safe(market_projections.get("streamer_fit") or report_output.get("streamer_fit"))
    awards_lane = _safe(market_projections.get("awards_lane") or report_output.get("awards_lane"))
    franchise = _safe(market_projections.get("franchise_potential") or report_output.get("franchise_potential"))

    if not executive_summary:
        executive_summary = _smart_summary("analysis", title, "", logline, synopsis, [], extra=genre)

    if not strengths_list:
        strengths_list = [s for s in [theme, engine, commercial, packaging] if s][:4]
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
    meta = "  ·  ".join([p for p in [genre, tone] if p])
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
        "Character value",
        "Market position",
        "Rewrite priorities",
        "Why this project matters",
    ]
    pdf.setFillColor(soft); pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(L, cy, "THIS REPORT INCLUDES"); cy -= 14
    for item in contents:
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 10); pdf.drawString(L, cy, "—")
        pdf.setFillColor(muted); pdf.setFont("Helvetica", 10); pdf.drawString(L + 16, cy, item); cy -= 14

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
        ctx.info_row("Top characters", ", ".join(top_chars[:8]))
    ctx.y -= 8

    ctx.section_header("Market Position", "The commercial lane this project appears to be in right now.")
    if comparables:
        ctx.info_row("Comparable titles", ", ".join(comparables[:6]))
    if audience:
        ctx.info_row("Audience profile", ", ".join(audience[:6]))
    if budget_lane:
        ctx.info_row("Budget lane", budget_lane)
    if streamer_fit:
        ctx.info_row("Streamer / buyer fit", streamer_fit)
    if awards_lane:
        ctx.info_row("Awards lane", awards_lane)
    if commercial:
        ctx.info_row("Commercial positioning", commercial)
    if packaging:
        ctx.info_row("Packaging potential", packaging)
    if franchise:
        ctx.info_row("Franchise potential", franchise)
    ctx.y -= 8

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

    ctx.section_header("Why This Project Matters", "The part a novice user, creative producer, or investor can understand quickly.")
    ctx.bullet_list([str(x) for x in story_insights[:8] if str(x).strip()], bullet_color=gold)
    if summary_note:
        ctx.info_row("Final note", summary_note)

    if strength:
        score_parts = []
        for key, label in [
            ("concept", "Concept"),
            ("character", "Character"),
            ("marketability", "Market"),
            ("originality", "Originality"),
        ]:
            val = strength.get(key)
            if val:
                score_parts.append(f"{label}: {val}/10")
        if score_parts:
            ctx.info_row("Strength index", "  ·  ".join(score_parts))

    ctx.methodology_box()
    _footer(pdf, W, ctx.page_no)
    pdf.save()
