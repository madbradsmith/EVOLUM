#!/usr/bin/env python3
"""
layout_engine.py — cinematic story-map aware slide planner

Purpose:
    Converts approved_brain_output.json into slide_plan.json using the unified
    story-map fields, while staging long-form synopsis as a mini-trailer arc:
        1) Setup
        2) Escalation
        3) Turn / Consequence

    PATCH V1:
        - carries forward image-plan metadata into slide_plan.json
        - supports image_options from newer brain outputs
        - keeps existing slide planning behavior intact

Usage:
    python3 layout_engine.py /path/to/approved_brain_output.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_INPUT = Path("approved_brain_output.json")
DEFAULT_OUTPUT = Path("slide_plan.json")

MIN_WORDS = 24
TARGET_WORDS = 44
MAX_WORDS = 68


def clean(text: Any) -> str:
    return " ".join(str(text or "").split()).strip()


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ===== USER UPLOAD OVERRIDES START ====================
def apply_user_upload_overrides(data: Dict[str, Any], input_path: Path) -> Dict[str, Any]:
    override_candidates = [
        input_path.parent / "user_upload_context.json",
        input_path.parent / "input" / "user_upload_context.json",
        input_path.parent / "pipeline" / "user_upload_context.json",
        Path.cwd() / "user_upload_context.json",
        Path.cwd() / "input" / "user_upload_context.json",
        Path.cwd() / "pipeline" / "user_upload_context.json",
    ]

    for candidate in override_candidates:
        if not candidate.exists():
            continue
        try:
            override_payload = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue

        submitted_logline = clean(override_payload.get("logline", ""))
        submitted_synopsis = clean(override_payload.get("synopsis", ""))

        if submitted_logline:
            data["logline"] = submitted_logline
            print(f"✅ Using uploaded logline override: {candidate}")
        if submitted_synopsis:
            data["synopsis"] = submitted_synopsis
            print(f"✅ Using uploaded synopsis override: {candidate}")

        return data

    return data
# ===== USER UPLOAD OVERRIDES END ======================


def word_count(text: str) -> int:
    return len(clean(text).split())


def sentence_split(text: str) -> List[str]:
    text = clean(text)
    if not text:
        return []
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def can_merge(a: str, b: str, max_words: int = MAX_WORDS) -> bool:
    return word_count(f"{a} {b}") <= max_words


def group_sentences(sentences: List[str]) -> List[str]:
    if not sentences:
        return []

    chunks: List[str] = []
    current = ""

    for sent in sentences:
        sent = clean(sent)
        if not current:
            current = sent
            continue

        trial = f"{current} {sent}".strip()
        current_words = word_count(current)
        trial_words = word_count(trial)

        if current_words < MIN_WORDS and trial_words <= MAX_WORDS:
            current = trial
            continue

        if trial_words <= TARGET_WORDS:
            current = trial
            continue

        chunks.append(current)
        current = sent

    if current:
        chunks.append(current)

    merged: List[str] = []
    for chunk in chunks:
        if merged and word_count(chunk) < MIN_WORDS and can_merge(merged[-1], chunk):
            merged[-1] = f"{merged[-1]} {chunk}".strip()
        else:
            merged.append(chunk)

    if len(merged) >= 2 and word_count(merged[-1]) < MIN_WORDS and can_merge(merged[-2], merged[-1]):
        merged[-2] = f"{merged[-2]} {merged[-1]}".strip()
        merged.pop()

    return merged


def normalize_image_options(options: Any) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    if not isinstance(options, list):
        return normalized

    for item in options:
        if not isinstance(item, dict):
            continue
        normalized.append({
            "rank": item.get("rank"),
            "score": item.get("score"),
            "option_id": clean(item.get("option_id")),
            "label": clean(item.get("label")),
            "focus": clean(item.get("focus")),
            "image_query": clean(item.get("image_query")),
            "image_tags": item.get("image_tags", []) if isinstance(item.get("image_tags"), list) else [],
        })
    return normalized


def build_image_plan_lookup(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    image_plan = data.get("image_plan", [])
    lookup: Dict[str, Dict[str, Any]] = {}

    if not isinstance(image_plan, list):
        return lookup

    for item in image_plan:
        if not isinstance(item, dict):
            continue

        title_key = clean(item.get("slide_title", "")).lower()
        if not title_key:
            continue

        lookup[title_key] = {
            "image_query": clean(item.get("image_query", "")),
            "image_tags": item.get("image_tags", []) if isinstance(item.get("image_tags"), list) else [],
            "image_score": item.get("image_score"),
            "image_options": normalize_image_options(item.get("image_options", [])),
        }

    return lookup


def lookup_image_meta(slide_title: str, image_lookup: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    key = clean(slide_title).lower()
    if key in image_lookup:
        return dict(image_lookup[key])

    # Map title slide to image plan's "Title" entry.
    if key and key not in image_lookup and "title" in image_lookup:
        return dict(image_lookup["title"])

    return {
        "image_query": "",
        "image_tags": [],
        "image_score": None,
        "image_options": [],
    }


def add_slide(
    plan: List[Dict[str, Any]],
    image_lookup: Dict[str, Dict[str, Any]],
    title: str,
    body: str,
    layout: str = "text",
    stage: str = "",
) -> None:
    body = clean(body)
    if layout != "title" and not body:
        return

    slide_title = clean(title)
    image_meta = lookup_image_meta(slide_title, image_lookup)

    plan.append({
        "title": slide_title,
        "body": body,
        "layout": layout,
        "stage": clean(stage),
        "image_query": clean(image_meta.get("image_query", "")),
        "image_tags": image_meta.get("image_tags", []) if isinstance(image_meta.get("image_tags"), list) else [],
        "image_score": image_meta.get("image_score"),
        "image_options": normalize_image_options(image_meta.get("image_options", [])),
    })


def first_sentence(text: str) -> str:
    parts = sentence_split(text)
    return parts[0] if parts else ""


def split_synopsis_cinematic(text: str) -> List[Dict[str, str]]:
    """
    Break synopsis into 2-4 cinematic story beats instead of bland text chunks.
    Priority:
        setup -> escalation -> consequence/turn
    """
    sentences = group_sentences(sentence_split(text))
    if not sentences:
        return []

    labels = [
        ("Synopsis", "setup", "narrative_setup"),
        ("Synopsis (2)", "escalation", "narrative_escalation"),
        ("Synopsis (3)", "turn", "narrative_turn"),
        ("Synopsis (4)", "aftermath", "narrative_aftermath"),
    ]

    slides: List[Dict[str, str]] = []
    for idx, chunk in enumerate(sentences):
        title, stage, layout = labels[min(idx, len(labels) - 1)]
        slides.append({
            "title": title,
            "body": chunk,
            "stage": stage,
            "layout": layout,
        })
    return slides


def build_slide_plan(data: Dict[str, Any]) -> Dict[str, Any]:
    title = clean(data.get("title", "Project"))
    protagonist = clean(data.get("protagonist", ""))
    world = clean(data.get("world", ""))
    logline = clean(data.get("logline", ""))
    tagline = clean(data.get("tagline", "")) or logline
    synopsis = clean(data.get("synopsis", ""))

    story_engine = clean(data.get("story_engine", ""))
    core_conflict = clean(data.get("core_conflict", ""))
    reversal = clean(data.get("reversal", ""))
    why_this_movie = clean(data.get("why_this_movie", ""))

    hook = clean(data.get("hook", ""))
    stakes = clean(data.get("stakes", ""))
    tone = clean(data.get("tone", "")) or world

    themes = data.get("themes", "")
    if isinstance(themes, list):
        themes_text = "\n".join(clean(x) for x in themes if clean(x))
    else:
        themes_text = clean(themes)

    theme_field = clean(data.get("theme", ""))
    if not why_this_movie:
        why_this_movie = theme_field or reversal

    plan: List[Dict[str, Any]] = []
    image_lookup = build_image_plan_lookup(data)

    # Title and core deck spine
    add_slide(plan, image_lookup, title, tagline, "title", "title")
    add_slide(plan, image_lookup, "Logline", logline, "analysis", "hook")

    # Cinematic synopsis progression
    for slide in split_synopsis_cinematic(synopsis):
        add_slide(plan, image_lookup, slide["title"], slide["body"], slide["layout"], slide["stage"])

    protagonist_summary = clean(data.get("protagonist_summary", ""))
    protagonist_body = protagonist_summary or protagonist
    add_slide(plan, image_lookup, protagonist or "Protagonist", protagonist_body, "text", "character")
    add_slide(plan, image_lookup, "World", world, "text", "world")
    if hook and hook != logline:
        add_slide(plan, image_lookup, "Hook", hook, "analysis", "hook")
    if core_conflict:
        add_slide(plan, image_lookup, "Conflict", core_conflict, "analysis", "conflict")
    if stakes and stakes != core_conflict:
        add_slide(plan, image_lookup, "Stakes", stakes, "analysis", "stakes")
    add_slide(plan, image_lookup, "Tone", tone, "text", "tone")

    if story_engine:
        add_slide(plan, image_lookup, "Story Engine", story_engine, "analysis", "engine")
    if reversal:
        add_slide(plan, image_lookup, "Reversal", reversal, "analysis", "turn")
    if themes_text:
        add_slide(plan, image_lookup, "Themes", themes_text, "text", "themes")
    if why_this_movie and why_this_movie not in {story_engine, core_conflict, logline}:
        add_slide(plan, image_lookup, "Why This Movie", why_this_movie, "analysis", "why_now")

    # Remove any slides whose body text is an exact duplicate of an earlier slide
    seen_bodies: set[str] = set()
    deduped: List[Dict[str, Any]] = []
    for slide in plan:
        body = slide.get("body", "")
        layout = slide.get("layout", "")
        if layout == "title" or body not in seen_bodies:
            deduped.append(slide)
            if body:
                seen_bodies.add(body)
    plan = deduped

    return {
        "title": title,
        "slides": plan,
        "slide_count": len(plan),
    }


def main() -> None:
    input_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_INPUT
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        raise SystemExit(1)

    data = read_json(input_path)
    data = apply_user_upload_overrides(data, input_path)
    plan = build_slide_plan(data)
    DEFAULT_OUTPUT.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print("✅ Full slide plan generated")
    print(f"✅ Slide count: {plan['slide_count']}")


if __name__ == "__main__":
    main()
