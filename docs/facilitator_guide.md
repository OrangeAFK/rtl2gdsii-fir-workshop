# Facilitator guide

Companion to [`ASIC_PD_Workshop_Design.md`](../ASIC_PD_Workshop_Design.md). Use this on day-of and for pre-cohort calibration.

## Pre-session (T−1 day or earlier)

1. Publish / pull the pinned image: `ghcr.io/orangeafk/rtl2gdsii-fir-workshop:2026.1`
2. Tell students to `docker compose pull` (or `build`) **before** arrival — session is network-free for PDK/tools.
3. Confirm GUI path on your demo machine (WSLg / XQuartz / screenshare fallback).
4. Run the **Calibration Checklist** below on the exact image digest you will ship.
5. Refresh [`reports/golden/`](../reports/golden/) text reports after calibration.
6. Time Implementation B full flow; if >10 minutes on workshop hardware, plan to show the cached/golden B run live.

## Calibration Checklist (every cohort / every image bump)

Tool and PDK revisions can flip a marginal constraint. Before each cohort:

1. Full flow for **Implementation A** (`fir_naive`) on the workshop image.
2. Record synth-stage WNS (`reports/fir_naive/synth/report_checks.rpt`) and post-route WNS (`./run_stage.sh sta --spef`).
3. Binary-search `clk_period` in [`design/constraints_a.sdc`](../design/constraints_a.sdc) (and the same value in `constraints_b.sdc` + `CLOCK_PERIOD` in configs) until:
   - synth WNS is **small and positive** (~0.1–0.5 ns)
   - post-route WNS is **clearly negative** (at least a few hundred ps)
4. Confirm **Implementation B** at the **same** period has **positive** post-route slack.
5. Confirm A configs keep timing checkers from aborting the reveal:
   - `QUIT_ON_TIMING_VIOLATIONS: false`
   - resizer / repair disabled on A (see `config/config_naive.json`)
6. Copy text reports into `reports/golden/` and write `reports/golden/CALIBRATION.md` with:
   - image digest
   - OpenLane tag
   - clock period
   - WNS numbers (A synth, A post-route, B post-route)
7. Dry-run Stage 7 timing window.

### If Failure 2 will not land

| Symptom | Try |
|---------|-----|
| A already fails at synth | Loosen (increase) period slightly |
| A still passes post-route | Tighten period; confirm SPEF STA; confirm repair/resizer off on A |
| B fails post-route | Loosen period slightly, or allow B repair; re-check pipeline RTL |
| Flow aborts on setup violations | Ensure `QUIT_ON_*_VIOLATIONS` false on A |

## Minute-by-minute cues

| Time | Move | Do not |
|------|------|--------|
| 0:00 | Confirm containers up; show RTL→GDSII once | Install tools live |
| 0:05 | Walk `fir_naive.v`; ask Prediction Q1 | Run synth before the bet |
| 0:12 | `./run_stage.sh synth`; open synth reports | Editorialize the positive slack |
| 0:20 | Floorplan + place @ 0.45; OpenROAD GUI | Skip the healthy placement view |
| 0:30 | High-density place side experiment; reset to 0.45 | Carry 0.85 into routing |
| 0:38 | CTS; wait for “why new buffers?” | Lecture skew before the question |
| 0:48 | Route; KLayout via zoom | Treat clean route as “timing done” |
| 0:56 | `sta --spef`; same `report_checks` as minute 18 | Explain before the room reacts |
| 1:04 | Trace worst path (8-term chain) | Jump straight to the fix |
| 1:10 | Diff pipelined RTL; show B results (live or golden) | Change the clock period here |
| 1:20 | Signoff DRC/LVS; orthogonal to STA | Equate DRC with timing |
| 1:26 | Concept map + interview Q lightning round | Introduce new tools |

## Prediction questions (ask live)

1. Will a “generous” clock for 8-bit logic stay fine to the end of the flow?
2. What happens to placement time / routing if utilization goes 45% → 85%?
3. Why did CTS add ~40 cells we never wrote?
4. Same STA command as minute 18 — what changed?
5. Smallest RTL change you would try first?

## Discussion prompts

- Why is a *marginal* constraint more educational than an obviously impossible one?
- When is one cycle of FIR latency a dealbreaker?
- Why do you need STA **and** DRC **and** LVS?
- Fix A without touching RTL — what are your options and costs?

## Cross-platform notes

- Students run **only** via Docker (Windows / macOS / Linux).
- Bash scripts are container-primary; do not demo native PowerShell flows.
- Prefer multi-arch image tested on amd64 + arm64; recalibrate if arch drifts.
- GUI unevenness: screenshare + golden views keep the spine intact.

## Take-home exercises (prompts only)

See design doc §15: balanced adder tree, 16 taps, SS corner, wider data, two-stage pipeline.
