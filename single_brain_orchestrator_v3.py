# SINGLE BRAIN ORCHESTRATOR — COMBINED STORY MAP VERSION + IMAGE PLAN
# Full replacement for: /home/madbrad/app/single_brain_orchestrator_v3.py
# V6_PROMETHEUS — image options + folder aware routing

import sys
import json
import os
import re
from pathlib import Path

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






def infer_protagonist_summary(story_map: dict) -> str:
    protagonist = (story_map.get("protagonist") or "Protagonist").title()
    world = story_map.get("world", "")
    tone = story_map.get("tone", "")

    if world == "feature / action espionage thriller":
        return f"{protagonist} is a capable operative forced to balance covert pressure, personal risk, and escalating danger without losing control."
    if world == "feature / contained urban thriller":
        return f"{protagonist} is a pressure-cooked lead whose fear and exhaustion distort the night, pushing ordinary decisions toward dangerous consequences."
    if world == "feature / legal / courtroom drama":
        return f"{protagonist} is a sharp but pressured legal lead forced to confront institutional power, buried truth, and the cost of standing their ground."
    if world == "feature / fantasy satire comedy":
        return f"{protagonist} is a clever outsider navigating absurd power structures with wit, survival instinct, and growing political awareness."
    if world == "feature / nightlife comedy":
        return f"{protagonist} is a socially volatile lead chasing validation through one chaotic night that keeps exposing their blind spots."
    if world == "feature / sports drama":
        return f"{protagonist} is a driven competitor carrying personal and external pressure into a defining test of identity, discipline, and resolve."
    return f"{protagonist} is the central engine of the story, carrying the emotional pressure, conflict, and forward momentum of the project."


def infer_theme(story_map: dict) -> str:
    world = story_map.get("world", "")
    conflict = (story_map.get("core_conflict") or "").lower()
    reversal = (story_map.get("reversal") or "").lower()

    if world == "feature / action espionage thriller":
        return "Secrecy, loyalty, and identity collide as private cost catches up with professional control."
    if world == "feature / contained urban thriller":
        return "Fear, pressure, and assumption distort perception, turning survival into a test of judgment and trust."
    if world == "feature / legal / courtroom drama":
        return "Truth versus institutional protection, and the personal cost of choosing integrity under pressure."
    if world == "feature / fantasy satire comedy":
        return "Image, power, and absurdity reveal how fragile authority becomes when spectacle replaces wisdom."
    if world == "feature / nightlife comedy":
        return "Validation, embarrassment, and self-delusion collide as one bad night exposes what the protagonist refuses to face."
    if world == "feature / sports drama":
        return "Identity, expectation, and discipline collide as performance pressure forces emotional truth into the open."

    if "identity" in conflict or "identity" in reversal:
        return "Identity is tested under pressure as the protagonist is forced to confront the gap between appearance and truth."
    if "truth" in conflict or "truth" in reversal:
        return "Truth grows more costly the longer pressure rewards denial, silence, or self-protection."
    return "Pressure reveals character, and the story tests what remains when certainty gives way to consequence."


def infer_document_layouts(story_map: dict) -> dict:
    world = story_map.get("world", "")
    primary_mode = ((story_map.get("presentation_modes") or {}).get("primary_mode") or "character_heart")
    strategy = story_map.get("layout_strategy") or {}

    analysis_style = "clean_cinematic_report"
    actor_style = "character_workbook_dark"
    audition_style = "fast_turnaround_brief"
    booked_style = "deep_role_dossier"
    chart_style = "gold_on_dark"

    if world == "feature / legal / courtroom drama" or primary_mode == "prestige_authority":
        analysis_style = "prestige_report"
        actor_style = "institutional_character_brief"
        audition_style = "measured_authority_sides"
        booked_style = "prestige_role_bible"
        chart_style = "formal_gold_grid"
    elif world == "feature / contained urban thriller" or primary_mode == "tension_pressure":
        analysis_style = "thriller_intelligence_report"
        actor_style = "pressure_character_brief"
        audition_style = "urgent_sides_brief"
        booked_style = "contained_thriller_role_map"
        chart_style = "signal_on_dark"
    elif world == "feature / fantasy satire comedy" or primary_mode == "spectacle_play":
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

    # World-specific weighting
    if "legal / courtroom drama" in world:
        scores["prestige_authority"] += 30
        scores["tension_pressure"] += 10
    elif "action espionage thriller" in world:
        scores["tension_pressure"] += 28
        scores["spectacle_play"] += 8
    elif "contained urban thriller" in world:
        scores["tension_pressure"] += 28
        scores["character_heart"] += 6
    elif "fantasy satire comedy" in world:
        scores["spectacle_play"] += 30
        scores["character_heart"] += 8
    elif "nightlife comedy" in world:
        scores["spectacle_play"] += 24
        scores["character_heart"] += 8
    elif "sports drama" in world:
        scores["character_heart"] += 18
        scores["prestige_authority"] += 6
        scores["tension_pressure"] += 8

    # Tone-specific weighting
    if any(t in tone for t in ["playful", "witty", "satirical", "heightened", "chaotic"]):
        scores["spectacle_play"] += 16
    if any(t in tone for t in ["tense", "sharp", "paranoid", "volatile", "claustrophobic"]):
        scores["tension_pressure"] += 16
    if any(t in tone for t in ["morally charged", "procedural", "restrained", "focused"]):
        scores["prestige_authority"] += 14
    if any(t in tone for t in ["emotional", "warm", "human", "grounded"]):
        scores["character_heart"] += 14

    # Balance and clamp
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    primary_mode = ordered[0][0]
    secondary_mode = ordered[1][0]

    if primary_mode == secondary_mode:
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
        controls.update({
            "layout_energy": "measured",
            "discipline_level": "high",
            "image_dominance": "medium",
            "rhythm_bias": "disciplined",
        })
    elif primary == "tension_pressure":
        controls.update({
            "layout_energy": "high",
            "discipline_level": "medium_high",
            "image_dominance": "high",
            "rhythm_bias": "tight",
        })
    elif primary == "character_heart":
        controls.update({
            "layout_energy": "medium",
            "discipline_level": "medium",
            "image_dominance": "medium",
            "rhythm_bias": "intimate",
        })
    elif primary == "spectacle_play":
        controls.update({
            "layout_energy": "high",
            "discipline_level": "medium_low",
            "image_dominance": "high",
            "rhythm_bias": "elastic",
        })

    # Secondary mode refinement
    if secondary == "character_heart" and controls["discipline_level"] in {"medium_high", "high"}:
        controls["discipline_level"] = "medium"
    if secondary == "prestige_authority" and primary == "spectacle_play":
        controls["discipline_level"] = "medium"
    if secondary == "spectacle_play" and primary == "tension_pressure":
        controls["layout_energy"] = "high"

    return controls

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




def infer_commercial_positioning(story_map: dict) -> str:
    world = story_map.get("world", "")
    primary_mode = ((story_map.get("presentation_modes") or {}).get("primary_mode") or "")
    if world == "feature / contained urban thriller":
        return "Contained commercial thriller with strong low-to-mid budget pitch value and trailer-ready tension."
    if world == "feature / fantasy satire comedy":
        return "Broad-appeal fantasy satire with strong family/comedy packaging potential and visual franchise upside."
    if world == "feature / legal / courtroom drama":
        return "Prestige-leaning legal drama with serious performance, awards, and streamer positioning potential."
    if world == "feature / nightlife comedy":
        return "Commercial nightlife comedy built for fast pacing, ensemble energy, and social-chaos marketability."
    if world == "feature / sports drama":
        return "Emotionally accessible sports drama with inspirational crossover and talent-driven packaging appeal."
    if primary_mode == "tension_pressure":
        return "Commercial tension-driven project with contained scale and strong word-of-mouth premise value."
    if primary_mode == "prestige_authority":
        return "Prestige-forward dramatic package with strong performer appeal and premium streamer potential."
    if primary_mode == "spectacle_play":
        return "Visual, accessible concept with strong packaging upside for broad audiences."
    return "Commercially viable story package with clear pitch angles across concept, character, and tone."


def infer_audience_profile(story_map: dict) -> list[str]:
    world = story_map.get("world", "")
    tone = story_map.get("tone", "")
    profiles = []
    if "thriller" in world:
        profiles += ["Thriller audiences", "Urban suspense viewers", "Contained-premise fans"]
    if "fantasy" in world or "adventure" in tone:
        profiles += ["Fantasy audiences", "Family-friendly comedy viewers", "Adventure-forward viewers"]
    if "courtroom" in world or "legal" in world:
        profiles += ["Prestige drama audiences", "Legal/procedural viewers", "Performance-driven film fans"]
    if "comedy" in world:
        profiles += ["Comedy audiences", "Streaming-first viewers"]
    if "sports" in world:
        profiles += ["Sports drama audiences", "Inspirational drama viewers"]
    if not profiles:
        profiles = ["General film audiences", "Character-driven story viewers", "Streaming platform audiences"]
    seen = []
    for p in profiles:
        if p not in seen:
            seen.append(p)
    return seen[:5]


def infer_strength_index(story_map: dict) -> dict:
    world = story_map.get("world", "")
    characters = story_map.get("characters", [])
    tone = story_map.get("tone", "")
    concept = 7
    character = 7
    marketability = 7
    originality = 7
    if "thriller" in world:
        concept += 2
        marketability += 2
    if "fantasy" in world or "satire" in world:
        originality += 2
        concept += 1
    if "courtroom" in world or "legal" in world:
        character += 1
        marketability += 1
    if len(characters) >= 4:
        character += 1
    if "playful" in tone or "witty" in tone:
        originality += 1
    if "contained" in world:
        marketability += 1
    return {
        "concept": max(1, min(10, concept)),
        "character": max(1, min(10, character)),
        "marketability": max(1, min(10, marketability)),
        "originality": max(1, min(10, originality)),
    }


def infer_packaging_potential(story_map: dict) -> str:
    world = story_map.get("world", "")
    protagonist = story_map.get("protagonist", "Lead")
    if "fantasy" in world:
        return f"Strong packaging upside through distinctive world, comedic ensemble, and a breakout lead role for {protagonist}."
    if "thriller" in world:
        return f"Packaging works best around a strong lead performance, contained tension, and a marketable trailer hook anchored by {protagonist}."
    if "courtroom" in world or "legal" in world:
        return f"Packaging works through prestige casting, performance credibility, and premium streamer positioning around {protagonist}."
    return f"Packaging potential is strongest when the project is sold through lead identity, tone clarity, and a concise market hook built around {protagonist}."


def infer_character_leverage(story_map: dict) -> str:
    protagonist = story_map.get("protagonist", "Lead")
    characters = [c for c in story_map.get("characters", []) if c != protagonist]
    if characters:
        return f"{protagonist} is the primary leverage point, with support strength coming from {', '.join(characters[:3])} as contrast, pressure, or energy multipliers."
    return f"{protagonist} is the clear leverage point and should carry the package, marketing, and audience entry path."


def infer_tone_comparables(story_map: dict) -> list[str]:
    world = story_map.get("world", "")
    tone = story_map.get("tone", "")
    if "fantasy satire comedy" in world:
        return ["The Princess Bride", "Shrek", "Galavant"]
    if "contained urban thriller" in world:
        return ["Collateral", "Nightcrawler", "Phone Booth"]
    if "legal / courtroom drama" in world:
        return ["A Few Good Men", "Michael Clayton", "The Firm"]
    if "nightlife comedy" in world:
        return ["After Hours", "Superbad", "Booksmart"]
    if "sports drama" in world:
        return ["Creed", "Remember the Titans", "Friday Night Lights"]
    if "playful" in tone:
        return ["Knives Out", "Jojo Rabbit", "The Grand Budapest Hotel"]
    return ["Prisoners", "Little Miss Sunshine", "Argo"]


def infer_executive_summary(story_map: dict) -> str:
    title = story_map.get("title", "This project")
    protagonist = story_map.get("protagonist", "the lead")
    world = story_map.get("world", "feature drama")
    tone = story_map.get("tone", "")
    conflict = story_map.get("core_conflict", "")
    return f"{title} is a {world} built around {protagonist}, with a tone that plays {tone}. The commercial hook comes from a clear central engine: {conflict}"


def infer_actor_objective(story_map: dict) -> str:
    protagonist = story_map.get("protagonist", "the character")
    world = story_map.get("world", "")
    if "thriller" in world:
        return "Stay in control long enough to survive the pressure without revealing fear too early."
    if "fantasy" in world:
        return "Hold ground inside absurd power dynamics while using wit and instinct to stay one step ahead."
    if "legal" in world or "courtroom" in world:
        return "Press for truth and leverage without losing authority, credibility, or emotional precision."
    return f"Move the scene forward with clear intention while protecting what {protagonist} most wants from exposure or collapse."


def infer_playable_tactics(story_map: dict) -> list[str]:
    world = story_map.get("world", "")
    tactics = ["Deflect", "Pressure", "Reframe", "Hold control"]
    if "fantasy" in world or "comedy" in world:
        tactics = ["Charm", "Deflect", "Pressure", "Observe", "Pivot"]
    if "thriller" in world:
        tactics = ["Probe", "Control", "Withhold", "Redirect", "Corner"]
    if "legal" in world:
        tactics = ["Corner", "Press", "Frame", "Challenge", "Hold authority"]
    return tactics[:5]


def infer_emotional_triggers(story_map: dict) -> list[str]:
    world = story_map.get("world", "")
    if "fantasy" in world:
        return ["Humiliation", "Status shifts", "Public spectacle", "Unexpected danger"]
    if "thriller" in world:
        return ["Suspicion", "Loss of control", "Time pressure", "Misread intentions"]
    if "legal" in world:
        return ["Institutional pressure", "Exposure of truth", "Loss of credibility", "Moral confrontation"]
    return ["Rejection", "Pressure", "Exposure", "Uncertainty"]


def infer_audition_danger_zones(story_map: dict) -> list[str]:
    world = story_map.get("world", "")
    zones = ["Overplaying intention", "Pushing emotion too early", "Ignoring listening beats"]
    if "comedy" in world or "fantasy" in world:
        zones.append("Playing the joke instead of the objective")
    if "thriller" in world:
        zones.append("Telegraphing fear instead of letting pressure build")
    if "legal" in world:
        zones.append("Mistaking authority for volume")
    return zones[:5]


def infer_reader_chemistry_tips(story_map: dict) -> list[str]:
    return [
        "Pick fixed eyelines for each off-camera character.",
        "Let interruptions feel live rather than pre-timed.",
        "Use the reader to sharpen pressure changes, not flatten them.",
        "Stay responsive to pace shifts instead of locking one rhythm."
    ]


def infer_memorization_beats(story_map: dict) -> list[str]:
    return [
        "Opening power move",
        "First pressure turn",
        "Status shift or reveal",
        "Control reset",
        "Exit beat / last impression"
    ]


def infer_role_arc_map(story_map: dict) -> list[str]:
    world = story_map.get("world", "")
    if "fantasy" in world:
        return ["outsider observation", "strategic adaptation", "increased political awareness", "active role in chaos", "earned authority"]
    if "thriller" in world:
        return ["uncertainty", "pressure escalation", "misread danger", "forced decision", "clarity through consequence"]
    if "legal" in world:
        return ["controlled distance", "institutional pressure", "moral confrontation", "truth pursuit", "earned conviction"]
    return ["setup", "pressure", "adaptation", "reversal", "resolution"]


def infer_pressure_ladder(story_map: dict) -> list[str]:
    world = story_map.get("world", "")
    if "thriller" in world:
        return ["unease", "suspicion", "containment pressure", "escalation", "breaking point"]
    if "fantasy" in world:
        return ["social absurdity", "status pressure", "court risk", "public chaos", "high-stakes confrontation"]
    if "legal" in world:
        return ["professional tension", "institutional resistance", "truth pressure", "public exposure", "high-cost choice"]
    return ["low pressure", "rising tension", "complication", "peak pressure", "release"]


def infer_emotional_continuity(story_map: dict) -> list[str]:
    return [
        "Track where confidence cracks, even if behavior stays controlled.",
        "Let pressure affect pace before it affects volume.",
        "Carry unresolved tension into the next scene rather than resetting to neutral.",
        "Protect consistency of listening behavior across takes and scenes."
    ]


def infer_costume_behavior_clues(story_map: dict) -> list[str]:
    world = story_map.get("world", "")
    if "fantasy" in world:
        return ["Carry status in posture before dialogue.", "Let movement reflect court awareness and survival instinct."]
    if "thriller" in world:
        return ["Wardrobe should support fatigue, caution, or pressure.", "Behavior should stay alert even in stillness."]
    if "legal" in world:
        return ["Clothing and posture should signal discipline.", "Small behavioral control beats matter more than broad gestures."]
    return ["Costume should support role clarity.", "Behavior should align with status, confidence, and pressure level."]


def infer_relationship_leverage_map(story_map: dict) -> list[dict]:
    protagonist = story_map.get("protagonist", "")
    chars = [c for c in story_map.get("characters", []) if c != protagonist][:4]
    maps = []
    for c in chars:
        maps.append({
            "character": c,
            "dynamic": "pressure / contrast / leverage",
            "function": "tests the protagonist through information, status, or escalation"
        })
    return maps


def infer_set_ready_checklist(story_map: dict) -> list[str]:
    return [
        "Know the scene's pressure level before you play it.",
        "Track what your character wants from each interaction.",
        "Mark where status rises, slips, or resets.",
        "Keep body language and listening behavior consistent across takes.",
        "Protect continuity more than novelty."
    ]

def enhance_with_api(story_map: dict, script_text: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {}
    try:
        import anthropic
    except ImportError:
        return {}

    protagonist = story_map.get("protagonist", "Protagonist").title()
    world = story_map.get("world", "")
    tone = story_map.get("tone", "")
    characters = [c.title() for c in story_map.get("characters", [])[:5]]
    core_conflict = story_map.get("core_conflict", "")
    reversal = story_map.get("reversal", "")
    script_excerpt = script_text

    system = (
        "You are a professional Hollywood screenplay analyst and pitch writer. "
        "Given a screenplay excerpt and story data, write five things for a pitch package:\n"
        "1. logline — one sentence under 50 words: protagonist + pressure + stakes\n"
        "2. tagline — punchy marketing one-liner under 12 words: the core tension or promise, title-card style\n"
        "3. synopsis — two paragraphs, 150-200 words total: what happens, what is at stake\n"
        "4. theme — one sentence under 20 words: what the story is really about\n"
        "5. protagonist_summary — one sentence under 25 words: who they are and what they carry\n\n"
        "Return ONLY a raw JSON object with keys: logline, tagline, synopsis, theme, protagonist_summary. "
        "No markdown. No explanation. No code fences."
    )

    user_prompt = (
        f"Title: {story_map.get('title', 'Untitled')}\n"
        f"Genre/World: {world}\n"
        f"Tone: {tone}\n"
        f"Protagonist: {protagonist}\n"
        f"Key Characters: {', '.join(characters)}\n"
        f"Core Conflict: {core_conflict}\n"
        f"Reversal: {reversal}\n\n"
        f"FULL SCRIPT:\n{script_excerpt}"
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=700,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = next((b.text for b in message.content if hasattr(b, "text")), "")
        if not raw:
            return {}
        result = json.loads(raw.strip())
        return {k: v for k, v in result.items() if k in ("logline", "tagline", "synopsis", "theme", "protagonist_summary")}
    except Exception:
        return {}


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

    story_map["protagonist_summary"] = infer_protagonist_summary(story_map)
    story_map["theme"] = infer_theme(story_map)
    story_map["protagonist_profile"] = {
        "name": protagonist,
        "summary": story_map["protagonist_summary"],
    }
    story_map["logline"] = build_logline_from_story_map(story_map)
    story_map["synopsis"] = build_synopsis_from_story_map(story_map)

    # Engine-only tagline fallback — first clause of logline (up to comma/dash/semicolon)
    raw_logline = story_map.get("logline", "")
    import re as _re
    _first_clause = _re.split(r"[,;—–]", raw_logline)[0].strip() if raw_logline else ""
    story_map["tagline"] = _first_clause[:80] if _first_clause else story_map.get("story_engine", "")[:80]

    api_enhancements = enhance_with_api(story_map, text)
    if api_enhancements:
        story_map.update(api_enhancements)
        if "protagonist_summary" in api_enhancements:
            story_map["protagonist_profile"]["summary"] = api_enhancements["protagonist_summary"]

    story_map["presentation_modes"] = infer_presentation_scores(story_map)
    story_map["presentation_controls"] = infer_presentation_controls(story_map)
    story_map["layout_strategy"] = infer_layout_strategy(story_map)
    story_map["slide_blueprint"] = infer_slide_blueprint(story_map)
    story_map["document_layouts"] = infer_document_layouts(story_map)
    story_map["commercial_positioning"] = infer_commercial_positioning(story_map)
    story_map["audience_profile"] = infer_audience_profile(story_map)
    story_map["strength_index"] = infer_strength_index(story_map)
    story_map["packaging_potential"] = infer_packaging_potential(story_map)
    story_map["character_leverage"] = infer_character_leverage(story_map)
    story_map["tone_comparables"] = infer_tone_comparables(story_map)
    story_map["executive_summary"] = infer_executive_summary(story_map)

    story_map["actor_objective"] = infer_actor_objective(story_map)
    story_map["playable_tactics"] = infer_playable_tactics(story_map)
    story_map["emotional_triggers"] = infer_emotional_triggers(story_map)
    story_map["audition_danger_zones"] = infer_audition_danger_zones(story_map)
    story_map["reader_chemistry_tips"] = infer_reader_chemistry_tips(story_map)
    story_map["memorization_beats"] = infer_memorization_beats(story_map)

    story_map["role_arc_map"] = infer_role_arc_map(story_map)
    story_map["pressure_ladder"] = infer_pressure_ladder(story_map)
    story_map["emotional_continuity"] = infer_emotional_continuity(story_map)
    story_map["costume_behavior_clues"] = infer_costume_behavior_clues(story_map)
    story_map["relationship_leverage_map"] = infer_relationship_leverage_map(story_map)
    story_map["set_ready_checklist"] = infer_set_ready_checklist(story_map)

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




def score_terms_for_slide(slide_name: str, story_map: dict) -> dict:
    world = story_map.get("world", "")
    primary_mode = story_map.get("presentation_modes", {}).get("primary_mode", "")
    secondary_mode = story_map.get("presentation_modes", {}).get("secondary_mode", "")
    protagonist = slugify(story_map.get("protagonist", ""))
    weights: dict[str, int] = {}

    def bump(term: str, points: int):
        if not term:
            return
        weights[term] = weights.get(term, 0) + points

    # Global slide-name weighting
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

    # World-specific weighting
    world_map = {
        "feature / action espionage thriller": {
            "base": [("surveillance", 14), ("night_operation", 12), ("hidden_identity", 10)],
            "character": [("split_life", 14), ("covert_pressure", 12), ("domestic_cover", 10)],
            "theme": [("family_risk", 12), ("explosive_reveal", 10), ("high_stakes", 10)],
        },
        "feature / contained urban thriller": {
            "base": [("streetlights", 16), ("car_interior", 14), ("night", 12)],
            "character": [("rearview", 14), ("windshield", 12), ("implied_presence", 10)],
            "theme": [("pressure", 10), ("isolation", 10), ("urban", 8)],
        },
        "feature / legal / courtroom drama": {
            "base": [("courtroom_wide", 16), ("institutional_space", 14), ("military_formality", 10)],
            "character": [("witness_stand", 14), ("command_pressure", 12), ("interrogation_room", 10)],
            "theme": [("truth_under_oath", 12), ("moral_weight", 10), ("verdict_energy", 10)],
        },
        "feature / fantasy satire comedy": {
            "base": [("castle_wide", 16), ("storybook_scale", 14), ("ceremonial_absurdity", 10)],
            "character": [("throne_room", 14), ("comic_intrigue", 12), ("royal_misrule", 10)],
            "theme": [("satirical_pageantry", 12), ("kingdom_chaos", 10), ("comic_resolution", 10)],
        },
        "feature / nightlife comedy": {
            "base": [("club_exterior", 14), ("velvet_rope", 12), ("city_lights", 10)],
            "character": [("awkward_party", 14), ("social_pressure", 12), ("dancefloor", 10)],
            "theme": [("afterparty_fallout", 12), ("neon_regret", 10), ("comic_release", 10)],
        },
        "feature / sports drama": {
            "base": [("arena", 14), ("empty_court", 12), ("night", 8)],
            "character": [("locker_room", 14), ("quiet_pressure", 12), ("hallway", 10)],
            "theme": [("scoreboard", 12), ("after_hours", 10), ("gym", 8)],
        },
    }

    category = "base"
    if slide_name in {"Protagonist", "Antagonist", "Supporting Characters", "Conflict Engine", "Stakes"}:
        category = "character"
    elif slide_name in {"Theme", "Tone", "Why This Film", "Closing Statement"}:
        category = "theme"

    for term, pts in world_map.get(world, {}).get(category, []):
        bump(term, pts)

    # Presentation mode nudges
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




FOLDER_LIBRARY = {
    "01_cinematic_tension": {"tags": ["cinematic", "tension", "pressure", "dark", "dramatic", "statement", "impact"]},
    "02_emotional_grounded": {"tags": ["emotion", "human_energy", "intimate", "warm", "connection", "grounded"]},
    "03_urban_pressure": {"tags": ["urban", "city", "street", "pressure", "traffic", "crowd", "grit"]},
    "04_status_wealth": {"tags": ["luxury", "wealth", "status", "elite", "designer", "premium"]},
    "05_scale_nature": {"tags": ["scale", "wide", "landscape", "epic", "horizon", "nature"]},
    "06_controlled_clean": {"tags": ["clean", "minimal", "controlled", "modern", "disciplined"]},
    "07_night_isolation": {"tags": ["night", "isolation", "nocturnal", "alone", "neon"]},
    "08_daylight_release": {"tags": ["daylight", "hope", "release", "bright", "open"]},
    "09_institutional_authority": {"tags": ["institution", "authority", "formal", "government", "executive"]},
    "10_courtroom_legal": {"tags": ["courtroom", "legal", "judge", "witness", "trial"]},
    "11_military_formal": {"tags": ["military", "uniform", "ceremony", "formation", "formal"]},
    "12_interrogation_pressure": {"tags": ["interrogation", "questioning", "pressure", "table", "suspicion"]},
    "13_fantasy_kingdom": {"tags": ["fantasy", "kingdom", "castle", "village", "storybook"]},
    "14_royal_court": {"tags": ["royal", "court", "throne", "ornate", "regal"]},
    "15_satire_power": {"tags": ["satire", "power", "absurdity", "symbolic", "spectacle"]},
    "16_espionage_covert": {"tags": ["espionage", "covert", "surveillance", "undercover", "shadow"]},
    "17_romance_connection": {"tags": ["romance", "connection", "relationship", "eye_contact", "warmth"]},
    "18_comedy_energy": {"tags": ["comedy", "energy", "awkward", "chaos", "funny"]},
    "19_friendship_loyalty": {"tags": ["friendship", "loyalty", "bond", "support", "group"]},
    "20_home_domestic": {"tags": ["home", "domestic", "kitchen", "apartment", "family"]},
    "21_working_class_realism": {"tags": ["working_class", "labor", "rideshare", "garage", "warehouse", "realism"]},
    "22_rebirth_hope": {"tags": ["rebirth", "hope", "sunrise", "horizon", "redemption"]},
}

def infer_folder_hints_from_terms(terms: list[str], story_map: dict, limit: int = 4) -> list[dict]:
    primary_mode = story_map.get("presentation_modes", {}).get("primary_mode", "")
    world = story_map.get("world", "")
    scores = {}
    term_set = set(t for t in terms if t)

    world_bias = {
        "feature / contained urban thriller": ["01_cinematic_tension", "03_urban_pressure", "07_night_isolation", "21_working_class_realism"],
        "feature / legal / courtroom drama": ["09_institutional_authority", "10_courtroom_legal", "11_military_formal", "12_interrogation_pressure"],
        "feature / fantasy satire comedy": ["13_fantasy_kingdom", "14_royal_court", "15_satire_power", "18_comedy_energy"],
        "feature / nightlife comedy": ["03_urban_pressure", "07_night_isolation", "18_comedy_energy", "19_friendship_loyalty"],
        "feature / action espionage thriller": ["16_espionage_covert", "01_cinematic_tension", "12_interrogation_pressure", "03_urban_pressure"],
        "feature / sports drama": ["21_working_class_realism", "19_friendship_loyalty", "02_emotional_grounded", "05_scale_nature"],
        "feature / crime drama": ["03_urban_pressure", "01_cinematic_tension", "12_interrogation_pressure", "21_working_class_realism"],
    }
    mode_bias = {
        "prestige_authority": ["09_institutional_authority", "10_courtroom_legal", "06_controlled_clean"],
        "tension_pressure": ["01_cinematic_tension", "07_night_isolation", "12_interrogation_pressure"],
        "character_heart": ["02_emotional_grounded", "17_romance_connection", "19_friendship_loyalty"],
        "spectacle_play": ["13_fantasy_kingdom", "14_royal_court", "15_satire_power", "18_comedy_energy"],
    }

    for folder, meta in FOLDER_LIBRARY.items():
        score = 0
        for tag in meta["tags"]:
            if tag in term_set:
                score += 14
            else:
                parts = tag.split('_')
                score += sum(4 for p in parts if p in term_set)
        if folder in world_bias.get(world, []):
            score += max(6, 18 - world_bias[world].index(folder) * 3)
        if folder in mode_bias.get(primary_mode, []):
            score += max(4, 12 - mode_bias[primary_mode].index(folder) * 2)
        if score > 0:
            scores[folder] = score

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [{"folder": f, "score": s} for f, s in ranked]


def infer_file_strategy(slide_name: str, story_map: dict) -> dict:
    composition = story_map.get("layout_strategy", {}).get("composition_bias", "balanced")
    if slide_name in {"Title", "World", "Visual Style", "Closing Statement"}:
        return {"subject_preference": "environment_first", "framing": "wide", "people_density": "low_to_medium", "swap_ready": True}
    if slide_name in {"Protagonist", "Antagonist", "Supporting Characters", "Conflict Engine", "Stakes"}:
        return {"subject_preference": "character_presence", "framing": "medium", "people_density": "medium", "swap_ready": True}
    if slide_name in {"Tone", "Theme", "Why This Film", "Audience", "Comparables"}:
        return {"subject_preference": "mood_symbolic", "framing": "flexible", "people_density": "low", "swap_ready": True}
    return {"subject_preference": composition, "framing": "flexible", "people_density": "medium", "swap_ready": True}

def build_ranked_image_options(slide_name: str, story_map: dict, max_options: int = 5) -> list[dict]:
    base_terms = slide_visual_terms(slide_name, story_map)
    score_map = score_terms_for_slide(slide_name, story_map)
    protagonist = slugify(story_map.get("protagonist", ""))

    option_blueprints = [
        {
            "option_id": "primary",
            "label": "Primary Pick",
            "focus": "balanced",
            "extra_terms": [],
            "boost_terms": ["cinematic", "world", "mood", protagonist],
        },
        {
            "option_id": "tone_alt",
            "label": "Tone Alt",
            "focus": "tone",
            "extra_terms": ["lighting", "texture", "mood"],
            "boost_terms": ["mood", "lighting", "texture"],
        },
        {
            "option_id": "world_alt",
            "label": "World Alt",
            "focus": "world",
            "extra_terms": ["environment", "place", "lived_in"],
            "boost_terms": ["environment", "place", "world"],
        },
        {
            "option_id": "character_alt",
            "label": "Character Alt",
            "focus": "character",
            "extra_terms": [protagonist, "presence", "implied_presence"],
            "boost_terms": [protagonist, "presence", "human_energy", "isolation"],
        },
        {
            "option_id": "statement_alt",
            "label": "Statement Alt",
            "focus": "statement",
            "extra_terms": ["symbolic", "impact", "resonance"],
            "boost_terms": ["symbolic", "impact", "resonance", "statement"],
        },
    ]

    options = []
    for rank, blueprint in enumerate(option_blueprints[:max_options], start=1):
        terms = []
        seen = set()
        for t in base_terms + [term for term in blueprint["extra_terms"] if term]:
            if t and t not in seen:
                seen.add(t)
                terms.append(t)

        score = 100 - ((rank - 1) * 8)
        for term in terms:
            score += score_map.get(term, 0)
        for term in blueprint["boost_terms"]:
            score += score_map.get(term, 0) // 2

        folder_hints = infer_folder_hints_from_terms(terms, story_map, limit=4)
        options.append({
            "rank": rank,
            "score": score,
            "option_id": blueprint["option_id"],
            "label": blueprint["label"],
            "focus": blueprint["focus"],
            "image_query": " ".join(terms),
            "image_tags": terms,
            "folder_hints": folder_hints,
            "visual_family": folder_hints[0]["folder"] if folder_hints else None,
        })

    options.sort(key=lambda item: (-item["score"], item["rank"]))
    for idx, option in enumerate(options, start=1):
        option["rank"] = idx
    return options

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
        ranked_options = build_ranked_image_options(slide_name, story_map, max_options=5)
        primary = ranked_options[0]
        plan.append({
            "slide_number": idx,
            "slide_title": slide_name,
            "image_query": primary["image_query"],
            "image_tags": primary["image_tags"],
            "image_score": primary["score"],
            "preferred_folders": primary.get("folder_hints", []),
            "visual_family": primary.get("visual_family"),
            "file_strategy": infer_file_strategy(slide_name, story_map),
            "image_options": ranked_options,
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
    print(f"🎯 Protagonist Summary: {story_map['protagonist_summary']}")
    print(f"🪞 Theme: {story_map['theme']}")
    print(f"🧠 Story Engine: {story_map['story_engine']}")
    print(f"⚔️ Core Conflict: {story_map['core_conflict']}")
    print(f"🔄 Reversal: {story_map['reversal']}")
    print(f"🧾 Logline: {story_map['logline']}")
    print(f"📚 Synopsis: {story_map['synopsis']}")
    print(f"🎛️ Presentation Modes: {json.dumps(story_map['presentation_modes'], indent=2)}")
    print(f"🎚️ Presentation Controls: {json.dumps(story_map['presentation_controls'], indent=2)}")
    print(f"🧱 Layout Strategy: {json.dumps(story_map['layout_strategy'], indent=2)}")
    print(f"📰 Document Layouts: {json.dumps(story_map['document_layouts'], indent=2)}")
    print(f"🗂️ Slide Blueprint: {json.dumps(story_map['slide_blueprint'], indent=2)}")
    print(f"🖼️ IMAGE PLAN SAMPLE: {json.dumps(story_map['image_plan'][:3], indent=2)}")
    if story_map["image_plan"]:
        print(f"🎞️ IMAGE OPTIONS SAMPLE: {json.dumps(story_map['image_plan'][0].get('image_options', [])[:5], indent=2)}")

    OUT.write_text(json.dumps(story_map, indent=2))


if __name__ == "__main__":
    main()
