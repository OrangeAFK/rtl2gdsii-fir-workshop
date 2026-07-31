#!/usr/bin/env python3
"""Run OpenLane 2 Classic flow up to a pedagogical workshop stage."""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import sys
from pathlib import Path

# Pedagogical stage -> last Classic step id to include (inclusive).
# Exact step class names match OpenLane 2 Classic; intermediate steps run too.
STAGE_TO_STEP = {
    "synth": "OpenROAD.STAPrePNR",
    "floorplan": "OpenROAD.Floorplan",
    "place": "OpenROAD.DetailedPlacement",
    "cts": "OpenROAD.CTS",
    "route": "OpenROAD.DetailedRouting",
    "signoff": "Netgen.LVS",
    "all": "Netgen.LVS",
}

DESIGN_CONFIG = {
    "fir_naive": "config_naive.json",
    "fir_pipelined": "config_pipelined.json",
}


def workshop_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_config(design: str, tag: str | None) -> Path:
    root = workshop_root()
    if tag == "high_density" and design == "fir_naive":
        return root / "config" / "config_naive_highdensity.json"
    name = DESIGN_CONFIG.get(design)
    if name is None:
        raise SystemExit(f"unknown design: {design}")
    return root / "config" / name


def run_dir_for(design: str, tag: str | None) -> Path:
    root = workshop_root()
    if tag:
        return root / "runs" / f"{design}_{tag}"
    return root / "runs" / design


def reports_dir_for(design: str, stage: str, tag: str | None) -> Path:
    root = workshop_root()
    if stage == "place" and tag:
        return root / "reports" / design / "place" / tag
    return root / "reports" / design / stage


def find_latest_run(base: Path) -> Path | None:
    if not base.exists():
        return None
    # OpenLane creates timestamped subdirs under the run directory when using -d/-f
    candidates = sorted(
        [p for p in base.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else (base if any(base.iterdir()) else None)


def copy_artifacts(run_path: Path, out_dir: Path, stage: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    patterns = {
        "synth": [
            "**/synthesis*/reports/*",
            "**/yosys*/reports/*",
            "**/staprepnr*/reports/*",
            "**/sta*/reports/*",
            "**/*stat*.rpt",
            "**/report_checks*",
            "**/*.nl.v",
            "**/*synth*.v",
        ],
        "floorplan": ["**/*.odb", "**/*.def", "**/floorplan*/reports/*"],
        "place": ["**/*.odb", "**/*.def", "**/placement*/reports/*", "**/globalplacement*/reports/*"],
        "cts": ["**/*.odb", "**/cts*/reports/*", "**/*cts*"],
        "route": ["**/*.odb", "**/*.gds", "**/routing*/reports/*", "**/*.spef"],
        "signoff": ["**/*.gds", "**/drc*", "**/lvs*", "**/magic*/reports/*", "**/netgen*/reports/*"],
        "all": ["**/*.gds", "**/drc*", "**/lvs*", "**/*.spef", "**/report_checks*"],
    }
    seen = set()
    for pat in patterns.get(stage, ["**/*"]):
        for src in glob.glob(str(run_path / pat), recursive=True):
            src_path = Path(src)
            if not src_path.is_file():
                continue
            # Prefer step report files and design views
            name = src_path.name
            if name in seen and src_path.suffix not in {".odb", ".gds", ".spef", ".def"}:
                continue
            dest_name = name
            if src_path.suffix in {".odb", ".gds", ".def", ".spef"}:
                dest_name = f"design{src_path.suffix}"
            dest = out_dir / dest_name
            shutil.copy2(src_path, dest)
            seen.add(dest_name)

    # Friendly aliases for workshop commands
    for cand in out_dir.glob("*stat*"):
        alias = out_dir / "synth_stat.rpt"
        if not alias.exists():
            shutil.copy2(cand, alias)
    for cand in list(out_dir.glob("*checks*")) + list(out_dir.glob("*sta*")):
        if cand.suffix in {".rpt", ".txt", ".log"} or "report" in cand.name.lower():
            alias = out_dir / "report_checks.rpt"
            if not alias.exists() and cand.is_file():
                shutil.copy2(cand, alias)
                break


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", default=os.environ.get("DESIGN", "fir_naive"))
    parser.add_argument(
        "--stage",
        choices=sorted(STAGE_TO_STEP.keys()),
        help="Pedagogical workshop stage",
    )
    parser.add_argument(
        "--to",
        help="Raw OpenLane step id (overrides --stage mapping)",
    )
    parser.add_argument("--tag", default=None, help="Run tag (e.g. high_density)")
    parser.add_argument(
        "--with-drc-lvs",
        action="store_true",
        help="Accepted for CLI compatibility; signoff/all already include DRC/LVS",
    )
    args = parser.parse_args()

    stage = args.stage
    to_step = args.to
    if stage:
        to_step = STAGE_TO_STEP[stage]
    if not to_step:
        raise SystemExit("provide --stage or --to")

    # Infer stage name for report layout when only --to is given
    if not stage:
        for name, step in STAGE_TO_STEP.items():
            if step == to_step:
                stage = name
                break
        stage = stage or "all"

    config = resolve_config(args.design, args.tag)
    if not config.exists():
        raise SystemExit(f"missing config: {config}")

    run_base = run_dir_for(args.design, args.tag)
    run_base.mkdir(parents=True, exist_ok=True)

    # Prefer OpenLane Python API; fall back to CLI.
    cmd_env = os.environ.copy()
    cmd_env.setdefault("PDK", "sky130A")
    cmd_env.setdefault("STD_CELL_LIBRARY", "sky130_fd_sc_hd")

    import subprocess

    # OpenLane 2 CLI flag spellings vary slightly by version; try known forms.
    # Do not fall back to a bare full-flow run — that would break staged demos.
    attempts = [
        [
            sys.executable, "-m", "openlane",
            "--last-stage", to_step,
            "--run-tag", args.tag or "workshop",
            str(config),
        ],
        [
            sys.executable, "-m", "openlane",
            "--to", to_step,
            "--run-tag", args.tag or "workshop",
            str(config),
        ],
        [
            sys.executable, "-m", "openlane",
            "-t", to_step,
            str(config),
        ],
    ]

    result = None
    for ol_cmd in attempts:
        print("Running:", " ".join(ol_cmd), flush=True)
        result = subprocess.run(
            ol_cmd,
            cwd=str(workshop_root()),
            env=cmd_env,
            capture_output=True,
            text=True,
        )
        sys.stdout.write(result.stdout or "")
        sys.stderr.write(result.stderr or "")
        if result.returncode == 0:
            break
        err = (result.stderr or "") + (result.stdout or "")
        unrecognized = (
            "unrecognized arguments" in err
            or "no such option" in err.lower()
            or "invalid choice" in err.lower()
            or "the following arguments are required" in err.lower()
        )
        if not unrecognized:
            # Flow ran but failed — do not mask with another CLI spelling.
            return result.returncode

    if result is None or result.returncode != 0:
        print(
            "OpenLane CLI could not run the requested stage.\n"
            f"Need a step cut-point for: {to_step}\n"
            "Install/use the pinned workshop image (see README).",
            file=sys.stderr,
        )
        return 1 if result is None else result.returncode

    run_path = find_latest_run(workshop_root() / "runs") or run_base

    # Also search common OpenLane run locations
    if not run_path.exists() or not any(Path(run_path).rglob("*.odb")):
        alt = find_latest_run(workshop_root() / "runs")
        if alt:
            run_path = alt

    out_dir = reports_dir_for(args.design, stage, args.tag)
    copy_artifacts(Path(run_path), out_dir, stage)
    print(f"[ok] stage={stage} design={args.design} reports -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
