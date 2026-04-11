import re
import json
import sys
import subprocess
from pathlib import Path
from pypdf import PdfReader

APP_DIR = Path(__file__).resolve().parent
ROOT_INPUT_PATH = APP_DIR / "input.txt"
STATUS_PATH = APP_DIR / "status.json"
ANALYSIS_ERROR_PATH = APP_DIR / "pipeline" / "analysis" / "analysis_error_report.json"

USER_MSG = "PDF text extraction failed. Please upload a valid screenplay PDF or use TXT/FDX format."


def write_root_input(text: str):
    ROOT_INPUT_PATH.write_text(text, encoding="utf-8")
    return str(ROOT_INPUT_PATH)


def _looks_like_gibberish_line(line: str) -> bool:
    if not line.strip():
        return False

    symbol_ratio = sum(not c.isalnum() and not c.isspace() for c in line) / max(len(line), 1)
    long_token = re.search(r"[A-Z0-9%&*/]{6,}", line)

    return symbol_ratio > 0.25 or bool(long_token)


def _gibberish_ratio(text: str) -> float:
    lines = text.splitlines()
    if not lines:
        return 1.0

    bad = sum(1 for l in lines if _looks_like_gibberish_line(l))
    return bad / len(lines)


def _looks_like_readable_text(text: str) -> bool:
    words = re.findall(r"[A-Za-z]{2,}", text)
    return len(words) > 80


def validate_pdf_text(text: str):
    text = (text or "").strip()

    if len(text) < 500:
        return False, "Too short"

    lowered = text.lower()

    if "%pdf" in lowered or "reportlab" in lowered:
        return False, "PDF markers present"

    if re.search(r"\bendobj\b", lowered):
        return False, "PDF object markers present"

    if not _looks_like_readable_text(text):
        return False, "Not enough readable text"

    gib_ratio = _gibberish_ratio(text)
    if gib_ratio > 0.25:
        return False, f"Gibberish ratio too high: {gib_ratio:.2f}"

    return True, ""


def score_extraction(text: str) -> tuple:
    text = (text or "").strip()
    if not text:
        return (0, 0, 1.0, 0)

    words = len(re.findall(r"[A-Za-z]{2,}", text))
    gib_ratio = _gibberish_ratio(text)
    lines = max(len(text.splitlines()), 1)
    return (words, len(text), gib_ratio, lines)


def normalize_extracted_text(text: str) -> str:
    text = text or ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_with_pypdf(input_path: str) -> str:
    reader = PdfReader(input_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return normalize_extracted_text(text)


def extract_pdf_with_pdftotext(input_path: str) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", input_path, "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "pdftotext failed")
    return normalize_extracted_text(result.stdout)


def fail_pipeline(input_path: str, reason: str):
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ANALYSIS_ERROR_PATH.parent.mkdir(parents=True, exist_ok=True)

    status = {
        "state": "error",
        "step": "input_handler",
        "message": USER_MSG,
        "detail": reason,
    }

    error = {
        "status": "failed",
        "stage": "input_validation",
        "message": USER_MSG,
        "detail": reason,
    }

    STATUS_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")
    ANALYSIS_ERROR_PATH.write_text(json.dumps(error, indent=2), encoding="utf-8")

    print("❌ VALIDATION FAILED:", reason)
    sys.exit(1)


def extract_pdf_text(input_path: str) -> str:
    candidates = []

    try:
        pypdf_text = extract_pdf_with_pypdf(input_path)
        candidates.append(("pypdf", pypdf_text, score_extraction(pypdf_text)))
    except Exception:
        pass

    try:
        pdftotext_text = extract_pdf_with_pdftotext(input_path)
        candidates.append(("pdftotext", pdftotext_text, score_extraction(pdftotext_text)))
    except Exception:
        pass

    if not candidates:
        fail_pipeline(input_path, "PDF extraction failed with all available methods")

    candidates.sort(key=lambda x: (x[2][0], -x[2][2], x[2][1]), reverse=True)
    best_method, best_text, _ = candidates[0]
    print(f"📘 Using extractor: {best_method}")
    return best_text


def main():
    if len(sys.argv) < 2:
        print("❌ No input file provided")
        sys.exit(1)

    input_path = sys.argv[1]
    ext = Path(input_path).suffix.lower()

    if ext == ".pdf":
        print("📕 Extracting PDF...")
        text = extract_pdf_text(input_path)

        valid, reason = validate_pdf_text(text)
        if not valid:
            fail_pipeline(input_path, reason)

        write_root_input(text)
        print("✅ PDF accepted")
        return

    text = Path(input_path).read_text(encoding="utf-8", errors="ignore")
    write_root_input(text)
    print("✅ Input accepted")


if __name__ == "__main__":
    main()
