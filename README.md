# RTL → GDSII FIR Workshop (IEEE SSCS)

Hands-on ASIC physical design on sky130: take an 8-tap FIR from RTL to GDSII.
The naive ripple-chain version looks fine after synthesis, then fails timing
after routing once real wire parasitics show up. The pipelined version adds one
register and closes at the same clock.

Needs Docker Desktop, bash (WSL on Windows), and about 16 GB RAM.

## Setup

```bash
docker compose build
docker compose run --rm pd-workshop bash
```

All stage commands below run **inside** that container shell.

## Workshop steps

### 0. Sanity

```bash
docker compose ps
```

### 1. Synthesis

```bash
./run_stage.sh synth
cat reports/fir_naive/synth/synth_stat.rpt
cat reports/fir_naive/synth/report_checks.rpt
```

### 2. Floorplan + place

```bash
./run_stage.sh floorplan
./run_stage.sh place
openroad_gui reports/fir_naive/place/design.odb
```

### 3. Utilization experiment

```bash
PL_TARGET_DENSITY=0.85 ./run_stage.sh place --tag high_density
openroad_gui reports/fir_naive/place/high_density/design.odb
./run_stage.sh place
```

### 4. CTS

```bash
./run_stage.sh cts
openroad_gui reports/fir_naive/cts/design.odb
```

### 5. Route

```bash
./run_stage.sh route
klayout reports/fir_naive/route/design.gds
```

### 6. Post-route STA

```bash
./run_stage.sh sta --spef
cat reports/fir_naive/sta/report_checks.rpt
python3 scripts/compare_reports.py --design fir_naive
```

### 7. Worst path

```bash
./run_stage.sh sta --spef --path-report
cat reports/fir_naive/sta/worst_path.rpt
```

### 8. Pipelined fix

```bash
diff design/fir_naive.v design/fir_pipelined.v
./run_stage.sh all --design fir_pipelined
cat reports/fir_pipelined/sta/report_checks.rpt
```

### 9. Signoff

```bash
./run_stage.sh signoff --design fir_pipelined
cat reports/fir_pipelined/signoff/drc.rpt
cat reports/fir_pipelined/signoff/lvs.rpt
klayout reports/fir_pipelined/signoff/design.gds
```

## Before teaching

Binary-search `clk_period` in `design/constraints_a.sdc` and `constraints_b.sdc`
(and `CLOCK_PERIOD` in the configs) until naive passes synth STA and fails
post-route STA, and pipelined passes post-route at the same period.
