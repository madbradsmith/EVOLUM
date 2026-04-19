from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas


@dataclass
class BeatEntry:
    reference: str
    scene_heading: str
    cue_line: str
    dialogue: str
    beat: str
    subtext: str
    playable_note: str


# Per-beat-type continuity notes so every card reads differently
_CONTINUITY_NOTES: Dict[str, str] = {
    "Pressure for Information": "Track what you learn in this beat and carry it forward — the character's intelligence compounds across scenes.",
    "Control the Room": "This is a high-stakes control moment. Protect the physicality and pace — don't let it read the same as lower-pressure beats.",
    "Set a Boundary": "The line drawn here defines the character's limit. Continuity means the next scene knows that line was already drawn.",
    "Reset and Move Forward": "This is a pivot beat — keep it light and efficient. Don't over-color it or it'll compete with the heavier moments.",
    "Apply Pressure": "Maintain the intelligence here. This is the character operating, not reacting. Keep it deliberate across every take.",
    "Hold Authority": "This is the character's baseline energy. Make sure it doesn't flatten — authority still has texture and specificity.",
}

_DEFAULT_CONTINUITY = "Stay behaviorally consistent. Let the scene pressure alter pace and patience while the core identity holds."


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


def _unique_scenes(beats: List[BeatEntry]) -> List[str]:
    return list(dict.fromkeys([b.scene_heading for b in beats if b.scene_heading]))


def _role_snapshot(character_name: str, beats: List[BeatEntry]) -> List[str]:
    beat_names = [b.beat for b in beats]
    top = beat_names[0] if beat_names else "Hold Authority"
    count = len(beats)
    scene_count = len(_unique_scenes(beats))
    return [
        f"{character_name.title()} currently reads as a role carried by pressure, control, and situational intelligence.",
        f"Detected {count} speaking beat{'s' if count != 1 else ''} across {scene_count} scene{'s' if scene_count != 1 else ''}, with the strongest recurring energy landing closest to '{top}'.",
        "Booked-mode prep should help the actor hold continuity, protect truth, and track shifts from one scene to the next.",
    ]


def _relationship_lines(character_name: str, beats: List[BeatEntry]) -> List[str]:
    scene_count = len(_unique_scenes(beats))
    return [
        f"{character_name.title()} appears to function as a pressure-sensitive role whose relationships are filtered through control, information, and timing.",
        f"The current material suggests this character is most active when scene pressure is already elevated — the role is interacting from a position of strategy rather than innocence.",
        f"Across {scene_count} detected scene{'s' if scene_count != 1 else ''}, the strongest dynamic is not confession — it is scene management.",
    ]


def _continuity_lines(beats: List[BeatEntry]) -> List[str]:
    unique_beats = list(dict.fromkeys([b.beat for b in beats]))
    if not unique_beats:
        unique_beats = ["Hold Authority"]
    joined = ", ".join(unique_beats[:4])
    return [
        f"Current extracted continuity is anchored in these recurring beat types: {joined}.",
        "The performance should therefore track not only what is said, but whether pressure is rising, stabilizing, or being redirected.",
        "The safest continuity rule is to let the role stay behaviorally consistent while allowing scene pressure to alter pace, patience, and openness.",
    ]


def build_actor_booked_pdf(script_text: str, character_name: str, output_path: str | Path, brain_data: Optional[Dict] = None) -> Path:
    output_path = Path(output_path)
    beats = extract_beats(script_text, character_name)
    brain_data = brain_data or {}

    pdf = canvas.Canvas(str(output_path), pagesize=LETTER)
    width, height = LETTER
    page_no = 1
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

    # ── COVER PAGE ──────────────────────────────────────────────
    pdf.setFillColor(charcoal)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    # Top gold stripe
    pdf.setFillColor(gold)
    pdf.rect(0, height - 6, width, 6, stroke=0, fill=1)

    # Label
    pdf.setFillColor(soft)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(left, height - 30, "EVOLUM  ·  ACTOR PREPARATION")

    # Main title
    pdf.setFillColor(gold)
    pdf.setFont("Helvetica-Bold", 40)
    pdf.drawString(left, height - 80, "BOOKED ROLE")
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(left, height - 116, "PREP PACKET")

    # Divider
    pdf.setStrokeColor(gold)
    pdf.setLineWidth(1)
    pdf.line(left, height - 132, right, height - 132)

    # Character name
    pdf.setFillColor(soft)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, height - 154, "CHARACTER")
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(left, height - 174, character_name.title())

    cover_y = height - 210

    # Beat count
    pdf.setFillColor(soft)
    pdf.setFont("Helvetica", 10)
    scene_count = len(_unique_scenes(beats))
    beat_label = f"{len(beats)} speaking beat{'s' if len(beats) != 1 else ''} across {scene_count} scene{'s' if scene_count != 1 else ''}" if beats else "No beats detected"
    pdf.drawString(left, cover_y, beat_label)
    cover_y -= 26

    # Brain data: tone
    tone = brain_data.get("tone", "")
    if tone:
        pdf.setFillColor(soft)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(left, cover_y, "TONE")
        cover_y -= 14
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 11)
        tone_lines = simpleSplit(tone, "Helvetica", 11, usable_width)
        for tl in tone_lines:
            pdf.drawString(left, cover_y, tl)
            cover_y -= 14
        cover_y -= 8

    # Brain data: logline in a panel
    logline = brain_data.get("logline", "")
    if logline:
        llines = simpleSplit(logline, "Helvetica-Oblique", 11, usable_width - 36)
        panel_h = len(llines) * 15 + 28
        pdf.setFillColor(panel)
        pdf.roundRect(left, cover_y - panel_h + 10, usable_width, panel_h, 12, stroke=0, fill=1)
        pdf.setFillColor(gold)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(left + 16, cover_y - 6, "LOGLINE")
        ly = cover_y - 22
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica-Oblique", 11)
        for ll in llines:
            pdf.drawString(left + 16, ly, ll)
            ly -= 15
        cover_y -= panel_h + 14

    # Packet contents list
    cover_y -= 14
    contents = [
        "Full Role Snapshot",
        "Relationship and Function Read",
        "Continuity Rules",
        f"Complete Scene Journey  ({len(beats)} beats)",
        "Set-Ready Checklist",
    ]
    pdf.setFillColor(soft)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(left, cover_y, "THIS PACKET INCLUDES")
    cover_y -= 16
    for item in contents:
        pdf.setFillColor(gold)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, cover_y, "—")
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(left + 16, cover_y, item)
        cover_y -= 16

    # Bottom gold stripe
    pdf.setFillColor(gold)
    pdf.rect(0, 0, width, 4, stroke=0, fill=1)

    _footer(pdf, width, page_no)
    pdf.showPage()
    page_no += 1

    # ── CONTENT PAGES ────────────────────────────────────────────
    pdf.setFillColor(charcoal)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    y = height - 56

    def section_header(title: str, subtitle: str = "") -> None:
        nonlocal y
        pdf.setFillColor(gold)
        pdf.setFont("Helvetica-Bold", 15)
        pdf.drawString(left, y, title)
        y -= 16
        if subtitle:
            pdf.setFillColor(soft)
            pdf.setFont("Helvetica", 10)
            y = _draw_lines(pdf, _split_lines(pdf, subtitle, "Helvetica", 10, usable_width), left, y, 12, "Helvetica", 10, soft)
            y -= 6

    def text_block(text: str, color=muted, font_name: str = "Helvetica", font_size: int = 11, leading: int = 14, inset: int = 0) -> None:
        nonlocal y, page_no
        lines = _split_lines(pdf, text, font_name, font_size, usable_width - inset)
        y, page_no = _ensure_space(pdf, width, height, y, max(40, len(lines) * leading + 10), page_no, charcoal)
        y = _draw_lines(pdf, lines, left + inset, y, leading, font_name, font_size, color)

    def bullet_list(items: List[str], bullet_color=blue) -> None:
        nonlocal y, page_no
        for item in items:
            lines = _split_lines(pdf, item, "Helvetica", 10, usable_width - 26)
            y, page_no = _ensure_space(pdf, width, height, y, len(lines) * 13 + 14, page_no, charcoal)
            pdf.setFillColor(bullet_color)
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(left, y, "•")
            y = _draw_lines(pdf, lines, left + 14, y, 13, "Helvetica", 10, muted)
            y -= 3

    def beat_card(idx: int, beat: BeatEntry) -> None:
        nonlocal y, page_no
        continuity = _CONTINUITY_NOTES.get(beat.beat, _DEFAULT_CONTINUITY)
        dialogue_lines = _split_lines(pdf, f"{beat.cue_line}: {beat.dialogue}", "Helvetica", 9, usable_width - 28)
        cont_lines = _split_lines(pdf, continuity, "Helvetica", 9, usable_width - 28)
        card_h = 46 + len(dialogue_lines) * 11 + len(cont_lines) * 11 + 14
        card_h = max(card_h, 100)

        y, page_no = _ensure_space(pdf, width, height, y, card_h + 10, page_no, charcoal)
        pdf.setFillColor(panel)
        pdf.roundRect(left, y - card_h + 10, usable_width, card_h, 12, stroke=0, fill=1)

        pdf.setFillColor(gold)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(left + 14, y - 8, f"Scene Beat {idx}  —  {beat.beat}")

        pdf.setFillColor(soft)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(left + 14, y - 22, f"{beat.reference}  |  {beat.scene_heading}")

        block_y = y - 40
        pdf.setFillColor(white)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left + 14, block_y, "Script line")
        block_y -= 12
        block_y = _draw_lines(pdf, dialogue_lines, left + 14, block_y, 11, "Helvetica", 9, muted)

        pdf.setFillColor(white)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left + 14, block_y - 2, "Continuity note")
        block_y -= 14
        _draw_lines(pdf, cont_lines, left + 14, block_y, 11, "Helvetica", 9, muted)
        y -= card_h + 10

    if not beats:
        section_header("No matching dialogue found", "The extraction did not detect dialogue for the requested role.")
        text_block("Try entering the role exactly as it appears in the script, or paste cleaner text if the file formatting stripped the cues.")
        _footer(pdf, width, page_no)
        pdf.save()
        return output_path

    section_header("Full Role Snapshot", "Booked-mode view using the current extraction.")
    for item in _role_snapshot(character_name, beats):
        text_block(item)
        y -= 2

    y -= 8
    section_header("Relationship and Function Read", "How the role currently presents from the detected dialogue path.")
    for item in _relationship_lines(character_name, beats):
        text_block(item)
        y -= 2

    y -= 8
    section_header("Continuity Rules", "How to hold the role consistently from scene to scene.")
    for item in _continuity_lines(beats):
        text_block(item)
        y -= 2

    y -= 10
    section_header("Role Performance Priorities")
    bullet_list([
        "Track whether the character is gaining control, holding control, or losing control.",
        "Protect consistent behavior across repeated scene pressure rather than reinventing the role every time.",
        "Let pace, patience, and openness shift with circumstance while core identity stays stable.",
    ])

    # All beats — no cap
    y -= 8
    section_header("Scene Journey", f"All {len(beats)} detected beat{'s' if len(beats) != 1 else ''} as role prep cards.")
    for idx, beat in enumerate(beats, start=1):
        beat_card(idx, beat)

    y -= 6
    section_header("Set-Ready Checklist")
    bullet_list([
        "Know where this scene sits in the role's pressure line before you play it.",
        "Track whether the character is entering hot, steady, or already compromised.",
        "Hold body language, voice rhythm, and listening behavior consistently across takes.",
        "Mark any scene where the role's pressure level clearly rises or drops.",
        "Protect continuity more than novelty.",
    ])

    _footer(pdf, width, page_no)
    pdf.save()
    return output_path
