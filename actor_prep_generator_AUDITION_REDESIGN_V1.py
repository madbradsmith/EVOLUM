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


def _extract_scene_context(beats: List[BeatEntry]) -> Tuple[str, str, str]:
    if not beats:
        return ("No scene context detected.", "No active scene context detected.", "No forward scene movement detected.")

    first = beats[0]
    last = beats[-1]
    unique_scenes = list(dict.fromkeys([b.scene_heading for b in beats if b.scene_heading]))

    before = f"The sides place {first.cue_line.title()} inside {first.scene_heading.lower()}. The scene appears to begin with existing pressure already in motion rather than a neutral start."
    during = f"Across {len(beats)} detected speaking beat{'s' if len(beats) != 1 else ''}, the role is consistently operating through {first.beat.lower()} and scene management rather than passive reaction."
    after = f"The material ends in {last.scene_heading.lower()}. Based on the final beat, the next movement likely continues the same pressure line instead of fully resolving it."

    if len(unique_scenes) > 1:
        after = f"The sides move across {len(unique_scenes)} distinct locations, which suggests escalation or a shift in control after the current beat sequence ends."

    return before, during, after


def _role_snapshot(character_name: str, beats: List[BeatEntry]) -> List[str]:
    beat_names = [b.beat for b in beats]
    top = beat_names[0] if beat_names else "Hold Authority"
    count = len(beats)
    return [
        f"{character_name.title()} reads as a role that is tested through pressure, control, and moment-to-moment decision making.",
        f"Detected {count} playable beat{'s' if count != 1 else ''}, with the strongest recurring energy landing closest to '{top}'.",
        "This appears to be a role where clarity, confidence, and listening will usually win more than pushing for volume.",
    ]


def _self_tape_checklist() -> List[str]:
    return [
        "Frame chest-up or mid-shot unless casting says otherwise.",
        "Pick exact eyeline marks and tape them before recording.",
        "Keep the background clean and the sound easy to understand.",
        "Do not rush the pauses. Let the thought finish before the next line.",
        "Dress in a way that hints at the role without turning it into costume.",
        "Check file name, instructions, and upload deadline before sending.",
    ]


def build_actor_prep_pdf(script_text: str, character_name: str, output_path: str | Path, brain_data: Optional[Dict] = None) -> Path:
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
    pdf.drawString(left, height - 80, "AUDITION")
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
    beat_label = f"{len(beats)} speaking beat{'s' if len(beats) != 1 else ''} detected" if beats else "No beats detected"
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
        "60-Second Role Snapshot",
        "What Casting Is Likely Testing",
        "Inferences from the Sides",
        f"Full Beat Breakdown  ({len(beats)} beats)",
        "Self-Tape Success Checklist",
        "Mistakes to Avoid",
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
        dialogue_lines = _split_lines(pdf, f"{beat.cue_line}: {beat.dialogue}", "Helvetica", 9, usable_width - 28)
        note_lines = _split_lines(pdf, beat.playable_note, "Helvetica", 9, usable_width - 28)
        card_h = 46 + len(dialogue_lines) * 11 + len(note_lines) * 11 + 14
        card_h = max(card_h, 100)

        y, page_no = _ensure_space(pdf, width, height, y, card_h + 10, page_no, charcoal)
        pdf.setFillColor(panel)
        pdf.roundRect(left, y - card_h + 10, usable_width, card_h, 12, stroke=0, fill=1)

        pdf.setFillColor(gold)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(left + 14, y - 8, f"Beat {idx}  —  {beat.beat}")

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
        pdf.drawString(left + 14, block_y - 2, "Playable note")
        block_y -= 14
        _draw_lines(pdf, note_lines, left + 14, block_y, 11, "Helvetica", 9, muted)
        y -= card_h + 10

    if not beats:
        section_header("No matching dialogue found", "The extraction did not detect dialogue for the requested role.")
        text_block("Try entering the role exactly as it appears in the script, or paste cleaner text if the file formatting stripped the cues.")
        _footer(pdf, width, page_no)
        pdf.save()
        return output_path

    # Role snapshot
    section_header("60-Second Role Snapshot", "Fast read for actors working on deadline.")
    for item in _role_snapshot(character_name, beats):
        text_block(item)
        y -= 2

    y -= 10
    section_header("What Casting Is Likely Testing")
    bullet_list([
        "Can you establish the role quickly without over-explaining it?",
        "Can you hold pressure and authority without forcing the performance?",
        "Can you let pauses, reactions, and listening do some of the work?",
    ])

    before, during, after = _extract_scene_context(beats)

    y -= 8
    section_header("Inferences from the Sides", "Built only from the material currently visible in the packet.")
    labels = [("Before the scene", before), ("What is happening now", during), ("Likely next movement", after)]
    for label, value in labels:
        y, page_no = _ensure_space(pdf, width, height, y, 54, page_no, charcoal)
        pdf.setFillColor(blue)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, y, label)
        y -= 14
        text_block(value, color=muted, font_name="Helvetica", font_size=10, leading=13)
        y -= 4

    y, page_no = _ensure_space(pdf, width, height, y, 80, page_no, charcoal)
    pdf.setFillColor(panel)
    pdf.roundRect(left, y - 56, usable_width, 54, 12, stroke=0, fill=1)
    pdf.setFillColor(gold)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(left + 14, y - 18, "Why this matters")
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(left + 14, y - 34, "It helps you enter the scene with a moment-before, not just a line reading.")
    y -= 74

    # Beats — all of them
    y = _new_page(pdf, width, height, page_no, charcoal)
    page_no += 1

    section_header("Playable Beat Breakdown", f"All {len(beats)} detected beat{'s' if len(beats) != 1 else ''} from the current sides.")
    for idx, beat in enumerate(beats, start=1):
        beat_card(idx, beat)

    # Self-tape page
    y = _new_page(pdf, width, height, page_no, charcoal)
    page_no += 1

    section_header("Self-Tape Success Checklist", "Short, practical, and deadline-friendly.")
    bullet_list(_self_tape_checklist(), bullet_color=gold)

    y -= 10
    section_header("Mistakes to Avoid")
    bullet_list([
        "Do not play the result before the listening is alive.",
        "Do not over-push volume when the scene can be won through certainty.",
        "Do not treat all beats the same. Let the pressure shift show up.",
    ], bullet_color=blue)

    _footer(pdf, width, page_no)
    pdf.save()
    return output_path
