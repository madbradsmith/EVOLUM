#!/usr/bin/env python3
"""
rename_visuals.py
Renames all stock images to: {genre}_{folder_theme}_{number}.ext
Run once. Safe to re-run — already-renamed files are skipped.
"""

import re
import shutil
from pathlib import Path

VISUALS_DIR = Path(__file__).resolve().parent / "visuals"

FOLDER_GENRE = {
    "01_cinematic_tension":     ("thriller",    "cinematic_tension"),
    "01_cinematic_tension_02":  ("thriller",    "cinematic_tension"),
    "02_emotional_grounded":    ("drama",       "emotional_grounded"),
    "02_emotional_grounded_02": ("drama",       "emotional_grounded"),
    "03_urban_pressure":        ("urban",       "urban_pressure"),
    "04_status_wealth":         ("prestige",    "status_wealth"),
    "05_scale_nature":          ("adventure",   "scale_nature"),
    "06_controlled_clean":      ("scifi",       "controlled_clean"),
    "07_night_isolation":       ("noir",        "night_isolation"),
    "08_daylight_release":      ("hope",        "daylight_release"),
    "09_institutional_authority":("political",  "institutional_authority"),
    "10_courtroom_legal":       ("legal",       "courtroom_legal"),
    "11_military_formal":       ("war",         "military_formal"),
    "12_interrogation_pressure":("crime",       "interrogation_pressure"),
    "13_fantasy_kingdom":       ("fantasy",     "fantasy_kingdom"),
    "14_royal_court":           ("historical",  "royal_court"),
    "15_satire_power":          ("satire",      "satire_power"),
    "16_espionage_covert":      ("espionage",   "espionage_covert"),
    "17_romance_connection":    ("romance",     "romance_connection"),
    "18_comedy_energy":         ("comedy",      "comedy_energy"),
    "19_friendship_loyalty":    ("friendship",  "friendship_loyalty"),
    "20_home_domestic":         ("domestic",    "home_domestic"),
    "21_working_class_realism": ("realism",     "working_class_realism"),
    "22_rebirth_hope":          ("hope",        "rebirth_hope"),
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

ALREADY_NAMED = re.compile(
    r"^(thriller|drama|urban|prestige|adventure|scifi|noir|hope|political|legal|war|crime|fantasy|historical|satire|espionage|romance|comedy|friendship|domestic|realism|rebirth)_[a-z_]+_\d{3,}\.(jpg|jpeg|png|webp)$"
)

def merge_and_rename():
    # Step 1: merge _02 folders into their parent
    for folder_name, (genre, theme) in FOLDER_GENRE.items():
        if not folder_name.endswith("_02"):
            continue
        src_dir = VISUALS_DIR / folder_name
        if not src_dir.exists():
            continue
        base_name = folder_name.replace("_02", "")
        dst_dir = VISUALS_DIR / base_name
        dst_dir.mkdir(exist_ok=True)
        moved = 0
        for f in src_dir.iterdir():
            if f.suffix.lower() in IMAGE_EXTS:
                shutil.move(str(f), str(dst_dir / f.name))
                moved += 1
        print(f"  Merged {moved} files from {folder_name} → {base_name}")
        src_dir.rmdir() if not any(src_dir.iterdir()) else None

    # Step 2: delete zip files inside visuals
    for z in VISUALS_DIR.glob("*.zip"):
        z.unlink()
        print(f"  Deleted zip: {z.name}")

    # Step 3: rename all images in each main folder
    total_renamed = 0
    total_skipped = 0

    main_folders = [k for k in FOLDER_GENRE if not k.endswith("_02")]

    for folder_name in main_folders:
        folder_dir = VISUALS_DIR / folder_name
        if not folder_dir.exists():
            continue

        genre, theme = FOLDER_GENRE[folder_name]
        images = sorted(
            [f for f in folder_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS],
            key=lambda f: f.name
        )

        counter = 1
        renamed = 0
        skipped = 0

        for img in images:
            if ALREADY_NAMED.match(img.name.lower()):
                skipped += 1
                continue

            ext = img.suffix.lower()
            if ext == ".jpeg":
                ext = ".jpg"

            new_name = f"{genre}_{theme}_{counter:03d}{ext}"
            new_path = folder_dir / new_name

            # avoid collision
            while new_path.exists() and new_path != img:
                counter += 1
                new_name = f"{genre}_{theme}_{counter:03d}{ext}"
                new_path = folder_dir / new_name

            img.rename(new_path)
            counter += 1
            renamed += 1

        print(f"  {folder_name}: {renamed} renamed, {skipped} already done")
        total_renamed += renamed
        total_skipped += skipped

    print(f"\nDone. {total_renamed} renamed, {total_skipped} skipped.")


if __name__ == "__main__":
    print("Renaming visuals...\n")
    merge_and_rename()
