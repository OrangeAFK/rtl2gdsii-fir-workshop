#!/usr/bin/env bash
# Single entrypoint for every workshop stage.
# Intended to run inside the workshop container (Linux).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ $# -lt 1 ]]; then
  cat <<'EOF'
Usage: ./run_stage.sh <stage> [options]

Stages:
  synth       Yosys synthesis + pre-PnR STA
  floorplan   Floorplan
  place       Global + detailed placement
  cts         Clock tree synthesis
  route       Detailed routing
  sta         Timing reports (--spef / --path-report)
  signoff     GDS stream-out + DRC + LVS
  all         Full flow through signoff

Options:
  --design NAME     fir_naive (default) | fir_pipelined
  --tag NAME        e.g. high_density for the utilization side experiment
  --spef            (sta) use post-route SPEF parasitics
  --path-report     (sta) write worst_path.rpt
  --with-drc-lvs    accepted for signoff/all compatibility

Environment:
  DESIGN              same as --design
  PL_TARGET_DENSITY   if set to 0.85, selects high-density config for fir_naive place
EOF
  exit 1
fi

STAGE="$1"
shift || true

DESIGN="${DESIGN:-fir_naive}"
TAG=""
STA_ARGS=()
EXTRA=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --design)
      DESIGN="$2"
      shift 2
      ;;
    --tag)
      TAG="$2"
      shift 2
      ;;
    --spef|--path-report|--with-drc-lvs)
      if [[ "$STAGE" == "sta" ]]; then
        STA_ARGS+=("$1")
      else
        EXTRA+=("$1")
      fi
      shift
      ;;
    *)
      EXTRA+=("$1")
      shift
      ;;
  esac
done

# Side experiment: PL_TARGET_DENSITY=0.85 ./run_stage.sh place --tag high_density
if [[ -n "${PL_TARGET_DENSITY:-}" ]]; then
  density="$PL_TARGET_DENSITY"
  if awk "BEGIN {exit !($density >= 0.8)}"; then
    TAG="${TAG:-high_density}"
  fi
fi

export DESIGN

case "$STAGE" in
  synth|floorplan|place|cts|route|signoff|all)
    args=(--design "$DESIGN" --stage "$STAGE")
    if [[ -n "$TAG" ]]; then
      args+=(--tag "$TAG")
    fi
    args+=("${EXTRA[@]}")
    python3 "$ROOT/scripts/stages/run_step.py" "${args[@]}"
    ;;
  sta)
    args=(--design "$DESIGN" "${STA_ARGS[@]}" "${EXTRA[@]}")
    python3 "$ROOT/scripts/stages/run_sta.py" "${args[@]}"
    ;;
  *)
    echo "unknown stage: $STAGE" >&2
    exit 1
    ;;
esac
