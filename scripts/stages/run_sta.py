#!/usr/bin/env python3
"""Extract / re-run STA reports for the workshop reveal."""

from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def workshop_root() -> Path:
    return Path(__file__).resolve().parents[2]


def find_run(design: str) -> Path | None:
    root = workshop_root() / "runs"
    if not root.exists():
        return None
    matches = sorted(
        [p for p in root.rglob("*") if p.is_dir() and design in p.name],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    # Prefer deepest run dirs that contain step folders
    for m in matches:
        if any(m.glob("*-*")):
            return m
    return matches[0] if matches else None


def collect_sta_reports(run_path: Path, want_spef: bool) -> list[Path]:
    patterns = [
        "**/stapostpnr*/reports/**",
        "**/sta*/reports/**",
        "**/report*checks*",
        "**/*wns*",
        "**/*timing*",
    ]
    if not want_spef:
        patterns = [
            "**/staprepnr*/reports/**",
            "**/sta*/reports/**",
            "**/report*checks*",
        ]
    files: list[Path] = []
    for pat in patterns:
        for f in glob.glob(str(run_path / pat), recursive=True):
            p = Path(f)
            if p.is_file():
                files.append(p)
    return files


def write_path_report(src_files: list[Path], dest: Path) -> None:
    """Pick the richest timing report and copy as worst_path.rpt."""
    best = None
    best_score = -1
    for f in src_files:
        try:
            text = f.read_text(errors="ignore")
        except OSError:
            continue
        score = 0
        if "Startpoint" in text or "startpoint" in text:
            score += 5
        if "Endpoint" in text or "endpoint" in text:
            score += 5
        if "slack" in text.lower():
            score += 2
        if "path_delay" in text.lower() or "Path Type" in text:
            score += 3
        if len(text) > best_score:
            # prefer content-rich path reports
            pass
        if score > best_score:
            best_score = score
            best = f
    if best is None and src_files:
        best = src_files[0]
    if best is None:
        dest.write_text(
            "No path report found in the OpenLane run directory.\n"
            "Re-run: ./run_stage.sh route && ./run_stage.sh sta --spef --path-report\n"
        )
        return
    shutil.copy2(best, dest)


def try_openroad_path_report(design: str, out_dir: Path, spef: bool) -> bool:
    """Optional: invoke OpenROAD if odb+spef+sdc are available."""
    reports = workshop_root() / "reports" / design
    odb_candidates = list(reports.rglob("design.odb")) + list(
        (workshop_root() / "runs").rglob("*.odb")
    )
    spef_candidates = list(reports.rglob("*.spef")) + list(
        (workshop_root() / "runs").rglob("*.spef")
    )
    sdc = workshop_root() / "design" / (
        "constraints_b.sdc" if design == "fir_pipelined" else "constraints_a.sdc"
    )
    if not odb_candidates or not sdc.exists():
        return False
    odb = odb_candidates[0]
    spef_file = spef_candidates[0] if spef and spef_candidates else None

    tcl = out_dir / "_sta_path.tcl"
    lines = [
        f"read_db {{{odb.as_posix()}}}",
        f"read_sdc {{{sdc.as_posix()}}}",
    ]
    if spef_file:
        lines.append(f"read_spef {{{spef_file.as_posix()}}}")
    lines += [
        f"report_checks -path_delay max -fields {{slew cap input_pins nets fanout}} "
        f"-digits 3 > {(out_dir / 'worst_path.rpt').as_posix()}",
        f"report_checks -path_delay max -format full_clock_expanded -digits 3 "
        f"> {(out_dir / 'report_checks.rpt').as_posix()}",
        "exit",
    ]
    tcl.write_text("\n".join(lines) + "\n")
    try:
        subprocess.run(["openroad", "-exit", str(tcl)], check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def summarize_wns(report: Path) -> str:
    text = report.read_text(errors="ignore")
    m = re.search(r"(wns|WNS|worst\s+slack)\s*[:=]?\s*(-?\d+\.?\d*)", text, re.I)
    if m:
        return f"Detected WNS-like value: {m.group(2)}"
    if "slack" in text.lower():
        return "Slack figures present — open report_checks.rpt"
    return "Could not parse WNS automatically"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", default=os.environ.get("DESIGN", "fir_naive"))
    parser.add_argument("--spef", action="store_true", help="Prefer post-route SPEF STA")
    parser.add_argument(
        "--path-report",
        action="store_true",
        help="Also write worst_path.rpt",
    )
    args = parser.parse_args()

    out_dir = workshop_root() / "reports" / args.design / "sta"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Try live OpenROAD first when SPEF/path requested
    if args.spef or args.path_report:
        if try_openroad_path_report(args.design, out_dir, spef=args.spef):
            print(f"[ok] OpenROAD STA -> {out_dir}")
            print(summarize_wns(out_dir / "report_checks.rpt"))
            return 0

    run_path = find_run(args.design)
    if run_path is None:
        # Fall back to already-copied synth reports for comparison demos
        synth = workshop_root() / "reports" / args.design / "synth" / "report_checks.rpt"
        if synth.exists() and not args.spef:
            shutil.copy2(synth, out_dir / "report_checks.rpt")
            print(f"[ok] copied synth STA to {out_dir}")
            return 0
        print(
            "No run directory found. Run ./run_stage.sh route (and synth) first.",
            file=sys.stderr,
        )
        return 1

    files = collect_sta_reports(run_path, want_spef=args.spef)
    if not files:
        print(f"No STA reports under {run_path}", file=sys.stderr)
        return 1

    # Prefer a file that looks like report_checks
    primary = None
    for f in files:
        if "check" in f.name.lower() or "sta" in f.name.lower():
            primary = f
            break
    primary = primary or files[0]
    shutil.copy2(primary, out_dir / "report_checks.rpt")

    if args.path_report:
        write_path_report(files, out_dir / "worst_path.rpt")

    print(f"[ok] STA reports from {run_path} -> {out_dir}")
    print(summarize_wns(out_dir / "report_checks.rpt"))
    print(
        "Compare with: cat reports/{}/synth/report_checks.rpt".format(args.design)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
