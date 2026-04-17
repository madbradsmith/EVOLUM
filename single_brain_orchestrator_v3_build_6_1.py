# SINGLE BRAIN ORCHESTRATOR — COMBINED STORY MAP VERSION + IMAGE PLAN
# Full replacement for: /home/madbrad/app/single_brain_orchestrator_v3.py
# V3_BUILD_6_1 — layout intelligence layer

import sys
import json
import re
from pathlib import Path

APP_DIR = Path("/home/madbrad/app")
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
        clean = normalize(line).replace("\ufeff", "")
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


def detect_world(text: str) -> str:
    t = text.lower()

    genre_signals = {
        "feature / action espionage thriller": [
            "spy", "agent", "terrorist", "mission", "intel", "nuclear", "harrier",
            "explosion", "surveillance", "secret service", "undercover", "assassin",
            "bomb", "hostage", "chase", "gunfire", "helicopter", "covert", "operative"
        ],
        "feature / contained urban thriller": [
            "rideshare", "uber", "lyft", "fare", "pickup", "dropoff", "backseat", "driver"
        ],
        "feature / legal / courtroom drama": [
            "courtroom", "court", "trial", "judge", "jury", "verdict", "witness",
            "cross-examination", "navy", "marine", "uniform code", "hearing", "defense counsel"
        ],
        "feature / fantasy satire comedy": [
            "kingdom", "castle", "court jester", "jester", "king", "queen", "princess",
            "dragon", "wizard", "sword", "medieval", "throne", "quest"
        ],
        "feature / nightlife comedy": [
            "club", "nightclub", "dance floor", "vip", "party", "bar", "bouncer",
            "night out", "hookup", "promoter", "velvet rope"
        ],
        "feature / sports drama": [
            "basketball", "team", "coach", "court", "locker room", "season",
            "championship", "practice", "rebels", "hornets"
        ],
        "feature / crime drama": [
            "money", "crime", "drug", "smuggle", "cop", "police", "cartel",
            "robbery", "detective", "murder", "heist"
        ],
    }

    scores = {}
    for genre, signals in genre_signals.items():
        scores[genre] = sum(1 for signal in signals if signal in t)

    strongest_genre = max(scores, key=scores.get)
    strongest_score = scores[strongest_genre]

    if strongest_score >= 2:
        return strongest_genre
    if strongest_score == 1 and strongest_genre in {
        "feature / action espionage thriller",
        "feature / legal / courtroom drama",
        "feature / fantasy satire comedy",
        "feature / nightlife comedy",
    }:
        return strongest_genre

    return "feature / drama"


def infer_time_frame(text: str) -> str:
    world = detect_world(text)
    t = text.lower()

    if any(phrase in t for phrase in ["single night", "one night", "through the night", "overnight"]):
        return "single night"
    if any(phrase in t for phrase in ["single day", "one day", "same day"]):
        return "single day"
    if world == "feature / action espionage thriller":
        return "compressed high-stakes timeframe"
    if world == "feature / contained urban thriller":
        return "single night"
    if world == "feature / legal / courtroom drama":
        return "contained escalating legal battle"
    if world == "feature / fantasy satire comedy":
        return "contained escalating journey"
    if world == "feature / nightlife comedy":
        return "single night"
    if world == "feature / sports drama":
        return "contained competitive season"
    return "contained timeframe"


def infer_setting(text: str, world: str) -> str:
    if world == "feature / action espionage thriller":
        return "across domestic spaces, covert locations, and escalating action set pieces"
    if world == "feature / contained urban thriller":
        return "inside a rideshare car and across a city at night"
    if world == "feature / legal / courtroom drama":
        return "across courtrooms, military offices, holding rooms, and institutional pressure spaces"
    if world == "feature / fantasy satire comedy":
        return "across castles, ceremonial chambers, village spaces, and a heightened kingdom full of absurd rules"
    if world == "feature / nightlife comedy":
        return "across clubs, streets, parties, and chaotic social spaces over one long night"
    if world == "feature / sports drama":
        return "across locker rooms, courts, homes, and emotionally charged spaces around the game"
    if world == "feature / crime drama":
        return "across dangerous interiors, streets, and pressure-filled underworld spaces"
    return "a contained dramatic environment"


def infer_tone(text: str, world: str) -> str:
    if world == "feature / action espionage thriller":
        return "propulsive, high-stakes, witty, cinematic"
    if world == "feature / contained urban thriller":
        return "tense, paranoid, urban, nocturnal"
    if world == "feature / legal / courtroom drama":
        return "tense, procedural, sharp, morally charged"
    if world == "feature / fantasy satire comedy":
        return "playful, witty, satirical, adventurous"
    if world == "feature / nightlife comedy":
        return "chaotic, funny, awkward, energetic"
    if world == "feature / sports drama":
        return "grounded, competitive, emotional, aspirational"
    if world == "feature / crime drama":
        return "tense, grounded, dangerous, dramatic"
    return "grounded, dramatic, character-driven"


def infer_story_engine(text: str, protagonist: str) -> str:
    world = detect_world(text)
    p = protagonist.title()
    if world == "feature / action espionage thriller":
        return (
            f"{p} is forced to balance a hidden life of danger with the illusion of normalcy, "
            f"until escalating threats pull both worlds into collision."
        )
    if world == "feature / contained urban thriller":
        return (
            f"{p} misreads a tense night of pickups and escalating stops as criminal activity, "
            f"and his growing suspicion begins to shape the danger around him."
        )
    if world == "feature / legal / courtroom drama":
        return (
            f"{p} is pulled into a high-pressure military case where loyalty, institutional power, "
            f"and buried truth collide, forcing him to decide what kind of lawyer—and man—he really is."
        )
    if world == "feature / fantasy satire comedy":
        return (
            f"{p} stumbles into a role far bigger than expected, and each attempt to survive "
            f"the absurd rules of the kingdom only pulls the chaos closer."
        )
    if world == "feature / nightlife comedy":
        return (
            f"{p} tries to keep one wild night under control, but every bad decision "
            f"turns the evening into a bigger social disaster."
        )
    if world == "feature / sports drama":
        return (
            f"{p} is forced to carry ambition, pressure, and expectation at the same time, "
            f"with every arena of life pushing harder against who they are trying to become."
        )
    return (
        f"{p} is pulled into a tense situation and forced to interpret incomplete information under pressure."
    )


def infer_core_conflict(text: str, protagonist: str) -> str:
    world = detect_world(text)
    p = protagonist.title()
    if world == "feature / action espionage thriller":
        return (
            f"{p} must protect family, identity, and mission at once as secrets and escalating danger threaten to expose everything."
        )
    if world == "feature / contained urban thriller":
        return (
            f"{p}'s fear and suspicion distort how he reads his passengers, "
            f"pushing him toward choices that could escalate the night beyond control."
        )
    if world == "feature / legal / courtroom drama":
        return (
            f"{p} must cut through loyalty, fear, and institutional pressure to uncover the truth "
            f"before the system closes ranks and buries it for good."
        )
    if world == "feature / fantasy satire comedy":
        return (
            f"{p} must navigate ridiculous power structures, inflated egos, and escalating chaos "
            f"without losing the part of themselves that makes them dangerous."
        )
    if world == "feature / sports drama":
        return (
            f"{p} must navigate the collision between personal ambition, emotional pressure, "
            f"and the expectations surrounding performance."
        )
    return f"{p} must navigate mounting pressure without fully understanding the situation."


def infer_reversal(text: str) -> str:
    world = detect_world(text)
    if world == "feature / action espionage thriller":
        return "The hidden life meant to protect the protagonist's family becomes the very thing that puts them in danger."
    if world == "feature / contained urban thriller":
        return "The passengers are not what the protagonist believes they are."
    if world == "feature / legal / courtroom drama":
        return "The deeper truth is not just about the crime—it is about the system protecting itself."
    if world == "feature / sports drama":
        return "What first looks like a path to achievement reveals a deeper emotional cost."
    return "The truth behind the situation is different from what the protagonist first assumes."


def build_logline_from_story_map(story_map: dict) -> str:
    world = story_map["world"]
    protagonist = story_map["protagonist"].title()

    if world == "feature / action espionage thriller":
        return (
            f"When a covert operative's double life begins collapsing under escalating danger, "
            f"{protagonist} must protect family and mission before both are destroyed."
        )
    if world == "feature / contained urban thriller":
        return (
            "During a tense night of pickups and drop-offs, a rideshare driver becomes convinced "
            "his passengers are planning something criminal—but as the night unfolds, his growing "
            "suspicion may be the very thing putting everything at risk."
        )
    if world == "feature / legal / courtroom drama":
        return (
            f"When a military hazing case lands on his desk, {protagonist} must push past ego, "
            f"fear, and institutional pressure to uncover a truth powerful men will do anything to protect."
        )
    if world == "feature / fantasy satire comedy":
        return (
            f"When court chaos thrusts {protagonist} into the center of a kingdom on the verge of collapse, "
            f"wit may be the only weapon sharp enough to survive."
        )
    if world == "feature / nightlife comedy":
        return (
            f"What starts as a simple night out spirals into escalating social disaster as {protagonist} "
            f"tries to outrun one bad decision after another."
        )
    if world == "feature / sports drama":
        return (
            f"When pressure, legacy, and competition collide, {protagonist} must fight to hold together identity, "
            f"ambition, and responsibility before everything slips out of reach."
        )

    return (
        f"When {protagonist} is pulled into a tense situation he does not fully understand, "
        f"he must navigate mounting pressure before everything collapses."
    )


def build_synopsis_from_story_map(story_map: dict) -> str:
    world = story_map["world"]
    protagonist = story_map["protagonist"].title()
    chars = [c.title() for c in story_map["characters"][1:4]]
    support_text = f" Along the way, {', '.join(chars)} complicate and deepen the stakes." if chars else ""

    if world == "feature / action espionage thriller":
        return (
            f"{protagonist} has spent years balancing danger, secrecy, and domestic routine without allowing those worlds to collide. "
            f"What begins as controlled compartmentalization gives way to escalating threats, hidden agendas, and dangerous revelations "
            f"that begin pulling every part of life into crisis.{support_text}\n\n"
            f"As pressure mounts, the cost of secrecy becomes personal. Every mission, lie, and split-second choice sharpens the danger, "
            f"forcing {protagonist} toward a defining confrontation where family, identity, and survival are all on the line."
        )

    if world == "feature / contained urban thriller":
        return (
            "Over the course of a single night, a rideshare driver picks up a series of passengers whose behavior "
            "begins to raise suspicion. As each stop adds new tension and unanswered questions, he becomes increasingly "
            "convinced that he is caught in something criminal. His fear begins to shape how he interprets every glance, "
            "every conversation, and every decision he makes behind the wheel. With the pressure mounting and nowhere to "
            "escape, his growing paranoia pushes him toward choices that could escalate the situation beyond control. But "
            "as the night unfolds, the truth behind his passengers may be far different than what he believes—forcing him "
            "to confront the consequences of acting on assumptions in a situation he never fully understood."
        )

    if world == "feature / legal / courtroom drama":
        return (
            f"{protagonist} is an ambitious Navy lawyer more comfortable coasting on charm than carrying the full weight of responsibility. "
            f"When a hazing death at Guantanamo Bay lands in his lap, what first appears to be a straightforward plea deal begins opening into "
            f"something far more dangerous. As the case deepens, institutional pressure, buried loyalties, and military hierarchy begin closing in.{support_text}\n\n"
            f"Forced to confront both the system around him and the parts of himself he has long avoided, {protagonist} must decide whether to "
            f"protect his career or risk everything to expose the truth. What begins as defense becomes a defining test of courage, integrity, and identity."
        )

    if world == "feature / fantasy satire comedy":
        return (
            f"{protagonist} is pulled into a kingdom where image matters more than wisdom and survival depends on reading absurd power dynamics correctly. "
            f"What first feels playful and ridiculous begins revealing deeper agendas, fragile egos, and a system far shakier than it looks.{support_text}\n\n"
            f"As the chaos escalates, wit becomes both shield and weapon. {protagonist} must learn how to survive the spectacle without being swallowed by it."
        )

    if world == "feature / nightlife comedy":
        return (
            f"{protagonist} moves through one long night chasing validation, excitement, and some version of control that never quite arrives. "
            f"What starts as a simple social outing spirals into escalating embarrassment, misfires, and comic self-destruction.{support_text}\n\n"
            f"Each attempt to recover only creates new complications, forcing {protagonist} to confront the difference between what they want and what they actually need."
        )

    if world == "feature / sports drama":
        support_text = ""
        if chars:
            support_text = f" Along the way, {', '.join(chars)} help shape the pressure closing in around them."
        return (
            f"{protagonist} sits at the center of a rising storm where family pressure, personal legacy, and high-stakes "
            f"competition begin colliding at the worst possible time. What starts as a familiar pursuit of success quickly "
            f"tightens into something more demanding, forcing them to navigate shifting expectations, emotional weight, "
            f"and the realities of performance under pressure.{support_text}\n\n"
            f"As the stakes escalate, the pressure becomes deeply personal. Every decision carries consequence, and the cost "
            f"of failure sharpens into something unavoidable. {protagonist} is driven toward a defining moment that reveals "
            f"who they are when expectation, identity, and ambition all demand an answer."
        )

    return (
        f"As pressure mounts around {protagonist}, incomplete information and rising tension force increasingly risky choices. "
        f"What first appears to be one kind of threat gradually reveals itself to be something more complicated, pushing the "
        f"story toward a reversal that challenges the protagonist's assumptions."
    )


def infer_layout_strategy(story_map: dict) -> dict:
    world = story_map["world"]
    tone = story_map["tone"].lower()
    synopsis = story_map.get("synopsis", "").lower()

    layout_style = "cinematic_grounded"
    text_density = "medium"
    image_priority = "high"
    pacing = "measured"
    visual_energy = "controlled"
    slide_rhythm = "balanced"
    headline_style = "statement"
    composition_bias = "image_forward"

    if world == "feature / action espionage thriller":
        layout_style = "cinematic_high_tension"
        text_density = "low"
        image_priority = "very_high"
        pacing = "fast"
        visual_energy = "volatile"
        slide_rhythm = "punchy"
        headline_style = "hook"
        composition_bias = "full_bleed"
    elif world == "feature / contained urban thriller":
        layout_style = "contained_nocturnal"
        text_density = "low"
        image_priority = "very_high"
        pacing = "tight"
        visual_energy = "claustrophobic"
        slide_rhythm = "minimal"
        headline_style = "hook"
        composition_bias = "full_bleed"
    elif world == "feature / legal / courtroom drama":
        layout_style = "institutional_cinematic"
        text_density = "medium"
        image_priority = "high"
        pacing = "measured"
        visual_energy = "restrained_intense"
        slide_rhythm = "balanced"
        headline_style = "argument"
        composition_bias = "split_text_image"
    elif world == "feature / fantasy satire comedy":
        layout_style = "storybook_satirical"
        text_density = "medium"
        image_priority = "high"
        pacing = "playful"
        visual_energy = "heightened"
        slide_rhythm = "varied"
        headline_style = "characterful"
        composition_bias = "illustrative"
    elif world == "feature / nightlife comedy":
        layout_style = "neon_social_chaos"
        text_density = "low"
        image_priority = "very_high"
        pacing = "fast"
        visual_energy = "chaotic"
        slide_rhythm = "punchy"
        headline_style = "hook"
        composition_bias = "full_bleed"
    elif world == "feature / sports drama":
        layout_style = "athletic_prestige"
        text_density = "medium"
        image_priority = "high"
        pacing = "driving"
        visual_energy = "focused"
        slide_rhythm = "balanced"
        headline_style = "statement"
        composition_bias = "hero_image"

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
    world = story_map["world"]
    strategy = story_map["layout_strategy"]

    slide_count = 12
    if strategy["image_priority"] == "very_high":
        slide_count = 14
    if world == "feature / legal / courtroom drama":
        slide_count = 13
    if world == "feature / fantasy satire comedy":
        slide_count = 14

    opening_style = "title_then_hook"
    if strategy["headline_style"] == "argument":
        opening_style = "title_then_premise"
    if strategy["headline_style"] == "characterful":
        opening_style = "title_then_world"

    return {
        "recommended_slide_count": slide_count,
        "opening_style": opening_style,
        "mid_deck_focus": strategy["composition_bias"],
        "closing_style": "statement" if world != "feature / nightlife comedy" else "punchline_with_heart",
    }


def build_story_map(text: str) -> dict:
    title = extract_title(text)
    dialogue_counts, dialogue_first, dialogue_support = analyze_dialogue_characters(text)
    action_counts, action_first = extract_action_names(text)
    characters, character_stats = merge_character_signals(
        dialogue_counts, dialogue_first, dialogue_support, action_counts, action_first
    )

    protagonist = pick_protagonist(characters, character_stats)
    world = detect_world(text)
    time_frame = infer_time_frame(text)
    setting = infer_setting(text, world)
    tone = infer_tone(text, world)
    story_engine = infer_story_engine(text, protagonist)
    core_conflict = infer_core_conflict(text, protagonist)
    reversal = infer_reversal(text)

    story_map = {
        "title": title,
        "characters": characters[:5],
        "character_stats": character_stats,
        "protagonist": protagonist,
        "world": world,
        "time_frame": time_frame,
        "setting": setting,
        "tone": tone,
        "story_engine": story_engine,
        "core_conflict": core_conflict,
        "reversal": reversal,
    }

    story_map["logline"] = build_logline_from_story_map(story_map)
    story_map["synopsis"] = build_synopsis_from_story_map(story_map)
    story_map["layout_strategy"] = infer_layout_strategy(story_map)
    story_map["slide_blueprint"] = infer_slide_blueprint(story_map)
    story_map["image_plan"] = build_image_plan(story_map)
    return story_map


def pick_protagonist(chars, stats) -> str:
    if not chars:
        return "Protagonist"

    ranked = []
    for name in chars:
        s = stats.get(name, {})
        d = s.get("dialogue_count", 0)
        a = s.get("action_count", 0)
        first = s.get("first_seen", 99999)

        score = 0
        score += a * 5
        score += d * 2

        if first < 50:
            score += 5
        elif first < 120:
            score += 2

        if a >= 3:
            score += 4

        ranked.append((name, score, first))

    ranked.sort(key=lambda x: (-x[1], x[2], x[0]))
    return ranked[0][0]


def base_image_terms(story_map: dict) -> list[str]:
    world = story_map["world"]
    terms = []

    if world == "feature / action espionage thriller":
        terms.extend(["covert", "surveillance", "domestic_tension", "high_stakes", "cinematic"])
    elif world == "feature / contained urban thriller":
        terms.extend(["urban", "night", "car", "tension", "isolation"])
    elif world == "feature / legal / courtroom drama":
        terms.extend(["courtroom", "institution", "military", "authority", "moral_pressure"])
    elif world == "feature / fantasy satire comedy":
        terms.extend(["kingdom", "pageantry", "satire", "fantasy", "court_chaos"])
    elif world == "feature / nightlife comedy":
        terms.extend(["nightlife", "social_chaos", "party", "awkwardness", "city_night"])
    elif world == "feature / sports drama":
        terms.extend(["sports", "court", "locker_room", "pressure", "competition"])
    elif world == "feature / crime drama":
        terms.extend(["urban", "danger", "night", "street", "pressure"])
    else:
        terms.extend(["grounded", "dramatic", "environment"])

    return terms


def slide_visual_terms(slide_name: str, story_map: dict) -> list[str]:
    world = story_map["world"]
    protagonist = slugify(story_map["protagonist"])
    tone_terms = [slugify(t) for t in story_map["tone"].split(",") if t.strip()]
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

    terms = []
    terms.extend(base_terms)
    terms.extend(tone_terms[:3])
    terms.extend(mapping.get(slide_name, ["cinematic", "environment"]))

    if world == "feature / action espionage thriller":
        if slide_name in {"Title", "Logline", "World"}:
            terms.extend(["surveillance", "night_operation", "hidden_identity"])
        elif slide_name in {"Protagonist", "Conflict Engine", "Stakes"}:
            terms.extend(["split_life", "domestic_cover", "covert_pressure"])
        elif slide_name in {"Theme", "Closing Statement"}:
            terms.extend(["explosive_reveal", "family_risk", "high_stakes"])
    elif world == "feature / contained urban thriller":
        if slide_name in {"Title", "Logline", "World"}:
            terms.extend(["streetlights", "car_interior", "night"])
        elif slide_name in {"Protagonist", "Conflict Engine", "Stakes"}:
            terms.extend(["windshield", "rearview", "implied_presence"])
    elif world == "feature / legal / courtroom drama":
        if slide_name in {"Title", "Logline", "World"}:
            terms.extend(["courtroom_wide", "military_formality", "institutional_space"])
        elif slide_name in {"Protagonist", "Conflict Engine", "Stakes"}:
            terms.extend(["witness_stand", "interrogation_room", "command_pressure"])
        elif slide_name in {"Theme", "Closing Statement"}:
            terms.extend(["truth_under_oath", "moral_weight", "verdict_energy"])
    elif world == "feature / fantasy satire comedy":
        if slide_name in {"Title", "Logline", "World"}:
            terms.extend(["castle_wide", "ceremonial_absurdity", "storybook_scale"])
        elif slide_name in {"Protagonist", "Conflict Engine", "Stakes"}:
            terms.extend(["throne_room", "comic_intrigue", "royal_misrule"])
        elif slide_name in {"Theme", "Closing Statement"}:
            terms.extend(["satirical_pageantry", "kingdom_chaos", "comic_resolution"])
    elif world == "feature / nightlife comedy":
        if slide_name in {"Title", "Logline", "World"}:
            terms.extend(["club_exterior", "velvet_rope", "city_lights"])
        elif slide_name in {"Protagonist", "Conflict Engine", "Stakes"}:
            terms.extend(["dancefloor", "awkward_party", "social_pressure"])
        elif slide_name in {"Theme", "Closing Statement"}:
            terms.extend(["afterparty_fallout", "neon_regret", "comic_release"])
    elif world == "feature / sports drama":
        if slide_name in {"Title", "Logline", "World"}:
            terms.extend(["empty_court", "arena", "night"])
        elif slide_name in {"Protagonist", "Stakes", "Conflict Engine"}:
            terms.extend(["locker_room", "hallway", "quiet_pressure"])
        elif slide_name in {"Theme", "Closing Statement"}:
            terms.extend(["scoreboard", "gym", "after_hours"])

    seen = set()
    ordered = []
    for t in terms:
        if not t:
            continue
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered


def build_image_plan(story_map: dict) -> list[dict]:
    slide_names = [
        "Title",
        "Logline",
        "Synopsis",
        "Protagonist",
        "Antagonist",
        "Supporting Characters",
        "Theme",
        "Tone",
        "World",
        "Conflict Engine",
        "Stakes",
        "Why This Film",
        "Audience",
        "Visual Style",
        "Comparables",
        "Market Position",
        "Director Vision",
        "Casting Ideas",
        "Production Scope",
        "Closing Statement",
    ]

    plan = []
    for idx, slide_name in enumerate(slide_names, start=1):
        terms = slide_visual_terms(slide_name, story_map)
        plan.append({
            "slide_number": idx,
            "slide_title": slide_name,
            "image_query": " ".join(terms),
            "image_tags": terms,
        })
    return plan


def main():
    if len(sys.argv) < 2:
        print("❌ No input provided")
        sys.exit(1)

    text = Path(sys.argv[1]).read_text(errors="ignore")
    story_map = build_story_map(text)

    print(f"🔥 TOP CHARACTER CANDIDATES: {story_map['characters']}")
    print(f"🧩 CHARACTER STATS: {json.dumps({k: story_map['character_stats'][k] for k in story_map['characters']}, indent=2)}")
    print(f"🎬 Title: {story_map['title']}")
    print(f"🔥 Characters: {story_map['characters']}")
    print(f"🎯 Protagonist: {story_map['protagonist']}")
    print(f"🌍 World: {story_map['world']}")
    print(f"🎭 Tone: {story_map['tone']}")
    print(f"🧠 Story Engine: {story_map['story_engine']}")
    print(f"⚔️ Core Conflict: {story_map['core_conflict']}")
    print(f"🔄 Reversal: {story_map['reversal']}")
    print(f"🧾 Logline: {story_map['logline']}")
    print(f"📚 Synopsis: {story_map['synopsis']}")
    print(f"🧱 Layout Strategy: {json.dumps(story_map['layout_strategy'], indent=2)}")
    print(f"🗂️ Slide Blueprint: {json.dumps(story_map['slide_blueprint'], indent=2)}")
    print(f"🖼️ IMAGE PLAN SAMPLE: {json.dumps(story_map['image_plan'][:3], indent=2)}")

    OUT.write_text(json.dumps(story_map, indent=2))


if __name__ == "__main__":
    main()
