# SINGLE BRAIN ORCHESTRATOR — AI-NATIVE VERSION
# Character stat counting is mechanical. All story analysis via Claude Sonnet.

import sys
import json
import os
import re
from pathlib import Path
from pypdf import PdfReader

APP_DIR = Path(__file__).resolve().parent
OUT = Path(__file__).parent / "approved_brain_output.json"

SCENE_PREFIXES = ("INT.", "EXT.", "INT/", "EXT/")
NON_CHARACTER_PHRASES = {
    "OPENING CREDITS", "END CREDITS", "TITLE CARD",
    "FADE TO BLACK", "FADE IN", "FADE OUT", "FADE UP", "FADE UP ON",
    "CUT TO", "CUT TO:", "TIME CUT", "TIME CUT:",
    "SMASH CUT TO", "SMASH CUT TO:", "DISSOLVE TO", "DISSOLVE TO:",
    "MATCH CUT TO", "MATCH CUT TO:", "BACK TO SCENE", "BACK TO PRESENT",
    "THE END", "BLACK", "END", "SUPER", "INSERT", "INTERCUT",
    "CONTINUED", "MONTAGE", "END MONTAGE", "SERIES OF SHOTS",
    "LATER", "MOMENTS LATER", "ANGLE ON", "CLOSE ON", "WIDE ON",
    "FLASHBACK", "FLASH ON", "FLASH OFF", "SUBTITLE APPEARS BELOW"
}
BAD_TOKENS = {
    "INT", "EXT", "CUT", "FADE", "UP", "ON", "TIME", "FLASH",
    "ANGLE", "WIDE", "CLOSE", "SCENE", "PRESENT"
}
SUSPICIOUS_SINGLE_WORDS = {
    "VIDEO", "TRUNK", "ROOM", "CAR", "DOOR", "HOUSE", "STREET", "WINDOW", "PHONE", "RADIO", "TV",
    "TELEVISION", "HALLWAY", "KITCHEN", "BEDROOM", "BATHROOM", "OFFICE", "DESK", "TABLE", "CHAIR",
    "GARAGE", "PORCH", "ALLEY", "ROAD", "FREEWAY", "AIRPORT", "STATION", "PLANE", "TRAIN", "BUS",
    "MOTEL", "HOTEL", "STORE", "SHOP", "BAR", "CLUB", "YARD", "PARKING", "LOT", "ROOF", "BASEMENT",
    "ATTIC", "ELEVATOR", "STAIRS", "TRUCK", "VAN", "SUV", "COUCH", "BED", "SOFA", "CAMERA",
    "SCREEN", "MONITOR", "FILE", "BOX", "BAG", "SUITCASE", "MAP", "EXCHANGE", "SESSION", "GROCERY"
}
GENERIC_ROLE_WORDS = {
    "MAN", "WOMAN", "GUY", "GIRL", "BOY", "CUSTOMER", "DRIVER", "PASSENGER", "CASHIER",
    "CLERK", "COP", "OFFICER", "WAITER", "WAITRESS", "BARTENDER", "HOST", "HOSTESS",
    "VOICE", "ANNOUNCER", "DISPATCH", "OPERATOR"
}
PRONOUN_WORDS = {
    "I", "ME", "MY", "MINE", "MYSELF",
    "YOU", "YOUR", "YOURS", "YOURSELF", "YOURSELVES",
    "HE", "HIM", "HIS", "HIMSELF",
    "SHE", "HER", "HERS", "HERSELF",
    "IT", "ITS", "ITSELF",
    "WE", "US", "OUR", "OURS", "OURSELVES",
    "THEY", "THEM", "THEIR", "THEIRS", "THEMSELVES"
}
SHOT_PREFIXES = {"CU", "ECU", "WS", "MS", "MLS", "MCU", "POV", "OS", "O.S.", "V.O.", "VO", "ANGLE", "ON", "UNDER", "OVER", "MEDIUM", "CLOSE", "WIDE"}


def normalize(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def extract_title(text: str) -> str:
    for line in text.splitlines():
        clean = normalize(line).replace("﻿", "")
        if clean:
            return clean
    return "Untitled"


def is_scene_heading(line: str) -> bool:
    return line.upper().startswith(SCENE_PREFIXES)


def clean_name(name: str) -> str:
    name = re.sub(r"\(.*?\)", "", name).strip()
    name = name.rstrip(":")
    name = re.sub(r"[.]+$", "", name).strip()
    name = re.sub(r"\s{2,}", " ", name)
    return name


def is_caps_candidate(line: str) -> bool:
    if not line or line != line.upper():
        return False
    line = normalize(line)
    if len(line) < 2 or len(line) > 40:
        return False
    if any(ch.isdigit() for ch in line):
        return False
    if "+" in line:
        return False
    if line.count("(") > 1 or line.count(")") > 1:
        return False
    return bool(re.fullmatch(r"[A-Z .'/\-():!?&]+", line))


def is_valid_character_name(name: str) -> bool:
    if not name:
        return False
    name = clean_name(name).strip()
    if not name:
        return False
    if any(ch.isdigit() for ch in name):
        return False
    if "+" in name:
        return False
    if len(name) < 2:
        return False
    if name in NON_CHARACTER_PHRASES:
        return False
    if name in GENERIC_ROLE_WORDS or name in PRONOUN_WORDS:
        return False
    if len(name.split()) > 3:
        return False
    if len(re.findall(r"[A-Z]", name)) < 2:
        return False
    if re.search(r"[^A-Z '\-.]", name):
        return False
    return True


def salvage_candidate(upper: str):
    tokens = upper.split()
    if not tokens or upper in NON_CHARACTER_PHRASES:
        return None
    if tokens[0] in {"A", "AN", "THE"}:
        return None
    if len(tokens) == 2 and tokens[0] in SHOT_PREFIXES:
        return tokens[1]
    if len(tokens) == 3 and tokens[1] == "AND":
        return [tokens[0], tokens[2]]
    return upper


def looks_like_dialogue_follow(lines, i: int) -> int:
    for j in range(i + 1, min(i + 5, len(lines))):
        nxt = normalize(lines[j])
        if not nxt:
            continue
        if is_scene_heading(nxt):
            return 0
        if nxt == nxt.upper():
            return 0
        return 1
    return 0


def analyze_dialogue_characters(text: str):
    lines = text.splitlines()
    counts, first_seen, dialogue_support = {}, {}, {}
    for i, raw in enumerate(lines):
        line = normalize(raw)
        if not line or i < 6 or is_scene_heading(line) or not is_caps_candidate(line):
            continue
        cleaned = clean_name(line).upper()
        salvaged = salvage_candidate(cleaned)
        if salvaged is None:
            continue
        candidates = salvaged if isinstance(salvaged, list) else [salvaged]
        for c in candidates:
            c = clean_name(c).upper()
            if not c or c in NON_CHARACTER_PHRASES or len(c.split()) > 3:
                continue
            if any(tok in BAD_TOKENS for tok in c.split()):
                continue
            if len(c.split()) == 1 and c in SUSPICIOUS_SINGLE_WORDS:
                continue
            if c in GENERIC_ROLE_WORDS or c in PRONOUN_WORDS:
                continue
            if not is_valid_character_name(c):
                continue
            counts[c] = counts.get(c, 0) + 1
            if c not in first_seen:
                first_seen[c] = i
            dialogue_support[c] = dialogue_support.get(c, 0) + looks_like_dialogue_follow(lines, i)
    return counts, first_seen, dialogue_support


def is_likely_action_line(line: str) -> bool:
    if not line:
        return False
    if is_scene_heading(line):
        return False
    if line == line.upper():
        return False
    if line.endswith(":"):
        return False
    return True


def extract_action_names(text: str):
    lines = text.splitlines()
    action_counts = {}
    action_first_seen = {}
    for i, raw in enumerate(lines):
        line = normalize(raw)
        if not is_likely_action_line(line):
            continue
        names = re.findall(r"\b([A-Z][a-z]{2,})\b", line)
        for name in names:
            upper = name.upper()
            if upper in GENERIC_ROLE_WORDS or upper in BAD_TOKENS or upper in SUSPICIOUS_SINGLE_WORDS:
                continue
            if upper in PRONOUN_WORDS or upper in {"THE", "A", "AN"}:
                continue
            action_counts[upper] = action_counts.get(upper, 0) + 1
            if upper not in action_first_seen:
                action_first_seen[upper] = i
        full_names = re.findall(r"\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\b", line)
        for full in full_names:
            upper = full.upper()
            if any(tok in GENERIC_ROLE_WORDS or tok in PRONOUN_WORDS for tok in upper.split()):
                continue
            action_counts[upper] = action_counts.get(upper, 0) + 1
            if upper not in action_first_seen:
                action_first_seen[upper] = i
    return action_counts, action_first_seen


def merge_character_signals(dialogue_counts, dialogue_first, dialogue_support, action_counts, action_first):
    all_names = set(dialogue_counts) | set(action_counts)
    scored = []

    for name in all_names:
        d = dialogue_counts.get(name, 0)
        a = action_counts.get(name, 0)
        first = min(dialogue_first.get(name, 99999), action_first.get(name, 99999))
        score = 0
        score += d * 2
        score += dialogue_support.get(name, 0) * 3
        score += a * 4
        if first < 80:
            score += 4
        elif first < 160:
            score += 2
        if d > 0 and a > 0:
            score += 4
        if a >= 3:
            score += 5
        if d == 1 and a == 0:
            score -= 2
        scored.append((name, score, d, a, first))

    scored.sort(key=lambda x: (-x[1], x[4], x[0]))

    ordered = []
    seen = set()
    for name, score, d, a, first in scored:
        if name in seen:
            continue
        tokens = name.split()
        drop = False
        if len(tokens) == 1:
            for other, _, od, oa, _ in scored:
                if other == name:
                    continue
                other_tokens = other.split()
                if len(other_tokens) > 1 and tokens[0] in other_tokens and (od + oa) >= (d + a):
                    drop = True
                    break
        if not drop:
            seen.add(name)
            ordered.append(name)

    stats = {
        name: {
            "dialogue_count": dialogue_counts.get(name, 0),
            "action_count": action_counts.get(name, 0),
            "first_seen": min(dialogue_first.get(name, 99999), action_first.get(name, 99999)),
        }
        for name in ordered
    }
    return ordered[:8], stats


# ─── AI-NATIVE STORY ANALYSIS ────────────────────────────────────────────────

def _world_category(world: str) -> str:
    """Map Claude's free-form world description to a visual/layout category."""
    w = world.lower()
    if any(t in w for t in ["espionage", "spy", "covert", "assassin", "secret agent", "operative"]):
        return "action_espionage"
    if any(t in w for t in ["rideshare", "cab driver", "contained urban", "urban thriller"]):
        return "contained_urban"
    if any(t in w for t in ["courtroom", "trial", "tribunal", "military court"]):
        return "legal_courtroom"
    if any(t in w for t in ["legal", "law school"]) and any(t in w for t in ["comedy", "romance", "romantic"]):
        return "romantic_comedy"
    if any(t in w for t in ["legal", "law"]):
        return "legal_courtroom"
    if any(t in w for t in ["fantasy", "medieval", "kingdom", "wizard", "dragon", "satire"]):
        return "fantasy_satire"
    if any(t in w for t in ["romantic comedy", "rom-com", "romance", "love story", "sorority"]):
        return "romantic_comedy"
    if any(t in w for t in ["nightlife", "club scene", "party"]):
        return "nightlife_comedy"
    if any(t in w for t in ["sports", "basketball", "football", "soccer", "athlete", "coach"]):
        return "sports_drama"
    if any(t in w for t in ["crime", "heist", "gangster", "cartel", "mob", "drug"]):
        return "crime_drama"
    if any(t in w for t in ["thriller", "suspense"]):
        return "thriller"
    return "drama"


_ANALYSIS_SYSTEM = """You are a Hollywood screenplay analyst. Read the screenplay and return a story map as a single raw JSON object.

CRITICAL RULES:
- Return ONLY the JSON — no markdown, no code fences, no extra text.
- Every string value must be CONCISE — under 20 words unless explicitly noted.
- Lists must have at most the number of items shown in the example.
- The entire JSON response must fit in 3500 tokens. Be tight.

{
  "title": "title as written in the screenplay",
  "world": "specific genre + world in 6-10 words (e.g. 'warm law-school romantic comedy', 'slow-burn Appalachian crime thriller')",
  "tone": "3-5 tone words, comma-separated",
  "setting": "where this story takes place, 10 words max",
  "time_frame": "time span of the story, 6 words max",
  "logline": "protagonist + pressure + stakes, under 40 words",
  "tagline": "marketing hook, under 10 words",
  "synopsis": "what happens and what is at stake — 80-100 words total",
  "theme": "what the story is really about, under 15 words",
  "story_engine": "what drives THIS story forward, 10 words max",
  "core_conflict": "the central tension, 10 words max",
  "reversal": "the key reversal or revelation, 12 words max",
  "protagonist": "protagonist name exactly as in the script",
  "protagonist_summary": "who they are and what drives them, under 20 words",
  "characters": ["top 5 character names exactly as written"],
  "character_arcs": {
    "CHARACTER_NAME": {
      "beginning_state": "8 words max",
      "end_state": "8 words max",
      "transformation": "10 words max"
    }
  },
  "relationship_leverage_map": [
    {"character": "name", "dynamic": "6 words", "function": "8 words"}
  ],
  "act_breakdown": {
    "act_1": {"summary": "15 words max", "key_beats": ["6 words", "6 words"], "turning_point": "8 words"},
    "act_2": {"summary": "15 words max", "key_beats": ["6 words", "6 words"], "turning_point": "8 words"},
    "act_3": {"summary": "15 words max", "key_beats": ["6 words", "6 words"], "turning_point": "8 words"}
  },
  "executive_summary": "producer-facing pitch, 2 sentences max",
  "commercial_positioning": "how this sells today, 15 words max",
  "packaging_potential": "what casting makes this work, 12 words max",
  "character_leverage": "commercial and awards appeal, 12 words max",
  "comparable_films": [
    {"title": "Film Title", "why": "10 words", "budget_tier": "low/mid/studio", "box_office": "$XM"},
    {"title": "Film Title", "why": "10 words", "budget_tier": "low/mid/studio", "box_office": "$XM"},
    {"title": "Film Title", "why": "10 words", "budget_tier": "low/mid/studio", "box_office": "$XM"}
  ],
  "tone_comparables": ["Film 1", "Film 2", "Film 3"],
  "audience_profile": ["segment 1", "segment 2", "segment 3"],
  "market_projections": {
    "budget_range": "dollar range",
    "distribution_angle": "streaming-first / theatrical / limited",
    "awards_potential": "honest 6-word assessment",
    "audience_reach": "who sees this, 8 words",
    "franchise_potential": "yes/no + 6 words"
  },
  "strength_index": {"concept": 8, "character": 9, "marketability": 7, "originality": 8},
  "strengths": ["strength 1, 8 words", "strength 2, 8 words", "strength 3, 8 words"],
  "development_risks": ["risk 1, 8 words", "risk 2, 8 words", "risk 3, 8 words"],
  "actor_objective": "what the lead must accomplish, 12 words",
  "role_arc_map": ["stage 1", "stage 2", "stage 3", "stage 4", "stage 5"],
  "pressure_ladder": ["beat 1", "beat 2", "beat 3", "beat 4", "beat 5"],
  "emotional_continuity": ["note 1, 10 words", "note 2, 10 words"],
  "playable_tactics": ["tactic 1", "tactic 2", "tactic 3", "tactic 4"],
  "emotional_triggers": ["trigger 1", "trigger 2", "trigger 3"],
  "audition_danger_zones": ["pitfall 1, 8 words", "pitfall 2, 8 words"],
  "reader_chemistry_tips": ["tip 1, 10 words", "tip 2, 10 words"],
  "memorization_beats": ["beat 1, 8 words", "beat 2, 8 words"],
  "costume_behavior_clues": ["clue 1, 8 words", "clue 2, 8 words"],
  "set_ready_checklist": ["item 1, 8 words", "item 2, 8 words", "item 3, 8 words"],
  "visual_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5", "keyword6"]
}"""


def _write_brain_tokens(usage) -> None:
    _work = os.environ.get("DAI_WORK_DIR", "")
    _f = Path(_work) / "pipeline_tokens.json" if _work else APP_DIR / "pipeline_tokens.json"
    try:
        existing = json.loads(_f.read_text(encoding="utf-8")) if _f.exists() else {}
    except Exception:
        existing = {}
    existing["brain"] = {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "model": "claude-haiku-4-5-20251001",
    }
    try:
        _f.write_text(json.dumps(existing), encoding="utf-8")
    except Exception:
        pass


def analyze_script_with_claude(text: str, title: str, char_stats: dict) -> dict:
    """Single Claude Haiku call — generates all story fields from the actual screenplay."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_story_map(title, list(char_stats.keys()))
    try:
        import anthropic
    except ImportError:
        return _fallback_story_map(title, list(char_stats.keys()))

    char_hint = ", ".join(list(char_stats.keys())[:12])
    # Cap screenplay at 120K chars (~30K tokens) to keep API time under Gunicorn timeout
    script_body = text[:120_000] if len(text) > 120_000 else text
    user_msg = (
        f"Title (from first line): {title}\n"
        f"Mechanically-detected character candidates (hints only — correct as needed): {char_hint}\n\n"
        f"FULL SCREENPLAY:\n{script_body}"
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=[{"type": "text", "text": _ANALYSIS_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = next((b.text for b in message.content if hasattr(b, "text")), "")
        if not raw:
            return _fallback_story_map(title, list(char_stats.keys()))
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw.rstrip())
        _write_brain_tokens(message.usage)
        return json.loads(raw)
    except Exception as e:
        print(f"⚠️  Claude analysis failed: {e}")
        return _fallback_story_map(title, list(char_stats.keys()))


def _fallback_story_map(title: str, characters: list) -> dict:
    """Minimal fallback when Claude API is unavailable."""
    protagonist = characters[0].title() if characters else "Protagonist"
    chars = [c.title() for c in characters[:6]]
    return {
        "title": title,
        "world": "feature / drama",
        "tone": "grounded, dramatic",
        "setting": "a contained dramatic environment",
        "time_frame": "contained timeframe",
        "logline": f"{protagonist} is forced into an impossible situation with no easy way out.",
        "tagline": "Some things can't be undone.",
        "synopsis": f"{title} follows {protagonist} through a story of pressure, consequence, and change.",
        "theme": "Identity is tested when pressure reveals what we're really made of.",
        "story_engine": f"{protagonist} is forced into a situation they cannot escape.",
        "core_conflict": f"{protagonist} must make an impossible choice.",
        "reversal": "The truth behind the situation is different from what was first assumed.",
        "protagonist": protagonist,
        "protagonist_summary": f"{protagonist} carries the weight of this story.",
        "protagonist_profile": {"name": protagonist, "summary": f"{protagonist} carries the weight of this story."},
        "characters": chars,
        "character_arcs": {},
        "relationship_leverage_map": [],
        "act_breakdown": {
            "act_1": {"summary": "Setup", "key_beats": [], "turning_point": ""},
            "act_2": {"summary": "Confrontation", "key_beats": [], "turning_point": ""},
            "act_3": {"summary": "Resolution", "key_beats": [], "turning_point": ""},
        },
        "executive_summary": f"{title} is a drama built around {protagonist}.",
        "commercial_positioning": "Character-driven story with clear pitch angles.",
        "packaging_potential": "Depends on a strong central performance.",
        "character_leverage": "The protagonist's journey drives commercial appeal.",
        "comparable_films": [],
        "tone_comparables": [],
        "audience_profile": ["General film audiences", "Character-driven story viewers"],
        "market_projections": {
            "budget_range": "",
            "distribution_angle": "",
            "awards_potential": "",
            "audience_reach": "",
            "franchise_potential": "",
        },
        "strength_index": {"concept": 7, "character": 7, "marketability": 6, "originality": 7},
        "strengths": [],
        "development_risks": [],
        "character_stats": {c: {"dialogue_count": 0, "action_count": 0, "first_seen": 99999} for c in chars},
        "actor_objective": f"Move the scene forward with clear intention while protecting what {protagonist} most wants.",
        "role_arc_map": ["setup", "pressure", "adaptation", "reversal", "resolution"],
        "pressure_ladder": ["low pressure", "rising tension", "complication", "peak pressure", "release"],
        "emotional_continuity": ["Track where confidence cracks.", "Let pressure affect pace before volume."],
        "playable_tactics": ["Deflect", "Pressure", "Reframe", "Hold", "Pivot"],
        "emotional_triggers": ["Rejection", "Pressure", "Exposure", "Uncertainty"],
        "audition_danger_zones": ["Overplaying intention", "Pushing emotion too early", "Ignoring listening beats"],
        "reader_chemistry_tips": ["Pick fixed eyelines.", "Let interruptions feel live.", "Stay responsive to pace shifts."],
        "memorization_beats": ["Opening beat", "First pressure turn", "Status shift", "Control reset", "Exit beat"],
        "costume_behavior_clues": ["Costume supports role clarity.", "Behavior aligns with status and pressure level."],
        "set_ready_checklist": ["Know the objective.", "Understand the relationship stakes.", "Prepare the physical life of the character."],
        "visual_keywords": ["cinematic", "dramatic", "grounded", "pressure", "environment"],
    }


def build_story_map(text: str) -> dict:
    # Step 1: Mechanical extraction — character stat counting only
    title = extract_title(text)
    dialogue_counts, dialogue_first, dialogue_support = analyze_dialogue_characters(text)
    action_counts, action_first = extract_action_names(text)
    characters_ranked, character_stats = merge_character_signals(
        dialogue_counts, dialogue_first, dialogue_support, action_counts, action_first
    )

    # Step 2: Claude reads the full screenplay and generates everything
    print("🧠 Sending screenplay to Claude for analysis...")
    story_map = analyze_script_with_claude(text, title, character_stats)

    # Step 3: Merge mechanical stats into Claude's character list
    claude_characters = story_map.get("characters") or characters_ranked[:6]
    merged_stats = {}
    for c in claude_characters:
        upper_c = c.upper()
        if upper_c in character_stats:
            merged_stats[c] = character_stats[upper_c]
        else:
            matched = next(
                (k for k in character_stats if k in upper_c or upper_c in k), None
            )
            merged_stats[c] = character_stats.get(
                matched, {"dialogue_count": 0, "action_count": 0, "first_seen": 99999}
            )
    story_map["character_stats"] = merged_stats

    # Ensure protagonist_profile exists
    protagonist = story_map.get("protagonist", "")
    if protagonist and "protagonist_profile" not in story_map:
        story_map["protagonist_profile"] = {
            "name": protagonist,
            "summary": story_map.get("protagonist_summary", ""),
        }

    # Layout fields computed from Claude's world + tone strings
    story_map["presentation_modes"] = infer_presentation_scores(story_map)
    story_map["presentation_controls"] = infer_presentation_controls(story_map)
    story_map["layout_strategy"] = infer_layout_strategy(story_map)
    story_map["slide_blueprint"] = infer_slide_blueprint(story_map)
    story_map["document_layouts"] = infer_document_layouts(story_map)

    return story_map


# ─── LAYOUT / PRESENTATION ───────────────────────────────────────────────────

def infer_document_layouts(story_map: dict) -> dict:
    cat = _world_category(story_map.get("world", ""))
    primary_mode = ((story_map.get("presentation_modes") or {}).get("primary_mode") or "character_heart")
    strategy = story_map.get("layout_strategy") or {}

    analysis_style = "clean_cinematic_report"
    actor_style = "character_workbook_dark"
    audition_style = "fast_turnaround_brief"
    booked_style = "deep_role_dossier"
    chart_style = "gold_on_dark"

    if cat == "legal_courtroom" or primary_mode == "prestige_authority":
        analysis_style = "prestige_report"
        actor_style = "institutional_character_brief"
        audition_style = "measured_authority_sides"
        booked_style = "prestige_role_bible"
        chart_style = "formal_gold_grid"
    elif cat in ("contained_urban", "thriller", "action_espionage") or primary_mode == "tension_pressure":
        analysis_style = "thriller_intelligence_report"
        actor_style = "pressure_character_brief"
        audition_style = "urgent_sides_brief"
        booked_style = "contained_thriller_role_map"
        chart_style = "signal_on_dark"
    elif cat == "fantasy_satire" or primary_mode == "spectacle_play":
        analysis_style = "storybook_analysis_report"
        actor_style = "playful_character_brief"
        audition_style = "characterful_sides_brief"
        booked_style = "fantasy_role_bible"
        chart_style = "ornate_gold_cards"
    elif primary_mode == "character_heart":
        analysis_style = "human_story_report"
        actor_style = "relationship_character_brief"
        audition_style = "intimate_sides_brief"
        booked_style = "emotional_role_bible"
        chart_style = "warm_neutral_report"

    return {
        "analysis_report": {
            "layout_family": analysis_style,
            "cover_style": strategy.get("headline_style", "statement"),
            "chart_style": chart_style,
            "section_density": strategy.get("text_density", "medium"),
        },
        "actor_prep_report": {
            "layout_family": actor_style,
            "beat_style": "scene_playable_cards",
            "callout_style": chart_style,
            "section_density": "medium_high",
        },
        "audition_analyzer": {
            "layout_family": audition_style,
            "delivery_mode": "quickpack",
            "section_density": "fast_read",
            "callout_style": chart_style,
        },
        "booked_role_analyzer": {
            "layout_family": booked_style,
            "delivery_mode": "deep_prep",
            "section_density": "expanded",
            "callout_style": chart_style,
        },
    }


def infer_presentation_scores(story_map: dict) -> dict:
    world = (story_map.get("world") or "").lower()
    tone = (story_map.get("tone") or "").lower()
    story_engine = (story_map.get("story_engine") or "").lower()
    conflict = (story_map.get("core_conflict") or "").lower()
    synopsis = (story_map.get("synopsis") or "").lower()
    reversal = (story_map.get("reversal") or "").lower()
    text_blob = " ".join([world, tone, story_engine, conflict, synopsis, reversal])

    scores = {
        "prestige_authority": 10,
        "tension_pressure": 10,
        "character_heart": 10,
        "spectacle_play": 10,
    }

    prestige_terms = [
        "courtroom", "legal", "military", "institution", "authority", "verdict",
        "hierarchy", "command", "political", "corporate", "prestige", "procedural",
        "under oath", "truth", "moral", "discipline"
    ]
    tension_terms = [
        "thriller", "pressure", "danger", "fear", "suspicion", "escalate", "paranoid",
        "crime", "buried", "risk", "threat", "urgent", "nocturnal", "claustrophobic",
        "chase", "survive", "consequence", "trap"
    ]
    heart_terms = [
        "family", "identity", "relationship", "emotional", "heart", "redemption",
        "human", "vulnerability", "love", "grief", "friendship", "belonging",
        "personal", "career or", "what kind of", "who they are"
    ]
    spectacle_terms = [
        "fantasy", "comedy", "satire", "adventure", "kingdom", "pageantry", "world",
        "spectacle", "playful", "witty", "absurd", "chaos", "storybook", "epic",
        "theatrical", "action", "big", "cinematic"
    ]

    for term in prestige_terms:
        if term in text_blob:
            scores["prestige_authority"] += 7
    for term in tension_terms:
        if term in text_blob:
            scores["tension_pressure"] += 7
    for term in heart_terms:
        if term in text_blob:
            scores["character_heart"] += 6
    for term in spectacle_terms:
        if term in text_blob:
            scores["spectacle_play"] += 7

    cat = _world_category(world)
    if cat == "legal_courtroom":
        scores["prestige_authority"] += 30
        scores["tension_pressure"] += 10
    elif cat == "action_espionage":
        scores["tension_pressure"] += 28
        scores["spectacle_play"] += 8
    elif cat == "contained_urban":
        scores["tension_pressure"] += 28
        scores["character_heart"] += 6
    elif cat == "fantasy_satire":
        scores["spectacle_play"] += 30
        scores["character_heart"] += 8
    elif cat == "nightlife_comedy":
        scores["spectacle_play"] += 24
        scores["character_heart"] += 8
    elif cat == "sports_drama":
        scores["character_heart"] += 18
        scores["prestige_authority"] += 6
        scores["tension_pressure"] += 8
    elif cat == "romantic_comedy":
        scores["character_heart"] += 22
        scores["spectacle_play"] += 8

    if any(t in tone for t in ["playful", "witty", "satirical", "heightened", "chaotic"]):
        scores["spectacle_play"] += 16
    if any(t in tone for t in ["tense", "sharp", "paranoid", "volatile", "claustrophobic"]):
        scores["tension_pressure"] += 16
    if any(t in tone for t in ["morally charged", "procedural", "restrained", "focused"]):
        scores["prestige_authority"] += 14
    if any(t in tone for t in ["emotional", "warm", "human", "grounded"]):
        scores["character_heart"] += 14

    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    primary_mode = ordered[0][0]
    secondary_mode = ordered[1][0]

    return {
        "presentation_scores": scores,
        "primary_mode": primary_mode,
        "secondary_mode": secondary_mode,
    }


def infer_presentation_controls(story_map: dict) -> dict:
    modes = story_map.get("presentation_modes") or {}
    primary = modes.get("primary_mode", "character_heart")
    secondary = modes.get("secondary_mode", "tension_pressure")

    controls = {
        "layout_energy": "medium",
        "discipline_level": "medium",
        "image_dominance": "medium_high",
        "rhythm_bias": "balanced",
    }

    if primary == "prestige_authority":
        controls.update({"layout_energy": "measured", "discipline_level": "high", "image_dominance": "medium", "rhythm_bias": "disciplined"})
    elif primary == "tension_pressure":
        controls.update({"layout_energy": "high", "discipline_level": "medium_high", "image_dominance": "high", "rhythm_bias": "tight"})
    elif primary == "character_heart":
        controls.update({"layout_energy": "medium", "discipline_level": "medium", "image_dominance": "medium", "rhythm_bias": "intimate"})
    elif primary == "spectacle_play":
        controls.update({"layout_energy": "high", "discipline_level": "medium_low", "image_dominance": "high", "rhythm_bias": "elastic"})

    if secondary == "character_heart" and controls["discipline_level"] in {"medium_high", "high"}:
        controls["discipline_level"] = "medium"
    if secondary == "prestige_authority" and primary == "spectacle_play":
        controls["discipline_level"] = "medium"
    if secondary == "spectacle_play" and primary == "tension_pressure":
        controls["layout_energy"] = "high"

    return controls


def infer_layout_strategy(story_map: dict) -> dict:
    cat = _world_category(story_map.get("world", ""))
    tone = (story_map.get("tone") or "").lower()
    synopsis = (story_map.get("synopsis") or "").lower()

    layout_style = "cinematic_grounded"
    text_density = "medium"
    image_priority = "high"
    pacing = "measured"
    visual_energy = "controlled"
    slide_rhythm = "balanced"
    headline_style = "statement"
    composition_bias = "image_forward"

    if cat == "action_espionage":
        layout_style = "cinematic_high_tension"
        text_density = "low"
        image_priority = "very_high"
        pacing = "fast"
        visual_energy = "volatile"
        slide_rhythm = "punchy"
        headline_style = "hook"
        composition_bias = "full_bleed"
    elif cat == "contained_urban":
        layout_style = "contained_nocturnal"
        text_density = "low"
        image_priority = "very_high"
        pacing = "tight"
        visual_energy = "claustrophobic"
        slide_rhythm = "minimal"
        headline_style = "hook"
        composition_bias = "full_bleed"
    elif cat == "legal_courtroom":
        layout_style = "institutional_cinematic"
        text_density = "medium"
        image_priority = "high"
        pacing = "measured"
        visual_energy = "restrained_intense"
        slide_rhythm = "balanced"
        headline_style = "argument"
        composition_bias = "split_text_image"
    elif cat == "fantasy_satire":
        layout_style = "storybook_satirical"
        text_density = "medium"
        image_priority = "high"
        pacing = "playful"
        visual_energy = "heightened"
        slide_rhythm = "varied"
        headline_style = "characterful"
        composition_bias = "illustrative"
    elif cat == "romantic_comedy":
        layout_style = "romantic_cinematic"
        text_density = "medium"
        image_priority = "high"
        pacing = "warm"
        visual_energy = "emotional"
        slide_rhythm = "flowing"
        headline_style = "characterful"
        composition_bias = "image_forward"
    elif cat == "nightlife_comedy":
        layout_style = "neon_social_chaos"
        text_density = "low"
        image_priority = "very_high"
        pacing = "fast"
        visual_energy = "chaotic"
        slide_rhythm = "punchy"
        headline_style = "hook"
        composition_bias = "full_bleed"
    elif cat == "sports_drama":
        layout_style = "athletic_prestige"
        text_density = "medium"
        image_priority = "high"
        pacing = "driving"
        visual_energy = "focused"
        slide_rhythm = "balanced"
        headline_style = "statement"
        composition_bias = "hero_image"
    elif cat == "crime_drama":
        layout_style = "urban_crime_cinematic"
        text_density = "medium"
        image_priority = "high"
        pacing = "measured"
        visual_energy = "tense"
        slide_rhythm = "balanced"
        headline_style = "hook"
        composition_bias = "full_bleed"
    elif cat == "thriller":
        layout_style = "cinematic_suspense"
        text_density = "low"
        image_priority = "very_high"
        pacing = "tight"
        visual_energy = "volatile"
        slide_rhythm = "punchy"
        headline_style = "hook"
        composition_bias = "full_bleed"

    if "morally charged" in tone or "procedural" in tone:
        text_density = "medium_high"
        slide_rhythm = "disciplined"
    if "playful" in tone or "satirical" in tone:
        slide_rhythm = "elastic"
    if "chaotic" in tone or "energetic" in tone:
        pacing = "fast"
    if "nocturnal" in tone or "paranoid" in tone:
        composition_bias = "full_bleed"
    if len(synopsis.split()) > 85 and text_density == "low":
        text_density = "medium"

    return {
        "layout_style": layout_style,
        "text_density": text_density,
        "image_priority": image_priority,
        "pacing": pacing,
        "visual_energy": visual_energy,
        "slide_rhythm": slide_rhythm,
        "headline_style": headline_style,
        "composition_bias": composition_bias,
    }


def infer_slide_blueprint(story_map: dict) -> dict:
    cat = _world_category(story_map.get("world", ""))
    strategy = story_map.get("layout_strategy") or {}

    slide_count = 12
    if strategy.get("image_priority") == "very_high":
        slide_count = 14
    if cat == "legal_courtroom":
        slide_count = 13
    if cat == "fantasy_satire":
        slide_count = 14

    opening_style = "title_then_hook"
    headline_style = strategy.get("headline_style", "statement")
    if headline_style == "argument":
        opening_style = "title_then_premise"
    if headline_style == "characterful":
        opening_style = "title_then_world"

    return {
        "recommended_slide_count": slide_count,
        "opening_style": opening_style,
        "mid_deck_focus": strategy.get("composition_bias", "image_forward"),
        "closing_style": "punchline_with_heart" if cat == "nightlife_comedy" else "statement",
    }


# ─── IMAGE TERM FUNCTIONS ────────────────────────────────────────────────────

def base_image_terms(story_map: dict) -> list[str]:
    cat = _world_category(story_map.get("world", ""))
    visual_keywords = story_map.get("visual_keywords") or []
    terms = []

    if cat == "action_espionage":
        terms.extend(["covert", "surveillance", "domestic_tension", "high_stakes", "cinematic"])
    elif cat == "contained_urban":
        terms.extend(["urban", "night", "car", "tension", "isolation"])
    elif cat == "legal_courtroom":
        terms.extend(["courtroom", "institution", "authority", "moral_pressure"])
    elif cat == "fantasy_satire":
        terms.extend(["kingdom", "pageantry", "satire", "fantasy", "court_chaos"])
    elif cat == "romantic_comedy":
        terms.extend(["romance", "connection", "warmth", "social_world", "emotional_honesty"])
    elif cat == "nightlife_comedy":
        terms.extend(["nightlife", "social_chaos", "party", "awkwardness", "city_night"])
    elif cat == "sports_drama":
        terms.extend(["sports", "court", "locker_room", "pressure", "competition"])
    elif cat == "crime_drama":
        terms.extend(["urban", "danger", "night", "street", "pressure"])
    elif cat == "thriller":
        terms.extend(["tension", "shadow", "isolation", "urban", "pressure"])
    else:
        terms.extend(["grounded", "dramatic", "environment"])

    terms.extend([k for k in visual_keywords[:4] if k not in terms])
    return terms


def slide_visual_terms(slide_name: str, story_map: dict) -> list[str]:
    cat = _world_category(story_map.get("world", ""))
    protagonist = slugify(story_map.get("protagonist", ""))
    tone_terms = [slugify(t) for t in (story_map.get("tone") or "").split(",") if t.strip()]
    base_terms = base_image_terms(story_map)

    mapping = {
        "Title": ["establishing", "cinematic", "world"],
        "Logline": ["wide", "establishing", "mood"],
        "Synopsis": ["pressure", "environment", "story_world"],
        "Protagonist": ["isolation", "implied_presence", protagonist],
        "Antagonist": ["pressure", "rival_energy", "confrontation_space"],
        "Supporting Characters": ["group_dynamic", "world_detail", "relationship_space"],
        "Theme": ["symbolic", "atmosphere", "identity"],
        "Tone": ["mood", "texture", "lighting"],
        "World": ["environment", "place", "lived_in"],
        "Conflict Engine": ["tension", "separation", "friction"],
        "Stakes": ["scale", "emptiness", "consequence"],
        "Why This Film": ["cinematic", "elevated", "statement"],
        "Audience": ["relatable_world", "emotion", "aspiration"],
        "Visual Style": ["visual_texture", "lighting", "composition"],
        "Comparables": ["premium", "cinematic", "recognizable_lane"],
        "Market Position": ["commercial", "elevated", "broad_appeal"],
        "Director Vision": ["intimate", "framing", "movement"],
        "Casting Ideas": ["presence", "silhouette", "human_energy"],
        "Production Scope": ["contained", "practical", "real_world"],
        "Closing Statement": ["emotional_finality", "impact", "resonance"],
    }

    cat_slide_terms = {
        "action_espionage": {
            "world_base": ["surveillance", "night_operation", "hidden_identity"],
            "character": ["split_life", "domestic_cover", "covert_pressure"],
            "theme": ["explosive_reveal", "family_risk", "high_stakes"],
        },
        "contained_urban": {
            "world_base": ["streetlights", "car_interior", "night"],
            "character": ["windshield", "rearview", "implied_presence"],
            "theme": ["pressure", "isolation", "urban"],
        },
        "legal_courtroom": {
            "world_base": ["courtroom_wide", "military_formality", "institutional_space"],
            "character": ["witness_stand", "interrogation_room", "command_pressure"],
            "theme": ["truth_under_oath", "moral_weight", "verdict_energy"],
        },
        "fantasy_satire": {
            "world_base": ["castle_wide", "ceremonial_absurdity", "storybook_scale"],
            "character": ["throne_room", "comic_intrigue", "royal_misrule"],
            "theme": ["satirical_pageantry", "kingdom_chaos", "comic_resolution"],
        },
        "romantic_comedy": {
            "world_base": ["warm_interior", "social_setting", "romance_connection"],
            "character": ["intimate_moment", "social_pressure", "friendship_bond"],
            "theme": ["love_realization", "emotional_honesty", "comic_warmth"],
        },
        "nightlife_comedy": {
            "world_base": ["club_exterior", "velvet_rope", "city_lights"],
            "character": ["dancefloor", "awkward_party", "social_pressure"],
            "theme": ["afterparty_fallout", "neon_regret", "comic_release"],
        },
        "sports_drama": {
            "world_base": ["empty_court", "arena", "night"],
            "character": ["locker_room", "hallway", "quiet_pressure"],
            "theme": ["scoreboard", "gym", "after_hours"],
        },
        "crime_drama": {
            "world_base": ["street_night", "urban_grit", "danger_interior"],
            "character": ["confrontation", "underworld_space", "tension"],
            "theme": ["consequence", "moral_cost", "street_truth"],
        },
    }

    terms = []
    terms.extend(base_terms)
    terms.extend(tone_terms[:3])
    terms.extend(mapping.get(slide_name, ["cinematic", "environment"]))

    cat_terms = cat_slide_terms.get(cat, {})
    if slide_name in {"Title", "Logline", "World"}:
        terms.extend(cat_terms.get("world_base", []))
    elif slide_name in {"Protagonist", "Antagonist", "Supporting Characters", "Conflict Engine", "Stakes"}:
        terms.extend(cat_terms.get("character", []))
    elif slide_name in {"Theme", "Closing Statement"}:
        terms.extend(cat_terms.get("theme", []))

    seen = set()
    ordered = []
    for t in terms:
        if not t:
            continue
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered


def score_terms_for_slide(slide_name: str, story_map: dict) -> dict:
    cat = _world_category(story_map.get("world", ""))
    primary_mode = story_map.get("presentation_modes", {}).get("primary_mode", "")
    secondary_mode = story_map.get("presentation_modes", {}).get("secondary_mode", "")
    protagonist = slugify(story_map.get("protagonist", ""))
    weights: dict[str, int] = {}

    def bump(term: str, points: int):
        if not term:
            return
        weights[term] = weights.get(term, 0) + points

    slide_weights = {
        "Title": [("establishing", 18), ("cinematic", 16), ("world", 14)],
        "Logline": [("mood", 15), ("wide", 14), ("establishing", 12)],
        "Synopsis": [("story_world", 16), ("pressure", 14), ("environment", 12)],
        "Protagonist": [(protagonist, 20), ("implied_presence", 16), ("isolation", 14)],
        "Antagonist": [("rival_energy", 16), ("confrontation_space", 14), ("pressure", 10)],
        "Supporting Characters": [("group_dynamic", 16), ("relationship_space", 14), ("world_detail", 10)],
        "Theme": [("symbolic", 18), ("identity", 14), ("atmosphere", 12)],
        "Tone": [("mood", 18), ("lighting", 14), ("texture", 12)],
        "World": [("place", 16), ("environment", 16), ("lived_in", 12)],
        "Conflict Engine": [("tension", 18), ("friction", 14), ("separation", 12)],
        "Stakes": [("consequence", 18), ("scale", 14), ("emptiness", 10)],
        "Why This Film": [("statement", 16), ("elevated", 14), ("cinematic", 12)],
        "Audience": [("emotion", 16), ("relatable_world", 12), ("aspiration", 10)],
        "Visual Style": [("composition", 16), ("lighting", 14), ("visual_texture", 12)],
        "Comparables": [("premium", 14), ("cinematic", 12), ("recognizable_lane", 10)],
        "Market Position": [("commercial", 14), ("broad_appeal", 12), ("elevated", 10)],
        "Director Vision": [("framing", 16), ("movement", 12), ("intimate", 10)],
        "Casting Ideas": [("presence", 14), ("silhouette", 12), ("human_energy", 10)],
        "Production Scope": [("practical", 14), ("contained", 12), ("real_world", 10)],
        "Closing Statement": [("impact", 16), ("resonance", 14), ("emotional_finality", 12)],
    }
    for term, pts in slide_weights.get(slide_name, []):
        bump(term, pts)

    cat_world_map = {
        "action_espionage": {
            "base": [("surveillance", 14), ("night_operation", 12), ("hidden_identity", 10)],
            "character": [("split_life", 14), ("covert_pressure", 12), ("domestic_cover", 10)],
            "theme": [("family_risk", 12), ("explosive_reveal", 10), ("high_stakes", 10)],
        },
        "contained_urban": {
            "base": [("streetlights", 16), ("car_interior", 14), ("night", 12)],
            "character": [("rearview", 14), ("windshield", 12), ("implied_presence", 10)],
            "theme": [("pressure", 10), ("isolation", 10), ("urban", 8)],
        },
        "legal_courtroom": {
            "base": [("courtroom_wide", 16), ("institutional_space", 14), ("military_formality", 10)],
            "character": [("witness_stand", 14), ("command_pressure", 12), ("interrogation_room", 10)],
            "theme": [("truth_under_oath", 12), ("moral_weight", 10), ("verdict_energy", 10)],
        },
        "fantasy_satire": {
            "base": [("castle_wide", 16), ("storybook_scale", 14), ("ceremonial_absurdity", 10)],
            "character": [("throne_room", 14), ("comic_intrigue", 12), ("royal_misrule", 10)],
            "theme": [("satirical_pageantry", 12), ("kingdom_chaos", 10), ("comic_resolution", 10)],
        },
        "romantic_comedy": {
            "base": [("romance_connection", 16), ("warm_interior", 14), ("social_setting", 10)],
            "character": [("intimate_moment", 14), ("social_pressure", 12), ("friendship_bond", 10)],
            "theme": [("love_realization", 12), ("emotional_honesty", 10), ("comic_warmth", 10)],
        },
        "nightlife_comedy": {
            "base": [("club_exterior", 14), ("velvet_rope", 12), ("city_lights", 10)],
            "character": [("awkward_party", 14), ("social_pressure", 12), ("dancefloor", 10)],
            "theme": [("afterparty_fallout", 12), ("neon_regret", 10), ("comic_release", 10)],
        },
        "sports_drama": {
            "base": [("arena", 14), ("empty_court", 12), ("night", 8)],
            "character": [("locker_room", 14), ("quiet_pressure", 12), ("hallway", 10)],
            "theme": [("scoreboard", 12), ("after_hours", 10), ("gym", 8)],
        },
        "crime_drama": {
            "base": [("street_night", 14), ("urban_grit", 12), ("danger_interior", 10)],
            "character": [("confrontation", 14), ("tension", 12), ("underworld", 10)],
            "theme": [("consequence", 12), ("moral_cost", 10), ("street_truth", 8)],
        },
    }

    category = "base"
    if slide_name in {"Protagonist", "Antagonist", "Supporting Characters", "Conflict Engine", "Stakes"}:
        category = "character"
    elif slide_name in {"Theme", "Tone", "Why This Film", "Closing Statement"}:
        category = "theme"

    for term, pts in cat_world_map.get(cat, {}).get(category, []):
        bump(term, pts)

    mode_weights = {
        "prestige_authority": [("premium", 12), ("authority", 10), ("disciplined", 8)],
        "tension_pressure": [("tension", 12), ("pressure", 10), ("isolation", 8)],
        "character_heart": [("emotion", 12), ("human_energy", 10), ("intimate", 8)],
        "spectacle_play": [("spectacle", 12), ("pageantry", 10), ("playful", 8)],
    }
    for term, pts in mode_weights.get(primary_mode, []):
        bump(term, pts)
    for term, pts in mode_weights.get(secondary_mode, []):
        bump(term, max(4, pts // 2))

    return weights


def infer_file_strategy(slide_name: str, story_map: dict) -> dict:
    composition = story_map.get("layout_strategy", {}).get("composition_bias", "balanced")
    if slide_name in {"Title", "World", "Visual Style", "Closing Statement"}:
        return {"subject_preference": "environment_first", "framing": "wide", "people_density": "low_to_medium", "swap_ready": True}
    if slide_name in {"Protagonist", "Antagonist", "Supporting Characters", "Conflict Engine", "Stakes"}:
        return {"subject_preference": "character_presence", "framing": "medium", "people_density": "medium", "swap_ready": True}
    if slide_name in {"Tone", "Theme", "Why This Film", "Audience", "Comparables"}:
        return {"subject_preference": "mood_symbolic", "framing": "flexible", "people_density": "low", "swap_ready": True}
    return {"subject_preference": composition, "framing": "flexible", "people_density": "medium", "swap_ready": True}


def build_image_plan(story_map: dict) -> list[dict]:
    slide_names = [
        "Title", "Logline", "Synopsis", "Protagonist", "Antagonist",
        "Supporting Characters", "Theme", "Tone", "World", "Conflict Engine",
        "Stakes", "Why This Film", "Audience", "Visual Style", "Comparables",
        "Market Position", "Director Vision", "Casting Ideas", "Production Scope",
        "Closing Statement",
    ]
    plan = []
    for idx, slide_name in enumerate(slide_names, start=1):
        terms = slide_visual_terms(slide_name, story_map)
        plan.append({
            "slide_number": idx,
            "slide_title": slide_name,
            "image_query": " ".join(terms[:4]),
            "image_tags": terms,
            "image_score": 1.0,
            "preferred_folders": [],
            "visual_family": None,
            "file_strategy": infer_file_strategy(slide_name, story_map),
            "image_options": [],
        })
    return plan


def main():
    if len(sys.argv) < 2:
        print("❌ No input provided")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if input_path.suffix.lower() == ".pdf":
        try:
            reader = PdfReader(input_path)
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
        except Exception:
            text = ""
    else:
        text = input_path.read_text(errors="ignore")
    story_map = build_story_map(text)

    print(f"🎬 Title: {story_map['title']}")
    print(f"🔥 Characters: {story_map['characters']}")
    print(f"🎯 Protagonist: {story_map['protagonist']}")
    print(f"🌍 World: {story_map['world']}")
    print(f"🎭 Tone: {story_map['tone']}")
    print(f"🪞 Theme: {story_map['theme']}")
    print(f"🧠 Story Engine: {story_map['story_engine']}")
    print(f"⚔️ Core Conflict: {story_map['core_conflict']}")
    print(f"🔄 Reversal: {story_map['reversal']}")
    print(f"🧾 Logline: {story_map['logline']}")
    print(f"📚 Synopsis: {story_map['synopsis']}")
    print(f"🎛️ Presentation Modes: {json.dumps(story_map['presentation_modes'], indent=2)}")
    print(f"🧱 Layout Strategy: {json.dumps(story_map['layout_strategy'], indent=2)}")

    _dai_work_dir = os.environ.get("DAI_WORK_DIR", "")
    out_path = Path(_dai_work_dir) / "approved_brain_output.json" if _dai_work_dir else OUT
    if _dai_work_dir:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(story_map, indent=2))


if __name__ == "__main__":
    main()
