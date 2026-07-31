#!/usr/bin/env bash
# Lightweight RTL smoke test (host or container with iverilog).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== fir_naive =="
iverilog -g2012 -o /tmp/sim_naive design/fir_naive.v design/tb_fir.v
vvp /tmp/sim_naive

echo "== fir_pipelined =="
iverilog -g2012 -DDUT_PIPELINED -o /tmp/sim_pipe design/fir_pipelined.v design/tb_fir.v
vvp /tmp/sim_pipe
