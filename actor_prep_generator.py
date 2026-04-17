from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
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


def _infer_beat(dialogue: str, scene_heading: str) -> tuple[str, str, str]:
    lower = dialogue.strip().lower()

    if any(k in lower for k in ["who", "what", "where", "why", "how"]):
        return (
            "Pressure for Information",
            "The character is pushing for answers and trying to control what gets revealed.",
            "Play the question like a tactic, not simple curiosity."
        )
    if any(k in lower for k in ["calm down", "sit down", "listen", "hold on", "wait"]):
        return (
            "Control the Room",
            "The character is taking command and forcing the scene back under control.",
            "Use stillness and certainty rather than volume."
        )
    if any(k in lower for k in ["don't", "do not", "can't", "cannot", "won't", "stop"]):
        return (
            "Set a Boundary",
            "The character is drawing a line and making the other person feel it.",
            "Keep the delivery clipped and definite."
        )
    if any(k in lower for k in ["good", "okay", "alright", "cool"]):
        return (
            "Reset and Move Forward",
            "The character absorbs the moment quickly and redirects the action.",
            "Treat it like a professional pivot, not relief."
        )
    if scene_heading and ("OFFICE" in scene_heading.upper() or "INTERROGATION" in scene_heading.upper()):
        return (
            "Apply Pressure",
            "The character is reading the other person and pressing for leverage.",
            "Let the intelligence do the work."
        )
    return (
        "Hold Authority",
        "The character is managing the scene from a position of control.",
        "Keep it grounded, specific, and in command."
    )


def extract_beats(script_text: str, character_name: str) -> list[BeatEntry]:
    script_text = _clean_text(script_text)
    lines = script_text.split("\n")
    target = normalize_character_name(character_name)

    beats: list[BeatEntry] = []
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
                dialogue_lines: list[str] = []

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


def _draw_wrapped(pdf: canvas.Canvas, text: str, x: int, y: int, max_width: int, font_name: str = "Helvetica", font_size: int = 10, leading: int = 13) -> int:
    words = text.split()
    line = ""
    pdf.setFont(font_name, font_size)

    for word in words:
        trial = f"{line} {word}".strip()
        if pdf.stringWidth(trial, font_name, font_size) <= max_width:
            line = trial
        else:
            pdf.drawString(x, y, line)
            y -= leading
            line = word

    if line:
        pdf.drawString(x, y, line)
        y -= leading

    return y


def build_actor_prep_pdf(script_text: str, character_name: str, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    beats = extract_beats(script_text, character_name)

    pdf = canvas.Canvas(str(output_path), pagesize=LETTER)
    width, height = LETTER
    left, right = 52, width - 52
    y = height - 52

    def new_page() -> None:
        nonlocal y
        pdf.showPage()
        y = height - 52

    def ensure_space(lines_needed: int = 6) -> None:
        nonlocal y
        if y - (lines_needed * 14) < 52:
            new_page()

    pdf.setTitle(f"Actor Prep - {character_name}")
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(left, y, f"Actor Preparation — {character_name}")
    y -= 26

    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, y, "Powered by Developum AI Engine")
    y -= 22

    if not beats:
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(left, y, "No matching dialogue found.")
        y -= 18
        pdf.setFont("Helvetica", 11)
        y = _draw_wrapped(
            pdf,
            "Try entering the role exactly as it appears in the script, or paste cleaner script text if the upload formatting was inconsistent.",
            left,
            y,
            int(right - left),
            font_size=11,
        )
        pdf.save()
        return output_path

    pdf.setFont("Helvetica", 11)
    y = _draw_wrapped(
        pdf,
        f"This packet identifies scene-by-scene playable moments for {character_name}. Each beat includes the script reference, subtext, and a practical performance note.",
        left,
        y,
        int(right - left),
        font_size=11,
    )
    y -= 10

    for idx, beat in enumerate(beats, start=1):
        ensure_space(12)

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(left, y, f"Beat {idx} — {beat.beat}")
        y -= 16

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, y, f"{beat.reference}  |  {beat.scene_heading}")
        y -= 14

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, y, "Script Line:")
        y -= 13
        y = _draw_wrapped(pdf, f"{beat.cue_line}: {beat.dialogue}", left + 10, y, int(right - left - 10), font_size=10)

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, y, "Subtext:")
        y -= 13
        y = _draw_wrapped(pdf, beat.subtext, left + 10, y, int(right - left - 10), font_size=10)

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, y, "Playable Note:")
        y -= 13
        y = _draw_wrapped(pdf, beat.playable_note, left + 10, y, int(right - left - 10), font_size=10)

        y -= 10
        pdf.line(left, y, right, y)
        y -= 12

    pdf.save()
    return output_path
