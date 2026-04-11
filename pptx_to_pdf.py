#!/usr/bin/env python3
"""
pptx_to_pdf.py

Converts a PowerPoint deck to PDF using LibreOffice in headless mode.

Usage:
    python3 pptx_to_pdf.py /home/madbrad/app/pitch_deck_v5.pptx

Output:
    Writes the PDF into the same folder as the input PPTX.
"""

import subprocess
import sys
from pathlib import Path


def convert_pptx_to_pdf(input_path: Path) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if input_path.suffix.lower() != ".pptx":
        raise ValueError("Input file must be a .pptx")

    output_dir = input_path.parent

    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(input_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            "LibreOffice conversion failed.\n"
            f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        )

    output_pdf = output_dir / f"{input_path.stem}.pdf"

    if not output_pdf.exists():
        raise RuntimeError(
            "Conversion command completed, but PDF was not created.\n"
            f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        )

    return output_pdf


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 pptx_to_pdf.py /path/to/deck.pptx")
        sys.exit(1)

    input_path = Path(sys.argv[1]).expanduser().resolve()

    try:
        output_pdf = convert_pptx_to_pdf(input_path)
        print(f"✅ PDF created: {output_pdf}")
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
