# RTL → GDSII FIR Workshop

A 90-minute discovery-based ASIC physical design workshop for interview-ready students (IEEE SSCS).

You implement an 8-tap FIR twice:

1. **`fir_naive`** — ripple-chain MAC. Looks fine after synthesis. Fails after routing once real wire parasitics appear.
2. **`fir_pipelined`** — one register splits the critical path. Same clock constraint; post-route timing closes.

**Stack:** Yosys → OpenROAD (OpenLane 2 Classic) → Magic / KLayout · PDK: sky130_fd_sc_hd

Design rationale and minute-by-minute pedagogy: [`ASIC_PD_Workshop_Design.md`](ASIC_PD_Workshop_Design.md)

---

## Quickstart (5 minutes)

### Prerequisites

- Docker Desktop (Windows: WSL2 backend; macOS 11+; Linux)
- ~16 GB RAM minimum (32 GB recommended)
- **Pull the image before the session** — the workshop assumes no network during the room time

### Launch

```bash
docker compose pull   # or: docker compose build
docker compose run --rm pd-workshop bash
```

Inside the container:

```bash
./run_stage.sh synth
cat reports/fir_naive/synth/synth_stat.rpt
cat reports/fir_naive/synth/report_checks.rpt
```

### Full stage sequence (student path)

```bash
./run_stage.sh synth
./run_stage.sh floorplan
./run_stage.sh place
PL_TARGET_DENSITY=0.85 ./run_stage.sh place --tag high_density   # side experiment
./run_stage.sh place                                             # reset to 0.45
./run_stage.sh cts
./run_stage.sh route
./run_stage.sh sta --spef
python3 scripts/compare_reports.py --design fir_naive
./run_stage.sh sta --spef --path-report
diff design/fir_naive.v design/fir_pipelined.v
./run_stage.sh all --design fir_pipelined
./run_stage.sh signoff --design fir_pipelined
```

GUI (host display / WSLg / XQuartz):

```bash
openroad_gui reports/fir_naive/place/design.odb
klayout reports/fir_naive/route/design.gds
```

---

## Version pins

| Component | Pin |
|-----------|-----|
| Base image | `ghcr.io/efabless/openlane2:2.3.10` |
| Workshop image | `ghcr.io/orangeafk/rtl2gdsii-fir-workshop:2026.1` |
| PDK | sky130A / `sky130_fd_sc_hd` (baked via volare/ciel) |
| Clock period | see `design/constraints_*.sdc` — **must be calibrated** per image (facilitator guide) |

---

## Repository layout

```
design/     RTL, SDC, testbench
config/     OpenLane 2 JSON configs
scripts/    stage runners + compare_reports.py
reports/    runtime outputs (gitignored) + golden/
docs/       facilitator + student prep
slides/     workshop slide outline
```

---

## Docs

- [Student prep](docs/student_prep.md) — what to know before day-of
- [Facilitator guide](docs/facilitator_guide.md) — calibration checklist + room cues
- [Slides outline](slides/workshop.md)

## RTL smoke test (optional, host)

```bash
# naive
iverilog -g2012 -o sim_naive design/fir_naive.v design/tb_fir.v && vvp sim_naive
# pipelined
iverilog -g2012 -DDUT_PIPELINED -o sim_pipe design/fir_pipelined.v design/tb_fir.v && vvp sim_pipe
```

## License

Apache-2.0 — see [LICENSE](LICENSE)
