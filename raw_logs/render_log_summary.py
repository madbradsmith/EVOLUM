#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

USAGE_RE = re.compile(r"USAGE \| (?P<event>[^|]+?)(?: \| (?P<kv>.*))?$")
ELAPSED_RE = re.compile(r"(?P<secs>\d+)s")

@dataclass
class Event:
    event: str
    data: dict[str, str]
    raw: str

def parse_keyvals(kv_blob: str | None) -> dict[str, str]:
    if not kv_blob:
        return {}
    data: dict[str, str] = {}
    parts = [p.strip() for p in kv_blob.split("|")]
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        data[key.strip()] = value.strip()
    return data

def parse_events(lines: list[str]) -> list[Event]:
    events: list[Event] = []
    for line in lines:
        match = USAGE_RE.search(line)
        if not match:
            continue
        event = match.group("event").strip()
        data = parse_keyvals(match.group("kv"))
        events.append(Event(event=event, data=data, raw=line.rstrip()))
    return events

def extract_seconds(value: str | None) -> int | None:
    if not value:
        return None
    m = ELAPSED_RE.search(value)
    if not m:
        return None
    return int(m.group("secs"))

def average(nums: list[int]) -> float | None:
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)

def summarize(lines: list[str]) -> dict[str, Any]:
    events = parse_events(lines)
    counts = Counter(e.event for e in events)

    beta_success = 0
    beta_fail = 0
    beta_codes = Counter()

    analyze_success_times: list[int] = []
    analyze_failures: list[dict[str, str]] = []

    generate_success_times: list[int] = []
    generate_failures: list[dict[str, str]] = []
    generated_files = Counter()

    http_500_lines: list[str] = []
    app_error_lines: list[str] = []

    for e in events:
        if e.event == "beta_access":
            code = e.data.get("code", "unknown")
            beta_codes[code] += 1
            if e.data.get("success") == "True":
                beta_success += 1
            else:
                beta_fail += 1
        elif e.event == "analyze_complete":
            if e.data.get("success") == "True":
                secs = extract_seconds(e.data.get("elapsed"))
                if secs is not None:
                    analyze_success_times.append(secs)
            else:
                analyze_failures.append(e.data)
        elif e.event == "generate_complete":
            if e.data.get("success") == "True":
                secs = extract_seconds(e.data.get("elapsed"))
                if secs is not None:
                    generate_success_times.append(secs)
                if "filename" in e.data:
                    generated_files[e.data["filename"]] += 1
            else:
                generate_failures.append(e.data)

    for line in lines:
        if " 500 " in line or '" 500 -' in line:
            http_500_lines.append(line.rstrip())
        if "ERROR in app" in line or "Traceback" in line:
            app_error_lines.append(line.rstrip())

    recent_events = [asdict(e) for e in events[-20:]]

    return {
        "overview": {
            "total_usage_events": len(events),
            "event_counts": dict(counts),
        },
        "beta_access": {
            "success_count": beta_success,
            "failure_count": beta_fail,
            "codes_seen": dict(beta_codes),
        },
        "analyze": {
            "runs_completed": len(analyze_success_times),
            "average_seconds": average(analyze_success_times),
            "failures": analyze_failures[-10:],
        },
        "generate": {
            "runs_completed": len(generate_success_times),
            "average_seconds": average(generate_success_times),
            "failures": generate_failures[-10:],
            "files_seen": dict(generated_files),
        },
        "errors": {
            "http_500_lines": http_500_lines[-20:],
            "app_error_lines": app_error_lines[-20:],
        },
        "recent_events": recent_events,
    }

def render_human(summary: dict[str, Any]) -> str:
    out: list[str] = []
    out.append("DEVELOPUM AI — RENDER LOG SUMMARY")
    out.append("=" * 40)
    out.append(f"Total usage events: {summary['overview']['total_usage_events']}")
    out.append("")
    out.append("Event Counts")
    out.append("-" * 40)
    for k, v in sorted(summary["overview"]["event_counts"].items()):
        out.append(f"{k}: {v}")
    out.append("")
    out.append("Beta Access")
    out.append("-" * 40)
    out.append(f"Successes: {summary['beta_access']['success_count']}")
    out.append(f"Failures: {summary['beta_access']['failure_count']}")
    if summary['beta_access']['codes_seen']:
        out.append("Codes seen:")
        for k, v in sorted(summary['beta_access']['codes_seen'].items(), key=lambda kv: (-kv[1], kv[0])):
            out.append(f"  {k}: {v}")
    out.append("")
    out.append("Analyze")
    out.append("-" * 40)
    out.append(f"Completed runs: {summary['analyze']['runs_completed']}")
    out.append(f"Average time: {summary['analyze']['average_seconds']}s")
    if summary['analyze']['failures']:
        out.append("Recent failures:")
        for item in summary['analyze']['failures']:
            out.append(f"  {item}")
    out.append("")
    out.append("Generate Deck")
    out.append("-" * 40)
    out.append(f"Completed runs: {summary['generate']['runs_completed']}")
    out.append(f"Average time: {summary['generate']['average_seconds']}s")
    if summary['generate']['files_seen']:
        out.append("Files generated:")
        for k, v in sorted(summary['generate']['files_seen'].items(), key=lambda kv: (-kv[1], kv[0])):
            out.append(f"  {k}: {v}")
    if summary['generate']['failures']:
        out.append("Recent failures:")
        for item in summary['generate']['failures']:
            out.append(f"  {item}")
    out.append("")
    out.append("Errors / 500s")
    out.append("-" * 40)
    if not summary['errors']['http_500_lines'] and not summary['errors']['app_error_lines']:
        out.append("No recent 500/app errors found in the parsed log.")
    else:
        for line in summary['errors']['http_500_lines']:
            out.append(line)
        for line in summary['errors']['app_error_lines']:
            out.append(line)
    out.append("")
    out.append("Recent Usage Events")
    out.append("-" * 40)
    for event in summary['recent_events']:
        out.append(event.get('raw', ''))
    return "\n".join(out)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("logfile", type=Path, help="Path to exported Render log text file")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of human summary")
    parser.add_argument("--save", type=Path, help="Optional path to save the summary output")
    args = parser.parse_args()

    if not args.logfile.exists():
        print(f"File not found: {args.logfile}", file=sys.stderr)
        return 1

    lines = args.logfile.read_text(encoding="utf-8", errors="replace").splitlines()
    summary = summarize(lines)
    output = json.dumps(summary, indent=2) if args.json else render_human(summary)

    if args.save:
        args.save.write_text(output, encoding="utf-8")
        print(f"Saved summary to: {args.save}")
    else:
        print(output)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
