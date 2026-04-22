#!/usr/bin/env python3
"""
layout_engine.py — cinematic story-map aware slide planner

Purpose:
    Converts approved_brain_output.json into slide_plan.json using the unified
    story-map fields, while staging long-form synopsis as a mini-trailer arc:
        1) Setup
        2) Escalation
        3) Turn / Consequence

    V2 API LAYOUT SYSTEM:
        - keeps text OUT of generated images
        - uses full-bleed image-first layout strategy
        - adds smart overlay-box metadata for deck builder
        - maps slide stage -> better composition presets
        - preserves existing slide planning behavior
        - remains provider-agnostic for text/image APIs

Usage:
    python3 layout_engine.py /path/to/approved_brain_output.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

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
    parts = re.split(r"(?<=[.!?])\s+", text)
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
            "image_path": clean(item.get("image_path")),
            "image_name": clean(item.get("image_name")),
            "image_source": clean(item.get("image_source")),
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
            "image_path": clean(item.get("image_path", "")),
            "image_name": clean(item.get("image_name", "")),
            "image_source": clean(item.get("image_source", "")),
            "selected_option_id": clean(item.get("selected_option_id", "")),
        }

    return lookup


def lookup_image_meta(slide_title: str, image_lookup: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    key = clean(slide_title).lower()
    if key in image_lookup:
        return dict(image_lookup[key])

    if key and key not in image_lookup and "title" in image_lookup:
        return dict(image_lookup["title"])

    return {
        "image_query": "",
        "image_tags": [],
        "image_score": None,
        "image_options": [],
        "image_path": "",
        "image_name": "",
        "image_source": "none",
        "selected_option_id": "",
    }


def clip_text(text: str, max_chars: int) -> str:
    text = clean(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def sanitize_slide_title(title: str) -> str:
    title = clean(title).replace("#", "")
    return title or "Untitled"


def stage_to_layout(stage: str, current_layout: str) -> str:
    stage = clean(stage).lower()
    mapping = {
        "title": "hero_full_bleed",
        "closing": "hero_full_bleed",
        "hook": "split_left_text",
        "setup": "bottom_story_card",
        "escalation": "split_right_text",
        "turn": "split_left_text",
        "aftermath": "bottom_story_card",
        "character": "character_focus",
        "world": "quote_overlay",
        "tone": "quote_overlay",
        "themes": "quote_overlay",
        "conflict": "split_left_text",
        "stakes": "split_right_text",
        "engine": "bottom_story_card",
        "why_now": "bottom_story_card",
        "market": "clean_grid",
    }
    return mapping.get(stage, clean(current_layout) or "split_left_text")


def box_for_layout(layout: str) -> Dict[str, Any]:
    presets: Dict[str, Dict[str, Any]] = {
        "hero_full_bleed": {
            "x": 0.055, "y": 0.68, "w": 0.89, "h": 0.22,
            "align": "left", "theme": "dark_glass"
        },
        "split_left_text": {
            "x": 0.055, "y": 0.14, "w": 0.39, "h": 0.68,
            "align": "left", "theme": "dark_glass"
        },
        "split_right_text": {
            "x": 0.555, "y": 0.14, "w": 0.39, "h": 0.68,
            "align": "left", "theme": "dark_glass"
        },
        "bottom_story_card": {
            "x": 0.055, "y": 0.61, "w": 0.89, "h": 0.25,
            "align": "left", "theme": "dark_glass"
        },
        "character_focus": {
            "x": 0.055, "y": 0.69, "w": 0.54, "h": 0.19,
            "align": "left", "theme": "dark_glass"
        },
        "quote_overlay": {
            "x": 0.14, "y": 0.36, "w": 0.72, "h": 0.22,
            "align": "center", "theme": "light_glass"
        },
        "clean_grid": {
            "x": 0.08, "y": 0.17, "w": 0.84, "h": 0.60,
            "align": "left", "theme": "clean"
        },
    }
    return presets.get(layout, presets["split_left_text"])


def title_size(layout: str) -> int:
    if layout == "hero_full_bleed":
        return 28
    if layout == "quote_overlay":
        return 24
    if layout == "clean_grid":
        return 22
    return 21


def body_size(layout: str) -> int:
    if layout == "hero_full_bleed":
        return 13
    if layout == "clean_grid":
        return 15
    if layout == "quote_overlay":
        return 17
    return 15


def build_layout_meta(slide_title: str, body: str, layout: str, stage: str, image_meta: Dict[str, Any]) -> Dict[str, Any]:
    image_path = clean(image_meta.get("image_path", ""))
    image_name = clean(image_meta.get("image_name", ""))
    image_source = clean(image_meta.get("image_source", "none")) or "none"
    selected_option_id = clean(image_meta.get("selected_option_id", ""))

    overlay_box = box_for_layout(layout)

    return {
        "background_image": image_path,
        "use_background_image": bool(image_path),
        "full_bleed": True,
        "overlay_box": overlay_box,
        "text_style": {
            "title_size": title_size(layout),
            "body_size": body_size(layout),
            "title_weight": "bold",
            "body_weight": "regular",
            "line_spacing": 1.1,
            "tracking": 0,
            "case": "auto",
        },
        "render_hints": {
            "apply_gradient_scrim": True,
            "safe_margins": True,
            "respect_aspect_ratio": True,
            "crop_mode": "cover",
            "avoid_text_on_faces": True,
            "prefer_empty_space_for_text": True,
        },
        "layout_version": "v2_api_layout_system",
        "deck_layout_family": layout,
        "display_title": sanitize_slide_title(slide_title),
        "display_body": body,
        "display_stage": clean(stage),
        "image_path": image_path,
        "image_name": image_name,
        "image_source": image_source,
        "selected_option_id": selected_option_id,
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

    slide_title = sanitize_slide_title(title)
    stage_clean = clean(stage)
    smart_layout = stage_to_layout(stage_clean, layout)
    image_meta = lookup_image_meta(slide_title, image_lookup)

    if smart_layout == "hero_full_bleed":
        clipped_body = clip_text(body, 140)
    elif smart_layout in {"split_left_text", "split_right_text", "bottom_story_card"}:
        clipped_body = clip_text(body, 260)
    elif smart_layout == "character_focus":
        clipped_body = clip_text(body, 220)
    elif smart_layout == "quote_overlay":
        clipped_body = clip_text(body, 180)
    else:
        clipped_body = clip_text(body, 320)

    layout_meta = build_layout_meta(slide_title, clipped_body, smart_layout, stage_clean, image_meta)

    plan.append({
        "title": slide_title,
        "body": clipped_body,
        "layout": smart_layout,
        "stage": stage_clean,
        "image_query": clean(image_meta.get("image_query", "")),
        "image_tags": image_meta.get("image_tags", []) if isinstance(image_meta.get("image_tags"), list) else [],
        "image_score": image_meta.get("image_score"),
        "image_options": normalize_image_options(image_meta.get("image_options", [])),
        "image_path": layout_meta["image_path"],
        "image_name": layout_meta["image_name"],
        "image_source": layout_meta["image_source"],
        "selected_option_id": layout_meta["selected_option_id"],
        "full_bleed": layout_meta["full_bleed"],
        "use_background_image": layout_meta["use_background_image"],
        "background_image": layout_meta["background_image"],
        "overlay_box": layout_meta["overlay_box"],
        "text_style": layout_meta["text_style"],
        "render_hints": layout_meta["render_hints"],
        "layout_version": layout_meta["layout_version"],
        "deck_layout_family": layout_meta["deck_layout_family"],
        "display_title": layout_meta["display_title"],
        "display_body": layout_meta["display_body"],
        "display_stage": layout_meta["display_stage"],
    })


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
    setting = clean(data.get("setting", ""))
    world_body = setting if setting else world
    logline = clean(data.get("logline", ""))
    tagline = clean(data.get("tagline", "")) or logline
    synopsis = clean(data.get("synopsis", ""))

    story_engine = clean(data.get("story_engine", ""))
    core_conflict = clean(data.get("core_conflict", ""))
    reversal = clean(data.get("reversal", ""))
    why_this_movie = clean(data.get("why_this_movie", ""))

    hook = clean(data.get("hook", ""))
    stakes = clean(data.get("stakes", ""))
    tone = clean(data.get("tone", ""))

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

    add_slide(plan, image_lookup, title, tagline, "title", "title")
    add_slide(plan, image_lookup, "Logline", logline, "analysis", "hook")

    for slide in split_synopsis_cinematic(synopsis):
        add_slide(plan, image_lookup, slide["title"], slide["body"], slide["layout"], slide["stage"])

    protagonist_summary = clean(data.get("protagonist_summary", ""))
    protagonist_body = protagonist_summary or protagonist
    add_slide(plan, image_lookup, protagonist or "Protagonist", protagonist_body, "text", "character")
    add_slide(plan, image_lookup, "World", world_body, "text", "world")
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

    comparable_films = data.get("comparable_films", [])
    if comparable_films:
        comp_titles = "  ·  ".join(
            f.get("title", str(f)) if isinstance(f, dict) else str(f)
            for f in comparable_films[:3]
        )
        add_slide(plan, image_lookup, "Comparables", comp_titles, "analysis", "market")

    market_projections = data.get("market_projections", {})
    if market_projections:
        proj_parts = []
        if market_projections.get("estimated_budget_tier"):
            proj_parts.append(f"Budget: {market_projections['estimated_budget_tier']}")
        if market_projections.get("distribution_angle"):
            proj_parts.append(f"Distribution: {market_projections['distribution_angle']}")
        if market_projections.get("awards_potential"):
            proj_parts.append(f"Awards: {market_projections['awards_potential']}")
        if market_projections.get("franchise_potential"):
            proj_parts.append(f"Franchise: {market_projections['franchise_potential']}")
        if proj_parts:
            add_slide(plan, image_lookup, "Market Projections", "  ·  ".join(proj_parts), "analysis", "market")

    tagline = clean(data.get("tagline") or data.get("story_engine") or "")
    closing_body = tagline[:120] if tagline else title
    add_slide(plan, image_lookup, "Closing", closing_body, "title", "closing")

    seen_bodies: set[str] = set()
    deduped: List[Dict[str, Any]] = []
    for slide in plan:
        body = slide.get("body", "")
        layout = slide.get("layout", "")
        if layout in {"hero_full_bleed", "title"} or body not in seen_bodies:
            deduped.append(slide)
            if body:
                seen_bodies.add(body)
    plan = deduped

    return {
        "title": title,
        "slides": plan,
        "slide_count": len(plan),
        "layout_engine_version": "v2_api_layout_system",
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
    print(f"✅ Layout engine: {plan.get('layout_engine_version', 'unknown')}")


if __name__ == "__main__":
    main()
