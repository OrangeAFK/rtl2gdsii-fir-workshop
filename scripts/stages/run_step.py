#!/usr/bin/env python3
"""Run OpenLane 2 Classic flow up to a pedagogical workshop stage."""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Pedagogical stage -> last Classic step id (inclusive).
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


def reports_dir_for(design: str, stage: str, tag: str | None) -> Path:
    root = workshop_root()
    if stage == "place" and tag:
        return root / "reports" / design / "place" / tag
    return root / "reports" / design / stage


def find_run_dir(root: Path, design: str, run_tag: str) -> Path | None:
    """Return the OpenLane run root (contains 01-*, 02-*, flow.log), not a step subdir."""
    candidates = [
        root / "runs" / run_tag,
        root / "runs" / design / run_tag,
        root / "runs" / design,
    ]
    for c in candidates:
        if c.is_dir() and (
            (c / "flow.log").exists()
            or any(c.glob("[0-9][0-9]-*"))
        ):
            return c
    runs = root / "runs"
    if not runs.exists():
        return None
    dirs = sorted(
        [
            p
            for p in runs.iterdir()
            if p.is_dir() and ((p / "flow.log").exists() or any(p.glob("[0-9][0-9]-*")))
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return dirs[0] if dirs else None


def _first_match(run_path: Path, patterns: list[str]) -> Path | None:
    for pat in patterns:
        hits = sorted(glob.glob(str(run_path / pat), recursive=True))
        for hit in hits:
            p = Path(hit)
            if p.is_file():
                return p
    return None


def copy_artifacts(run_path: Path, out_dir: Path, stage: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Prefer typical corner STA; fall back to summary / any checks.rpt
    if stage in {"synth", "sta"}:
        stat = _first_match(
            run_path,
            [
                "**/yosys-synthesis/reports/stat.rpt",
                "**/06-yosys-synthesis/reports/stat.rpt",
                "**/synthesis*/reports/stat.rpt",
            ],
        )
        if stat:
            shutil.copy2(stat, out_dir / "synth_stat.rpt")

        checks = _first_match(
            run_path,
            [
                "**/*staprepnr*/nom_tt*/checks.rpt",
                "**/*stapostpnr*/nom_tt*/checks.rpt",
                "**/*staprepnr*/summary.rpt",
                "**/*stapostpnr*/summary.rpt",
                "**/*staprepnr*/**/checks.rpt",
                "**/*stapostpnr*/**/checks.rpt",
                "**/checks.rpt",
            ],
        )
        if checks:
            shutil.copy2(checks, out_dir / "report_checks.rpt")

        nl = _first_match(run_path, ["**/yosys-synthesis/*.nl.v", "**/*.nl.v"])
        if nl:
            shutil.copy2(nl, out_dir / nl.name)

    view_patterns = {
        "floorplan": ["**/openroad-floorplan/*.odb", "**/*floorplan*/**/*.odb", "**/*.odb"],
        "place": ["**/openroad-detailedplacement/*.odb", "**/*detailedplacement*/**/*.odb", "**/*.odb"],
        "cts": ["**/openroad-cts/*.odb", "**/*cts*/**/*.odb", "**/*.odb"],
        "route": [
            "**/*detailedrouting*/**/*.odb",
            "**/*.odb",
            "**/*.gds",
            "**/*.spef",
        ],
        "signoff": ["**/*.gds", "**/drc*.rpt", "**/lvs*.rpt", "**/*drc*", "**/*lvs*"],
        "all": ["**/*.gds", "**/drc*.rpt", "**/lvs*.rpt", "**/*.spef"],
    }
    if stage in view_patterns:
        for pat in view_patterns[stage]:
            for src in glob.glob(str(run_path / pat), recursive=True):
                src_path = Path(src)
                if not src_path.is_file():
                    continue
                dest_name = src_path.name
                if src_path.suffix in {".odb", ".gds", ".def", ".spef"}:
                    dest_name = f"design{src_path.suffix}"
                dest = out_dir / dest_name
                if not dest.exists():
                    shutil.copy2(src_path, dest)
                # Prefer one of each view type
                if src_path.suffix in {".odb", ".gds"} and dest.exists():
                    break


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", default=os.environ.get("DESIGN", "fir_naive"))
    parser.add_argument("--stage", choices=sorted(STAGE_TO_STEP.keys()))
    parser.add_argument("--to", help="Raw OpenLane step id (overrides --stage)")
    parser.add_argument("--tag", default=None)
    parser.add_argument("--with-drc-lvs", action="store_true")
    args = parser.parse_args()

    stage = args.stage
    to_step = args.to
    if stage:
        to_step = STAGE_TO_STEP[stage]
    if not to_step:
        raise SystemExit("provide --stage or --to")

    if not stage:
        for name, step in STAGE_TO_STEP.items():
            if step == to_step:
                stage = name
                break
        stage = stage or "all"

    root = workshop_root()
    config = resolve_config(args.design, args.tag)
    if not config.exists():
        raise SystemExit(f"missing config: {config}")

    run_tag = args.tag or f"{args.design}_workshop"
    cmd_env = os.environ.copy()
    cmd_env.setdefault("PDK", "sky130A")
    cmd_env.setdefault("STD_CELL_LIBRARY", "sky130_fd_sc_hd")

    # OpenLane 2.3.x: -T/--to stops at a step; -f selects Classic flow.
    ol_cmd = [
        sys.executable,
        "-m",
        "openlane",
        "-f",
        "Classic",
        "-T",
        to_step,
        "--run-tag",
        run_tag,
        "--design-dir",
        str(root),
        "--overwrite",
        str(config),
    ]

    print("Running:", " ".join(ol_cmd), flush=True)
    result = subprocess.run(ol_cmd, cwd=str(root), env=cmd_env)
    if result.returncode != 0:
        return result.returncode

    run_path = find_run_dir(root, args.design, run_tag)
    if run_path is None:
        print(f"warning: no run directory found under {root / 'runs'}", file=sys.stderr)
        return 1

    out_dir = reports_dir_for(args.design, stage, args.tag)
    copy_artifacts(run_path, out_dir, stage)
    print(f"[ok] stage={stage} design={args.design} run={run_path} reports -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
