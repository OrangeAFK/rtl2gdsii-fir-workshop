#!/usr/bin/env python3
"""Side-by-side synth vs post-route report_checks for the timing reveal."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def workshop_root() -> Path:
    return Path(__file__).resolve().parents[1]


def extract_metrics(text: str) -> dict[str, str]:
    metrics: dict[str, str] = {}
    patterns = {
        "wns": r"(?:wns|WNS|worst(?:\s+negative)?\s+slack)\s*[:=]?\s*(-?\d+\.?\d*)",
        "tns": r"(?:tns|TNS|total\s+negative\s+slack)\s*[:=]?\s*(-?\d+\.?\d*)",
        "slack": r"(?:^\s*slack\s*[:=\[]\s*|slack\s+)\(?(-?\d+\.?\d*)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text, re.I | re.M)
        if m:
            metrics[key] = m.group(1)
    # Endpoint hint
    m = re.search(r"(?:Endpoint|endpoint)\s*[:=]?\s*(\S+)", text)
    if m:
        metrics["endpoint"] = m.group(1)
    return metrics


def load(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(errors="ignore")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", default="fir_naive")
    args = parser.parse_args()

    root = workshop_root()
    synth = root / "reports" / args.design / "synth" / "report_checks.rpt"
    post = root / "reports" / args.design / "sta" / "report_checks.rpt"

    st = load(synth)
    pt = load(post)
    if not st and not pt:
        print("No reports found. Run synth and sta --spef first.", file=sys.stderr)
        return 1

    sm = extract_metrics(st)
    pm = extract_metrics(pt)

    print(f"Design: {args.design}")
    print(f"{'Metric':<12} {'Synth STA':<16} {'Post-route STA':<16}")
    print("-" * 48)
    for key in ("wns", "tns", "slack", "endpoint"):
        print(f"{key:<12} {sm.get(key, '—'):<16} {pm.get(key, '—'):<16}")

    print()
    if sm.get("wns") and pm.get("wns"):
        try:
            if float(sm["wns"]) >= 0 and float(pm["wns"]) < 0:
                print(
                    "Narrative check: synth WNS >= 0 and post-route WNS < 0 — Failure 2 landed."
                )
            else:
                print(
                    "Narrative check: unexpected WNS polarity — recalibrate CLOCK_PERIOD "
                    "(see docs/facilitator_guide.md)."
                )
        except ValueError:
            pass

    print(f"\nFiles:\n  {synth}\n  {post}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
