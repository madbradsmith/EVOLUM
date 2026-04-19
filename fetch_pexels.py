#!/usr/bin/env python3
"""
fetch_pexels.py — Download ~3000 additional stock images from Pexels.
Adds ~130 new images per visual category folder.
Run: python3 fetch_pexels.py
"""

import os
import time
import requests
from pathlib import Path

API_KEY = "ESnGA1QprAQm9DsMq3B8OzHMIt3qLVSBLWCSbAipl8hBilEK4Z3TnyAX"
VISUALS_DIR = Path(__file__).resolve().parent / "visuals"
TARGET_PER_FOLDER = 130
PER_PAGE = 80  # Pexels max

FOLDER_QUERIES = {
    "01_cinematic_tension":       ["cinematic dramatic lighting", "dark moody film", "tension suspense scene"],
    "02_emotional_grounded":      ["emotional moment close up", "human drama portrait", "raw emotion face"],
    "03_urban_pressure":          ["city street pressure", "urban crowd rush", "busy city life"],
    "04_status_wealth":           ["luxury lifestyle wealth", "executive power office", "high status fashion"],
    "05_scale_nature":            ["epic landscape vast", "mountain wilderness scale", "dramatic sky horizon"],
    "06_controlled_clean":        ["minimal clean architecture", "modern interior design", "corporate precision"],
    "07_night_isolation":         ["night city alone", "dark street isolation", "urban night solitude"],
    "08_daylight_release":        ["golden hour freedom", "sunrise hope outdoor", "bright daylight relief"],
    "09_institutional_authority": ["government building authority", "institutional hallway", "formal architecture power"],
    "10_courtroom_legal":         ["courtroom justice", "legal proceeding trial", "lawyer attorney"],
    "11_military_formal":         ["military uniform formal", "soldier ceremony", "armed forces discipline"],
    "12_interrogation_pressure":  ["interrogation room dark", "pressure confrontation", "tense conversation"],
    "13_fantasy_kingdom":         ["fantasy castle kingdom", "medieval epic landscape", "mythical world"],
    "14_royal_court":             ["royal palace throne", "monarchy ceremony", "regal elegance"],
    "15_satire_power":            ["political satire crowd", "protest demonstration", "power corruption"],
    "16_espionage_covert":        ["spy covert shadows", "surveillance secret", "night operation stealth"],
    "17_romance_connection":      ["couple romance intimate", "love connection tender", "romantic moment"],
    "18_comedy_energy":           ["comedy laughter fun", "group celebration energy", "playful humor"],
    "19_friendship_loyalty":      ["friends together bond", "loyalty trust group", "camaraderie team"],
    "20_home_domestic":           ["home family domestic", "kitchen living room warm", "suburban house life"],
    "21_working_class_realism":   ["working class labor", "blue collar worker", "factory construction worker"],
    "22_rebirth_hope":            ["hope renewal sunrise", "new beginning fresh start", "rebirth transformation"],
}


def existing_count(folder: Path) -> int:
    return len(list(folder.glob("*.jpg")) + list(folder.glob("*.png")))


def next_index(folder: Path) -> int:
    files = list(folder.glob("*.jpg")) + list(folder.glob("*.png"))
    if not files:
        return 1
    nums = []
    for f in files:
        parts = f.stem.split("_")
        if parts and parts[-1].isdigit():
            nums.append(int(parts[-1]))
    return (max(nums) + 1) if nums else len(files) + 1


def download_for_folder(folder_name: str, queries: list[str]) -> None:
    folder = VISUALS_DIR / folder_name
    folder.mkdir(exist_ok=True)

    current = existing_count(folder)
    needed = max(0, TARGET_PER_FOLDER - current + current)  # always add TARGET_PER_FOLDER new
    needed = TARGET_PER_FOLDER
    print(f"\n📁 {folder_name} — {current} existing, adding up to {needed}")

    downloaded = 0
    idx = next_index(folder)
    prefix = folder_name.split("_", 1)[1] if "_" in folder_name else folder_name

    for query in queries:
        if downloaded >= needed:
            break
        page = 1
        while downloaded < needed:
            try:
                resp = requests.get(
                    "https://api.pexels.com/v1/search",
                    headers={"Authorization": API_KEY},
                    params={
                        "query": query,
                        "per_page": PER_PAGE,
                        "page": page,
                        "orientation": "landscape",
                    },
                    timeout=15,
                )
                if resp.status_code == 429:
                    print("  ⚠ Rate limited — sleeping 60s")
                    time.sleep(60)
                    continue
                if resp.status_code != 200:
                    print(f"  ✗ Error {resp.status_code} for query '{query}'")
                    break

                data = resp.json()
                photos = data.get("photos", [])
                if not photos:
                    break

                for photo in photos:
                    if downloaded >= needed:
                        break
                    url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large")
                    if not url:
                        continue
                    filename = folder / f"{prefix}_{idx:03d}.jpg"
                    try:
                        img_resp = requests.get(url, timeout=20)
                        if img_resp.status_code == 200:
                            filename.write_bytes(img_resp.content)
                            downloaded += 1
                            idx += 1
                            if downloaded % 20 == 0:
                                print(f"  ✓ {downloaded}/{needed}")
                    except Exception as e:
                        print(f"  ✗ Download failed: {e}")
                    time.sleep(0.05)

                if not data.get("next_page"):
                    break
                page += 1
                time.sleep(0.3)

            except Exception as e:
                print(f"  ✗ Request error: {e}")
                break

    print(f"  ✅ Done — {downloaded} new images added to {folder_name}")


def main():
    print(f"🎬 Pexels fetch starting — target {TARGET_PER_FOLDER} new images per folder")
    print(f"📂 Visuals dir: {VISUALS_DIR}")
    total = 0
    for folder_name, queries in FOLDER_QUERIES.items():
        before = existing_count(VISUALS_DIR / folder_name)
        download_for_folder(folder_name, queries)
        after = existing_count(VISUALS_DIR / folder_name)
        total += (after - before)
    print(f"\n🏁 Complete — {total} total new images downloaded")


if __name__ == "__main__":
    main()
