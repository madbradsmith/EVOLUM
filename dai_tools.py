from __future__ import annotations

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
    text = re.sub(r'\d{4,}\s*-\s*\w+ \d{1,2},\s*\d{4}\s*\d{1,2}:\d{2}\s*[AP]M\s*-?\s*', '', text)
    text = re.sub(r'([A-Z]{2,6}-){3,}[A-Z]{2,6}', '', text)
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
            "The character is pushing for answers and trying to control what gets revealed.",
            "Play the question like a tactic, not simple curiosity.",
        )
    if any(k in lower for k in ["calm down", "sit down", "listen", "hold on", "wait"]):
        return (
            "Control the Room",
            "The character is taking command and forcing the scene back under control.",
            "Use stillness and certainty rather than volume.",
        )
    if any(k in lower for k in ["don't", "do not", "can't", "cannot", "won't", "stop"]):
        return (
            "Set a Boundary",
            "The character is drawing a line and making the other person feel it.",
            "Keep the delivery clipped and definite.",
        )
    if any(k in lower for k in ["good", "okay", "alright", "cool"]):
        return (
            "Reset and Move Forward",
            "The character absorbs the moment quickly and redirects the action.",
            "Treat it like a professional pivot, not relief.",
        )
    if scene_heading and ("OFFICE" in scene_heading.upper() or "INTERROGATION" in scene_heading.upper()):
        return (
            "Apply Pressure",
            "The character is reading the other person and pressing for leverage.",
            "Let the intelligence do the work.",
        )
    return (
        "Hold Authority",
        "The character is managing the scene from a position of control.",
        "Keep it grounded, specific, and in command.",
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


# ── SHARED HELPERS FOR ALL THREE PDF BUILDERS ─────────────────────────────────

def _safe(val, fallback: str = "") -> str:
    if val is None:
        return fallback
    if isinstance(val, list):
        return ", ".join(str(v) for v in val if str(v).strip())
    return str(val).strip() or fallback


class _PDFCtx:
    """Mutable drawing state — y-cursor and page counter as instance attributes."""

    def __init__(self, pdf: canvas.Canvas, width: float, height: float, left: float,
                 usable_width: float, charcoal, gold, blue, white, muted, soft, panel):
        self.pdf      = pdf
        self.width    = width
        self.height   = height
        self.left     = left
        self.uw       = usable_width
        self.charcoal = charcoal
        self.gold     = gold
        self.blue     = blue
        self.white    = white
        self.muted    = muted
        self.soft     = soft
        self.panel    = panel
        self.y        = height - 56
        self.page_no  = 2

    def section_header(self, title: str, subtitle: str = "") -> None:
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

    def text_block(self, text: str, color=None, font_name: str = "Helvetica",
                   font_size: int = 11, leading: int = 14, inset: int = 0) -> None:
        color = color if color is not None else self.muted
        lines = _split_lines(self.pdf, text, font_name, font_size, self.uw - inset)
        self.y, self.page_no = _ensure_space(self.pdf, self.width, self.height, self.y,
                                             max(40, len(lines) * leading + 10), self.page_no, self.charcoal)
        self.y = _draw_lines(self.pdf, lines, self.left + inset, self.y, leading, font_name, font_size, color)

    def bullet_list(self, items: List[str], bullet_color=None) -> None:
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

    def section_band(self, label: str) -> None:
        panel2 = colors.HexColor("#1f1f1f")
        self.y, self.page_no = _ensure_space(self.pdf, self.width, self.height, self.y, 44, self.page_no, self.charcoal)
        self.pdf.setFillColor(panel2)
        self.pdf.roundRect(self.left, self.y - 20, self.uw, 26, 8, stroke=0, fill=1)
        self.pdf.setFillColor(self.gold)
        self.pdf.setFont("Helvetica-Bold", 12)
        self.pdf.drawString(self.left + 12, self.y - 4, label)
        self.y -= 38

    def info_row(self, label: str, value: str) -> None:
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

    def gold_label(self, label: str) -> None:
        self.y, self.page_no = _ensure_space(self.pdf, self.width, self.height, self.y, 32, self.page_no, self.charcoal)
        self.pdf.setFillColor(self.gold)
        self.pdf.setFont("Helvetica-Bold", 12)
        self.pdf.drawString(self.left, self.y, label.upper())
        self.pdf.setStrokeColor(self.gold)
        self.pdf.line(self.left, self.y - 6, self.left + len(label) * 7, self.y - 6)
        self.y -= 20

    def chip_row(self, items: List[str], chip_color=None) -> None:
        cc = chip_color or self.gold
        x = self.left
        chip_h = 20
        self.y, self.page_no = _ensure_space(self.pdf, self.width, self.height, self.y, chip_h + 12, self.page_no, self.charcoal)
        for item in items:
            w = len(str(item)) * 6.5 + 16
            if x + w > self.left + self.uw:
                self.y -= chip_h + 6
                x = self.left
                self.y, self.page_no = _ensure_space(self.pdf, self.width, self.height, self.y, chip_h + 6, self.page_no, self.charcoal)
            self.pdf.setFillColor(self.panel)
            self.pdf.roundRect(x, self.y - chip_h + 4, w, chip_h, 6, stroke=0, fill=1)
            self.pdf.setFillColor(cc)
            self.pdf.setFont("Helvetica-Bold", 9)
            self.pdf.drawString(x + 8, self.y - 10, str(item))
            x += w + 8
        self.y -= chip_h + 10

    def new_page(self) -> None:
        _footer(self.pdf, self.width, self.page_no)
        self.pdf.showPage()
        self.page_no += 1
        self.pdf.setFillColor(self.charcoal)
        self.pdf.rect(0, 0, self.width, self.height, stroke=0, fill=1)
        self.y = self.height - 56


# ── MODE 1: AUDITION ANALYZER ─────────────────────────────────────────────────

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
    panel    = colors.HexColor("#1a1a1a")
    gold     = colors.HexColor("#f0c15d")
    blue     = colors.HexColor("#52a8ff")
    white    = colors.white
    muted    = colors.HexColor("#cfcfcf")
    soft     = colors.HexColor("#8f8f8f")

    tone            = _safe(brain_data.get("tone"))
    logline         = _safe(brain_data.get("logline"))
    protagonist_sum = _safe(brain_data.get("protagonist_summary"))
    actor_objective = _safe(brain_data.get("actor_objective"))
    danger_zones    = brain_data.get("audition_danger_zones") or []
    tactics         = brain_data.get("playable_tactics") or []
    triggers        = brain_data.get("emotional_triggers") or []
    chemistry_tips  = brain_data.get("reader_chemistry_tips") or []

    # ── COVER ────────────────────────────────────────────────────
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
    pdf.drawString(left, height - 116, "PREP PACKET")

    pdf.setStrokeColor(gold)
    pdf.setLineWidth(1)
    pdf.line(left, height - 132, right, height - 132)

    pdf.setFillColor(soft)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, height - 154, "CHARACTER")
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(left, height - 174, character_name.title())

    cy = height - 200
    beat_label = f"{len(beats)} speaking beat{'s' if len(beats) != 1 else ''} detected" if beats else "No beats detected"
    pdf.setFillColor(soft)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, cy, beat_label)
    cy -= 20

    if tone:
        pdf.setFillColor(soft); pdf.setFont("Helvetica", 9)
        pdf.drawString(left, cy, "TONE"); cy -= 13
        pdf.setFillColor(muted); pdf.setFont("Helvetica", 10)
        for tl in simpleSplit(tone, "Helvetica", 10, usable_width):
            pdf.drawString(left, cy, tl); cy -= 13
        cy -= 6

    if actor_objective:
        obj_lines = simpleSplit(actor_objective, "Helvetica-Oblique", 11, usable_width - 32)
        obj_h = len(obj_lines) * 15 + 30
        pdf.setFillColor(panel)
        pdf.roundRect(left, cy - obj_h + 10, usable_width, obj_h, 12, stroke=0, fill=1)
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(left + 16, cy - 6, "ACTOR OBJECTIVE")
        oy = cy - 22
        pdf.setFillColor(white); pdf.setFont("Helvetica-Oblique", 11)
        for ol in obj_lines:
            pdf.drawString(left + 16, oy, ol); oy -= 15
        cy -= obj_h + 10

    if logline:
        ll_lines = simpleSplit(logline, "Helvetica-Oblique", 10, usable_width - 32)
        ll_h = len(ll_lines) * 14 + 26
        pdf.setFillColor(colors.HexColor("#161616"))
        pdf.roundRect(left, cy - ll_h + 10, usable_width, ll_h, 12, stroke=0, fill=1)
        pdf.setFillColor(soft); pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(left + 16, cy - 6, "LOGLINE")
        ly = cy - 20
        pdf.setFillColor(muted); pdf.setFont("Helvetica-Oblique", 10)
        for ll in ll_lines:
            pdf.drawString(left + 16, ly, ll); ly -= 14
        cy -= ll_h + 10

    cy -= 8
    contents = [
        "The Role in 60 Seconds",
        "What Casting Is Testing",
        "What the Sides Are Really Telling You  (inference)",
        f"Beat Breakdown  ({len(beats)} beats)",
        "Self-Tape Checklist",
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

    # ── CONTENT PAGES ────────────────────────────────────────────
    pdf.setFillColor(charcoal)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    ctx = _PDFCtx(pdf, width, height, left, usable_width, charcoal, gold, blue, white, muted, soft, panel)

    def beat_card(idx: int, beat: BeatEntry) -> None:
        dialogue_lines = _split_lines(pdf, f"{beat.cue_line}: {beat.dialogue}", "Helvetica", 9, usable_width - 28)
        note_lines = _split_lines(pdf, beat.playable_note, "Helvetica", 9, usable_width - 28)
        card_h = max(46 + len(dialogue_lines) * 11 + len(note_lines) * 11 + 14, 100)
        ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, card_h + 10, ctx.page_no, charcoal)
        pdf.setFillColor(panel)
        pdf.roundRect(left, ctx.y - card_h + 10, usable_width, card_h, 12, stroke=0, fill=1)
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(left + 14, ctx.y - 8, f"Beat {idx}  —  {beat.beat}")
        pdf.setFillColor(soft); pdf.setFont("Helvetica", 9)
        pdf.drawString(left + 14, ctx.y - 22, f"{beat.reference}  |  {beat.scene_heading}")
        by = ctx.y - 40
        pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left + 14, by, "Script line"); by -= 12
        by = _draw_lines(pdf, dialogue_lines, left + 14, by, 11, "Helvetica", 9, muted)
        pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left + 14, by - 2, "Playable note"); by -= 14
        _draw_lines(pdf, note_lines, left + 14, by, 11, "Helvetica", 9, muted)
        ctx.y -= card_h + 10

    if not beats:
        ctx.section_header("No matching dialogue found")
        ctx.text_block("The extraction did not detect dialogue for this role. Try entering the character name exactly as it appears in the script.")
        _footer(pdf, width, ctx.page_no)
        pdf.save()
        return output_path

    # THE ROLE IN 60 SECONDS
    ctx.section_header("The Role in 60 Seconds", "Fast read. Audition-focused.")
    if protagonist_sum:
        ctx.text_block(protagonist_sum, color=white, font_size=12, leading=16)
        ctx.y -= 4
    beat_names = [b.beat for b in beats]
    top_beat = beat_names[0] if beat_names else "Hold Authority"
    ctx.text_block(f"Detected {len(beats)} playable beat{'s' if len(beats) != 1 else ''} in the sides. The strongest energy reads closest to '{top_beat}'. Clarity, listening, and specificity will win this room more than volume.", leading=14)
    ctx.y -= 12

    # WHAT CASTING IS TESTING
    ctx.section_header("What Casting Is Testing", "Inferred from the material — not generic advice.")
    if danger_zones:
        ctx.text_block("These are the specific traps in this material. Avoiding them is how you show you can read a room:", color=soft, font_size=10)
        ctx.y -= 4
        ctx.bullet_list(danger_zones, bullet_color=blue)
    else:
        ctx.bullet_list([
            "Can you establish presence without announcing it?",
            "Can you hold pressure without forcing the scene?",
            "Can you let pauses and listening do the work?",
        ], bullet_color=blue)
    ctx.y -= 12

    # WHAT THE SIDES ARE REALLY TELLING YOU
    ctx.section_header("What the Sides Are Really Telling You", "This is the inference section. Most actors miss this.")
    ctx.y -= 4

    if actor_objective:
        ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, 50, ctx.page_no, charcoal)
        pdf.setFillColor(blue); pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, ctx.y, "The core objective")
        ctx.y -= 14
        ctx.text_block(actor_objective, color=white, font_size=11, leading=14)
        ctx.y -= 8

    if triggers:
        ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, 40, ctx.page_no, charcoal)
        pdf.setFillColor(blue); pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, ctx.y, "What the scene is designed to provoke")
        ctx.y -= 14
        ctx.chip_row(triggers, chip_color=gold)
        ctx.y -= 4

    if tactics:
        ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, 40, ctx.page_no, charcoal)
        pdf.setFillColor(blue); pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, ctx.y, "Tactics available to this character")
        ctx.y -= 14
        ctx.chip_row(tactics, chip_color=muted)
        ctx.y -= 4

    if chemistry_tips:
        ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, 40, ctx.page_no, charcoal)
        pdf.setFillColor(blue); pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, ctx.y, "Working with the reader")
        ctx.y -= 14
        ctx.bullet_list(chemistry_tips, bullet_color=gold)
    ctx.y -= 12

    # BEAT BREAKDOWN
    ctx.new_page()
    ctx.section_header("Beat Breakdown", f"All {len(beats)} detected beat{'s' if len(beats) != 1 else ''} from the current sides.")
    for idx, beat in enumerate(beats, start=1):
        beat_card(idx, beat)
    ctx.y -= 12

    # SELF-TAPE CHECKLIST
    ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, 100, ctx.page_no, charcoal)
    ctx.section_header("Self-Tape Checklist", "Short, practical, deadline-friendly.")
    ctx.bullet_list([
        "Frame chest-up or mid-shot unless casting specifies otherwise.",
        "Lock your eyeline marks for each off-camera character before you record.",
        "Keep the background clean and the audio easy to understand.",
        "Do not rush pauses. Let the thought finish before the next line arrives.",
        "Dress to suggest the role — not to costume it.",
        "Check file name, submission instructions, and deadline before sending.",
    ], bullet_color=gold)

    _footer(pdf, width, ctx.page_no)
    pdf.save()
    return output_path


# ── MODE 2: BOOKED ROLE ANALYZER ──────────────────────────────────────────────

_CONTINUITY_NOTES: Dict[str, str] = {
    "Pressure for Information": "Track what you learn in this beat and carry it forward — the character's intelligence compounds across scenes.",
    "Control the Room": "High-stakes control moment. Protect the physicality and pace — don't let it read the same as lower-pressure beats.",
    "Set a Boundary": "The line drawn here defines the character's limit. The next scene already knows this line was drawn.",
    "Reset and Move Forward": "Pivot beat — keep it light and efficient. Don't over-color it or it'll compete with heavier moments.",
    "Apply Pressure": "The character is operating here, not reacting. Keep it deliberate across every take.",
    "Hold Authority": "This is the character's baseline. Make sure it doesn't flatten — authority still has texture and specificity.",
}
_DEFAULT_CONTINUITY = "Stay behaviorally consistent. Let scene pressure alter pace and patience while core identity holds."


def _unique_scenes(beats: List[BeatEntry]) -> List[str]:
    return list(dict.fromkeys([b.scene_heading for b in beats if b.scene_heading]))


def build_actor_booked_pdf(script_text: str, character_name: str, output_path: str | Path, brain_data: Optional[Dict] = None) -> Path:
    output_path = Path(output_path)
    beats = extract_beats(script_text, character_name)
    brain_data = brain_data or {}

    pdf = canvas.Canvas(str(output_path), pagesize=LETTER)
    pdf.setTitle(f"{character_name.title()} — Booked Role Packet")
    width, height = LETTER
    left = 42
    right = width - 42
    usable_width = right - left

    charcoal = colors.HexColor("#111111")
    panel    = colors.HexColor("#1a1a1a")
    gold     = colors.HexColor("#f0c15d")
    blue     = colors.HexColor("#52a8ff")
    white    = colors.white
    muted    = colors.HexColor("#cfcfcf")
    soft     = colors.HexColor("#8f8f8f")

    tone            = _safe(brain_data.get("tone"))
    logline         = _safe(brain_data.get("logline"))
    protagonist_sum = _safe(brain_data.get("protagonist_summary"))
    actor_objective = _safe(brain_data.get("actor_objective"))
    tactics         = brain_data.get("playable_tactics") or []
    triggers        = brain_data.get("emotional_triggers") or []
    role_arc        = brain_data.get("role_arc_map") or []
    pressure_ladder = brain_data.get("pressure_ladder") or []
    em_continuity   = brain_data.get("emotional_continuity") or []
    rel_map         = brain_data.get("relationship_leverage_map") or []
    costume_clues   = brain_data.get("costume_behavior_clues") or []
    memo_beats      = brain_data.get("memorization_beats") or []
    set_checklist   = brain_data.get("set_ready_checklist") or []
    scene_count     = len(_unique_scenes(beats))

    # ── COVER ────────────────────────────────────────────────────
    pdf.setFillColor(charcoal)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    pdf.setFillColor(gold)
    pdf.rect(0, height - 6, width, 6, stroke=0, fill=1)

    pdf.setFillColor(soft); pdf.setFont("Helvetica", 9)
    pdf.drawString(left, height - 30, "EVOLUM  ·  ACTOR PREPARATION")

    pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 40)
    pdf.drawString(left, height - 80, "BOOKED ROLE")
    pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(left, height - 116, "PREP PACKET")

    pdf.setStrokeColor(gold); pdf.setLineWidth(1)
    pdf.line(left, height - 132, right, height - 132)

    pdf.setFillColor(soft); pdf.setFont("Helvetica", 10)
    pdf.drawString(left, height - 154, "CHARACTER")
    pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(left, height - 174, character_name.title())

    cy = height - 200
    beat_label = (f"{len(beats)} speaking beat{'s' if len(beats) != 1 else ''} across "
                  f"{scene_count} scene{'s' if scene_count != 1 else ''}") if beats else "No beats detected"
    pdf.setFillColor(soft); pdf.setFont("Helvetica", 10)
    pdf.drawString(left, cy, beat_label); cy -= 20

    if tone:
        pdf.setFillColor(soft); pdf.setFont("Helvetica", 9)
        pdf.drawString(left, cy, "TONE"); cy -= 13
        pdf.setFillColor(muted); pdf.setFont("Helvetica", 10)
        for tl in simpleSplit(tone, "Helvetica", 10, usable_width):
            pdf.drawString(left, cy, tl); cy -= 13
        cy -= 6

    if actor_objective:
        obj_lines = simpleSplit(actor_objective, "Helvetica-Oblique", 11, usable_width - 32)
        obj_h = len(obj_lines) * 15 + 30
        pdf.setFillColor(panel)
        pdf.roundRect(left, cy - obj_h + 10, usable_width, obj_h, 12, stroke=0, fill=1)
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(left + 16, cy - 6, "ACTOR OBJECTIVE")
        oy = cy - 22
        pdf.setFillColor(white); pdf.setFont("Helvetica-Oblique", 11)
        for ol in obj_lines:
            pdf.drawString(left + 16, oy, ol); oy -= 15
        cy -= obj_h + 10

    if logline:
        ll_lines = simpleSplit(logline, "Helvetica-Oblique", 10, usable_width - 32)
        ll_h = len(ll_lines) * 14 + 26
        pdf.setFillColor(colors.HexColor("#161616"))
        pdf.roundRect(left, cy - ll_h + 10, usable_width, ll_h, 12, stroke=0, fill=1)
        pdf.setFillColor(soft); pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(left + 16, cy - 6, "LOGLINE")
        ly = cy - 20
        pdf.setFillColor(muted); pdf.setFont("Helvetica-Oblique", 10)
        for ll in ll_lines:
            pdf.drawString(left + 16, ly, ll); ly -= 14
        cy -= ll_h + 10

    cy -= 8
    contents = [
        "Role Overview",
        "Actor Objective",
        "Role Arc & Pressure Ladder",
        "Playable Tactics & Emotional Triggers",
        "Emotional Continuity",
        "Relationship Map",
        "Physical & Costume Notes",
        "Beats to Lock In",
        f"Full Scene Journey  ({len(beats)} beats)",
        "Set-Ready Checklist",
    ]
    pdf.setFillColor(soft); pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(left, cy, "THIS PACKET INCLUDES"); cy -= 14
    for item in contents:
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, cy, "—")
        pdf.setFillColor(muted); pdf.setFont("Helvetica", 10)
        pdf.drawString(left + 16, cy, item); cy -= 13

    pdf.setFillColor(gold)
    pdf.rect(0, 0, width, 4, stroke=0, fill=1)
    _footer(pdf, width, 1)
    pdf.showPage()

    # ── CONTENT PAGES ────────────────────────────────────────────
    pdf.setFillColor(charcoal)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    ctx = _PDFCtx(pdf, width, height, left, usable_width, charcoal, gold, blue, white, muted, soft, panel)

    def beat_card(idx: int, beat: BeatEntry) -> None:
        continuity = _CONTINUITY_NOTES.get(beat.beat, _DEFAULT_CONTINUITY)
        d_lines = _split_lines(pdf, f"{beat.cue_line}: {beat.dialogue}", "Helvetica", 9, usable_width - 28)
        c_lines = _split_lines(pdf, continuity, "Helvetica", 9, usable_width - 28)
        card_h = max(46 + len(d_lines) * 11 + len(c_lines) * 11 + 14, 100)
        ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, card_h + 10, ctx.page_no, charcoal)
        pdf.setFillColor(panel)
        pdf.roundRect(left, ctx.y - card_h + 10, usable_width, card_h, 12, stroke=0, fill=1)
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(left + 14, ctx.y - 8, f"Scene Beat {idx}  —  {beat.beat}")
        pdf.setFillColor(soft); pdf.setFont("Helvetica", 9)
        pdf.drawString(left + 14, ctx.y - 22, f"{beat.reference}  |  {beat.scene_heading}")
        by = ctx.y - 40
        pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left + 14, by, "Script line"); by -= 12
        by = _draw_lines(pdf, d_lines, left + 14, by, 11, "Helvetica", 9, muted)
        pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left + 14, by - 2, "Continuity note"); by -= 14
        _draw_lines(pdf, c_lines, left + 14, by, 11, "Helvetica", 9, muted)
        ctx.y -= card_h + 10

    if not beats:
        ctx.section_header("No matching dialogue found")
        ctx.text_block("The extraction did not detect dialogue for this role. Try entering the character name exactly as it appears in the script.")
        _footer(pdf, width, ctx.page_no)
        pdf.save()
        return output_path

    # ROLE OVERVIEW
    ctx.section_header("Role Overview", "Full booked-mode read using the complete script.")
    if protagonist_sum:
        ctx.text_block(protagonist_sum, color=white, font_size=12, leading=16)
        ctx.y -= 4
    beat_names = [b.beat for b in beats]
    top_beat = beat_names[0] if beat_names else "Hold Authority"
    ctx.text_block(f"Detected {len(beats)} speaking beat{'s' if len(beats) != 1 else ''} across {scene_count} scene{'s' if scene_count != 1 else ''}. The dominant energy reads closest to '{top_beat}'. Prep should focus on continuity, truth, and tracking how pressure shifts from scene to scene.", leading=14)
    ctx.y -= 12

    # ACTOR OBJECTIVE
    if actor_objective:
        ctx.section_header("Actor Objective", "What this role is fundamentally doing in every scene.")
        ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, 50, ctx.page_no, charcoal)
        pdf.setFillColor(panel)
        pdf.roundRect(left, ctx.y - 38, usable_width, 46, 10, stroke=0, fill=1)
        pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 12)
        obj_lines = _split_lines(pdf, actor_objective, "Helvetica-Bold", 12, usable_width - 28)
        oy = ctx.y - 14
        for ol in obj_lines:
            pdf.drawString(left + 14, oy, ol); oy -= 16
        ctx.y -= 56
        ctx.y -= 8

    # ROLE ARC & PRESSURE LADDER
    if role_arc or pressure_ladder:
        ctx.section_header("Role Arc & Pressure Ladder", "Where the role travels and how the stakes build.")
        if role_arc:
            ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, 30, ctx.page_no, charcoal)
            pdf.setFillColor(blue); pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(left, ctx.y, "Arc progression"); ctx.y -= 14
            ctx.chip_row(role_arc, chip_color=gold)
        if pressure_ladder:
            ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, 30, ctx.page_no, charcoal)
            pdf.setFillColor(blue); pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(left, ctx.y, "Pressure escalation"); ctx.y -= 14
            ctx.chip_row(pressure_ladder, chip_color=muted)
        ctx.y -= 10

    # PLAYABLE TACTICS & EMOTIONAL TRIGGERS
    if tactics or triggers:
        ctx.section_header("Playable Tactics & Emotional Triggers")
        if tactics:
            ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, 30, ctx.page_no, charcoal)
            pdf.setFillColor(blue); pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(left, ctx.y, "Tactics available to this character"); ctx.y -= 14
            ctx.chip_row(tactics, chip_color=gold)
        if triggers:
            ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, 30, ctx.page_no, charcoal)
            pdf.setFillColor(blue); pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(left, ctx.y, "What the role is emotionally responding to"); ctx.y -= 14
            ctx.chip_row(triggers, chip_color=muted)
        ctx.y -= 10

    # EMOTIONAL CONTINUITY
    if em_continuity:
        ctx.section_header("Emotional Continuity", "The through-line that needs to hold across every scene and take.")
        ctx.bullet_list(em_continuity, bullet_color=gold)
        ctx.y -= 8

    # RELATIONSHIP MAP
    if rel_map:
        ctx.section_header("Relationship Map", "How key relationships function in this script.")
        for rel in rel_map:
            char = _safe(rel.get("character"))
            dynamic = _safe(rel.get("dynamic"))
            func = _safe(rel.get("function"))
            if char:
                ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, 44, ctx.page_no, charcoal)
                pdf.setFillColor(panel)
                pdf.roundRect(left, ctx.y - 34, usable_width, 42, 8, stroke=0, fill=1)
                pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 10)
                pdf.drawString(left + 12, ctx.y - 10, char)
                pdf.setFillColor(soft); pdf.setFont("Helvetica", 9)
                pdf.drawString(left + 12, ctx.y - 22, dynamic)
                f_lines = _split_lines(pdf, func, "Helvetica", 9, usable_width - 100)
                pdf.setFillColor(muted)
                fy = ctx.y - 22
                for fl in f_lines[:1]:
                    pdf.drawString(left + 200, fy, fl)
                ctx.y -= 46
        ctx.y -= 6

    # PHYSICAL & COSTUME NOTES
    if costume_clues:
        ctx.section_header("Physical & Costume Notes", "How the body and wardrobe carry the role.")
        ctx.bullet_list(costume_clues, bullet_color=blue)
        ctx.y -= 8

    # BEATS TO LOCK IN
    if memo_beats:
        ctx.section_header("Beats to Lock In", "The moments that define how casting and the director will remember this performance.")
        ctx.bullet_list(memo_beats, bullet_color=gold)
        ctx.y -= 8

    # FULL SCENE JOURNEY
    ctx.new_page()
    ctx.section_header("Full Scene Journey", f"All {len(beats)} detected beat{'s' if len(beats) != 1 else ''} as prep cards.")
    for idx, beat in enumerate(beats, start=1):
        beat_card(idx, beat)
    ctx.y -= 10

    # SET-READY CHECKLIST
    ctx.y, ctx.page_no = _ensure_space(pdf, width, height, ctx.y, 100, ctx.page_no, charcoal)
    ctx.section_header("Set-Ready Checklist")
    checklist = set_checklist if set_checklist else [
        "Know where this scene sits in the role's pressure line before you play it.",
        "Track whether the character is entering hot, steady, or already compromised.",
        "Hold body language, voice rhythm, and listening behavior consistently across takes.",
        "Mark any scene where the role's pressure level clearly rises or drops.",
        "Protect continuity more than novelty.",
    ]
    ctx.bullet_list(checklist, bullet_color=gold)

    _footer(pdf, width, ctx.page_no)
    pdf.save()
    return output_path


# ── MODE 3: SCRIPT ANALYZER ───────────────────────────────────────────────────

def build_simple_analysis_pdf(report_output: dict, out_path: Path):
    W, H = LETTER
    L, R = 42, W - 42
    UW = R - L

    charcoal = colors.HexColor("#111111")
    panel    = colors.HexColor("#1a1a1a")
    gold     = colors.HexColor("#f0c15d")
    blue     = colors.HexColor("#4C88C7")
    white    = colors.white
    muted    = colors.HexColor("#cfcfcf")
    soft     = colors.HexColor("#8f8f8f")
    rule     = colors.HexColor("#2b2b2b")

    title           = _safe(report_output.get("title"), "UNTITLED PROJECT").upper()
    genre           = _safe(report_output.get("genre") or report_output.get("world"))
    tone            = _safe(report_output.get("tone"))
    logline         = _safe(report_output.get("logline"))
    synopsis        = _safe(report_output.get("synopsis"))
    theme           = _safe(report_output.get("theme"))
    world           = _safe(report_output.get("world"))
    core            = _safe(report_output.get("core_conflict"))
    engine          = _safe(report_output.get("story_engine"))
    reversal        = _safe(report_output.get("reversal"))
    setting         = _safe(report_output.get("setting"))
    time_frame      = _safe(report_output.get("time_frame"))
    lead            = _safe(report_output.get("lead_character") or report_output.get("protagonist"))
    supports        = report_output.get("supporting_characters") or []
    protagonist_sum = _safe(report_output.get("protagonist_summary"))
    char_leverage   = _safe(report_output.get("character_leverage"))
    top_chars       = (report_output.get("character_analysis") or {}).get("top_characters", [])
    comparables        = report_output.get("tone_comparables") or []
    comparable_films   = report_output.get("comparable_films") or []
    market_projections = report_output.get("market_projections") or {}
    strength           = report_output.get("strength_index") or {}
    commercial      = _safe(report_output.get("commercial_positioning"))
    audience        = report_output.get("audience_profile") or []
    packaging       = _safe(report_output.get("packaging_potential"))
    exec_summary    = _safe(report_output.get("executive_summary"))
    summary_note    = _safe(report_output.get("summary_note"))
    story_insights  = report_output.get("story_insights") or []

    pdf = canvas.Canvas(str(out_path), pagesize=LETTER)
    pdf.setTitle(f"{title} Analysis Report")

    # ── COVER ────────────────────────────────────────────────────
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

    pdf.setStrokeColor(gold); pdf.setLineWidth(1)
    pdf.line(L, H - 132, R, H - 132)

    pdf.setFillColor(soft); pdf.setFont("Helvetica", 10)
    pdf.drawString(L, H - 154, "PROJECT")
    pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 20)
    ty = H - 174
    for tl in simpleSplit(title, "Helvetica-Bold", 20, UW):
        pdf.drawString(L, ty, tl); ty -= 26

    cy = ty - 10

    if genre:
        pdf.setFillColor(soft); pdf.setFont("Helvetica", 9)
        pdf.drawString(L, cy, "GENRE"); cy -= 13
        pdf.setFillColor(muted); pdf.setFont("Helvetica", 11)
        for gl in simpleSplit(genre, "Helvetica", 11, UW):
            pdf.drawString(L, cy, gl); cy -= 13
        cy -= 4

    if tone:
        pdf.setFillColor(soft); pdf.setFont("Helvetica", 9)
        pdf.drawString(L, cy, "TONE"); cy -= 13
        pdf.setFillColor(muted); pdf.setFont("Helvetica", 11)
        for tl in simpleSplit(tone, "Helvetica", 11, UW):
            pdf.drawString(L, cy, tl); cy -= 13
        cy -= 4

    if comparables:
        pdf.setFillColor(soft); pdf.setFont("Helvetica", 9)
        pdf.drawString(L, cy, "COMPARABLE TO"); cy -= 13
        comp_text = "  ·  ".join(str(c) for c in comparables[:4] if str(c).strip())
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Oblique", 11)
        for cl in simpleSplit(comp_text, "Helvetica-Oblique", 11, UW):
            pdf.drawString(L, cy, cl); cy -= 13
        cy -= 6

    if logline:
        ll_lines = simpleSplit(logline, "Helvetica-Oblique", 11, UW - 36)
        ph = len(ll_lines) * 15 + 28
        pdf.setFillColor(panel)
        pdf.roundRect(L, cy - ph + 10, UW, ph, 12, stroke=0, fill=1)
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(L + 16, cy - 6, "LOGLINE")
        ly = cy - 22
        pdf.setFillColor(muted); pdf.setFont("Helvetica-Oblique", 11)
        for ll in ll_lines:
            pdf.drawString(L + 16, ly, ll); ly -= 15
        cy -= ph + 14

    if strength:
        score_items = [("CONCEPT", strength.get("concept", 0)), ("CHARACTER", strength.get("character", 0)),
                       ("MARKET", strength.get("marketability", 0)), ("ORIGINAL", strength.get("originality", 0))]
        score_items = [(lbl, v) for lbl, v in score_items if v]
        if score_items:
            pdf.setFillColor(soft); pdf.setFont("Helvetica-Bold", 9)
            pdf.drawString(L, cy, "STRENGTH INDEX"); cy -= 14
            badge_w = (UW - 12) / 4
            for bi, (lbl, val) in enumerate(score_items[:4]):
                bx = L + bi * (badge_w + 4)
                pdf.setFillColor(panel); pdf.roundRect(bx, cy - 20, badge_w, 26, 6, stroke=0, fill=1)
                pdf.setFillColor(soft); pdf.setFont("Helvetica", 7.5)
                pdf.drawString(bx + 6, cy - 4, lbl)
                pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 13)
                pdf.drawRightString(bx + badge_w - 6, cy - 17, f"{val}/10")
            cy -= 36

    cy -= 4
    contents = [
        "The Story  (logline, synopsis)",
        "Story Core  (world, theme, conflict, engine, reversal)",
        "The Protagonist",
        "Character Landscape",
        "Market & Packaging",
        "Comparable Films  (with context and budget tier)",
        "Market Projections  (budget, distribution, awards, franchise)",
    ]
    pdf.setFillColor(soft); pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(L, cy, "THIS REPORT INCLUDES"); cy -= 14
    for item in contents:
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(L, cy, "—")
        pdf.setFillColor(muted); pdf.setFont("Helvetica", 10)
        pdf.drawString(L + 16, cy, item); cy -= 13

    pdf.setFillColor(gold)
    pdf.rect(0, 0, W, 4, stroke=0, fill=1)
    pdf.setStrokeColor(rule); pdf.line(L, 28, R, 28)
    pdf.setFillColor(soft); pdf.setFont("Helvetica", 8)
    pdf.drawString(L, 16, "Powered by Developum AI Engine")
    pdf.drawRightString(R, 16, "Page 1")
    pdf.showPage()

    # ── CONTENT PAGES ────────────────────────────────────────────
    pdf.setFillColor(charcoal)
    pdf.rect(0, 0, W, H, stroke=0, fill=1)

    def footer(p):
        pdf.setStrokeColor(rule); pdf.line(L, 28, R, 28)
        pdf.setFillColor(soft); pdf.setFont("Helvetica", 8)
        pdf.drawString(L, 16, "Powered by Developum AI Engine")
        pdf.drawRightString(R, 16, f"Page {p}")

    ctx = _PDFCtx(pdf, W, H, L, UW, charcoal, gold, blue, white, muted, soft, panel)

    # SUMMARY CALLOUT
    if summary_note:
        ctx.y, ctx.page_no = _ensure_space(pdf, W, H, ctx.y, 60, ctx.page_no, charcoal)
        sn_lines = simpleSplit(summary_note, "Helvetica-Oblique", 11, UW - 32)
        sn_h = len(sn_lines) * 15 + 28
        pdf.setFillColor(panel)
        pdf.roundRect(L, ctx.y - sn_h + 10, UW, sn_h, 12, stroke=0, fill=1)
        pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(L + 16, ctx.y - 6, "OVERVIEW")
        sy = ctx.y - 22
        pdf.setFillColor(muted); pdf.setFont("Helvetica-Oblique", 11)
        for sl in sn_lines:
            pdf.drawString(L + 16, sy, sl); sy -= 15
        ctx.y -= sn_h + 14

    # THE STORY
    ctx.section_header("The Story")
    if logline:
        ctx.y, ctx.page_no = _ensure_space(pdf, W, H, ctx.y, 40, ctx.page_no, charcoal)
        pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 13)
        for line in simpleSplit(logline, "Helvetica-Bold", 13, UW):
            pdf.drawString(L, ctx.y, line); ctx.y -= 17
        ctx.y -= 6
    if synopsis:
        ctx.text_block(synopsis, color=muted, font_size=11, leading=15)
    ctx.y -= 14

    # STORY CORE
    ctx.section_band("STORY CORE")
    if world:
        ctx.info_row("World", world)
    if setting:
        ctx.info_row("Setting", setting)
    if time_frame:
        ctx.info_row("Time Frame", time_frame)
    if theme:
        ctx.info_row("Theme", theme)
    if core:
        ctx.info_row("Core Conflict", core)
    if engine:
        ctx.info_row("Story Engine", engine)
    if reversal:
        ctx.info_row("Reversal", reversal)
    ctx.y -= 14

    # THE PROTAGONIST
    if protagonist_sum or lead:
        ctx.section_header("The Protagonist")
        if lead:
            ctx.y, ctx.page_no = _ensure_space(pdf, W, H, ctx.y, 24, ctx.page_no, charcoal)
            pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 13)
            pdf.drawString(L, ctx.y, lead); ctx.y -= 18
        if protagonist_sum:
            ctx.text_block(protagonist_sum, color=white, font_size=11, leading=15)
        ctx.y -= 14

    # CHARACTER LANDSCAPE
    ctx.section_header("Character Landscape")
    if char_leverage:
        ctx.text_block(char_leverage, color=muted, font_size=11, leading=15)
        ctx.y -= 6
    if supports:
        sup_text = ",  ".join(str(s) for s in supports if str(s).strip())
        ctx.text_block(f"Supporting cast: {sup_text}", color=soft, font_size=10, leading=13)
        ctx.y -= 6
    if top_chars:
        ctx.y, ctx.page_no = _ensure_space(pdf, W, H, ctx.y, 60, ctx.page_no, charcoal)
        colx = [L, L + 140, L + 230, L + 330]
        headers = ["Character", "Dialogue", "Action", "First Seen"]
        pdf.setFillColor(blue)
        pdf.roundRect(L, ctx.y - 16, UW, 22, 8, stroke=0, fill=1)
        pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 9)
        for hx, ht in zip(colx, headers):
            pdf.drawString(hx + 8, ctx.y - 2, ht)
        ctx.y -= 26
        for i, entry in enumerate(top_chars[:8]):
            ctx.y, ctx.page_no = _ensure_space(pdf, W, H, ctx.y, 22, ctx.page_no, charcoal)
            if i % 2 == 0:
                pdf.setFillColor(panel)
                pdf.roundRect(L, ctx.y - 16, UW, 20, 6, stroke=0, fill=1)
            pdf.setFillColor(white); pdf.setFont("Helvetica-Bold", 9.5)
            pdf.drawString(colx[0] + 8, ctx.y - 3, _safe(entry.get("name")))
            pdf.setFont("Helvetica", 9.5)
            pdf.drawString(colx[1] + 8, ctx.y - 3, str(entry.get("dialogue_count", 0)))
            pdf.drawString(colx[2] + 8, ctx.y - 3, str(entry.get("action_count", 0)))
            pdf.drawString(colx[3] + 8, ctx.y - 3, str(entry.get("first_seen", 0)))
            ctx.y -= 22
    ctx.y -= 14

    # MARKET & PACKAGING
    ctx.section_band("MARKET & PACKAGING")
    if exec_summary:
        ctx.y -= 6
        ctx.text_block(exec_summary, color=muted, font_size=11, leading=15)
        ctx.y -= 6
    if commercial:
        ctx.info_row("Positioning", commercial)
    if packaging:
        ctx.info_row("Packaging", packaging)
    if audience:
        aud_text = ",  ".join(str(a) for a in audience if str(a).strip())
        ctx.info_row("Audience", aud_text)
    if comparable_films:
        ctx.y, ctx.page_no = _ensure_space(pdf, W, H, ctx.y, 44, ctx.page_no, charcoal)
        pdf.setFillColor(soft); pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(L, ctx.y, "COMPARABLE FILMS"); ctx.y -= 16
        for film in comparable_films[:3]:
            if not isinstance(film, dict):
                continue
            ctx.y, ctx.page_no = _ensure_space(pdf, W, H, ctx.y, 52, ctx.page_no, charcoal)
            pdf.setFillColor(panel)
            pdf.roundRect(L, ctx.y - 38, UW, 44, 8, stroke=0, fill=1)
            pdf.setFillColor(gold); pdf.setFont("Helvetica-Bold", 10.5)
            pdf.drawString(L + 12, ctx.y - 6, _safe(film.get("title")))
            budget = _safe(film.get("budget_tier"))
            box_office = _safe(film.get("box_office"))
            if budget or box_office:
                badge = f"{budget}  ·  {box_office}" if budget and box_office else budget or box_office
                pdf.setFillColor(soft); pdf.setFont("Helvetica", 8)
                pdf.drawRightString(L + UW - 12, ctx.y - 6, badge)
            why_lines = simpleSplit(_safe(film.get("why")), "Helvetica", 9.5, UW - 24)
            wy = ctx.y - 20
            pdf.setFillColor(muted); pdf.setFont("Helvetica", 9.5)
            for wl in why_lines[:2]:
                pdf.drawString(L + 12, wy, wl); wy -= 13
            ctx.y -= 52
        ctx.y -= 6
    elif comparables:
        ctx.y, ctx.page_no = _ensure_space(pdf, W, H, ctx.y, 44, ctx.page_no, charcoal)
        pdf.setFillColor(soft); pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(L, ctx.y, "COMPARABLES"); ctx.y -= 14
        ctx.chip_row(comparables, chip_color=gold)

    if market_projections:
        ctx.section_band("MARKET PROJECTIONS")
        if market_projections.get("estimated_budget_tier"):
            ctx.info_row("Budget Tier", market_projections["estimated_budget_tier"])
        if market_projections.get("distribution_angle"):
            ctx.info_row("Distribution", market_projections["distribution_angle"])
        if market_projections.get("awards_potential"):
            ctx.info_row("Awards", market_projections["awards_potential"])
        if market_projections.get("audience_reach"):
            ctx.info_row("Audience", market_projections["audience_reach"])
        if market_projections.get("franchise_potential"):
            ctx.info_row("Franchise", market_projections["franchise_potential"])

    ctx.y -= 14

    # KEY OBSERVATIONS
    if story_insights:
        ctx.section_band("KEY OBSERVATIONS")
        ctx.bullet_list(story_insights, bullet_color=gold)
        ctx.y -= 8

    footer(ctx.page_no)
    pdf.save()
