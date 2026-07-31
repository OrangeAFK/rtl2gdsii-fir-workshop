# Student prep

Read this before the workshop (~30–45 minutes).

## What you should already know

- Combinational vs sequential logic; flip-flops and clocks
- Setup time (data must arrive before the capturing edge, minus library setup)
- Basic Verilog: `module`, `always @(posedge clk)`, `wire`/`reg`, parameters
- What synthesis means at a high level (RTL → gates), even if you have not run a PD flow

You do **not** need prior OpenROAD / OpenLane experience.

## What we will build

An **8-tap direct-form FIR filter** (signed 8-bit samples, fixed coefficients).

Two implementations of the same math:

| Impl | Structure | Story role |
|------|-----------|------------|
| A `fir_naive` | Ripple-chain sum of 8 products | Passes early timing checks, fails after routing |
| B `fir_pipelined` | One pipeline register mid-sum | Same clock; closes timing |

Optional: skim [`design/fir_naive.v`](../design/fir_naive.v) and predict whether a ~10 ns clock “should be fine” for 8-bit logic. Keep that prediction — we will revisit it.

## Laptop setup (before you arrive)

1. Install **Docker Desktop**
   - Windows: enable the **WSL2** backend
   - macOS 11+: Docker Desktop; share `/Users` if prompted
2. Clone this repo
3. Pull / build so you are offline-ready:

```bash
docker compose pull || docker compose build
docker compose run --rm pd-workshop ./run_stage.sh synth
```

4. Confirm you can open a shell in the container and see `run_stage.sh`

**Hardware:** 16 GB RAM minimum; 32 GB recommended. If your laptop is slow, the facilitator has golden reports so the narrative continues.

## Vocabulary cheat sheet (will show up in tools)

| Term | One-liner |
|------|-----------|
| Critical path | Longest register-to-register delay; sets max clock |
| Utilization | Fraction of core area filled by standard cells |
| Congestion | Local routing demand > supply |
| CTS | Clock tree synthesis — buffer tree for the clock |
| SPEF | Extracted wire R/C after routing |
| WNS / TNS | Worst / total negative slack |
| DRC / LVS | Geometry rules vs layout↔schematic match |
| GDSII | Layout file sent toward the foundry |

## Optional reading

- Workshop design doc: [`ASIC_PD_Workshop_Design.md`](../ASIC_PD_Workshop_Design.md) §§1–2, §8
- OpenLane newcomers page (skim only): https://openlane2.readthedocs.io/
