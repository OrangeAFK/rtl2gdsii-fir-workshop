# Calibration record

Status: **PLACEHOLDER — not yet run on the pinned workshop image**

| Field | Value |
|-------|-------|
| Workshop image | `ghcr.io/orangeafk/rtl2gdsii-fir-workshop:2026.1` |
| Image digest | _TBD_ |
| OpenLane base tag | `2.3.10` |
| PDK / SCL | sky130A / sky130_fd_sc_hd |
| Clock period (ns) | `10.0` (initial guess in SDC/configs) |
| A synth WNS | _TBD_ (target: small positive) |
| A post-route WNS | _TBD_ (target: clearly negative) |
| B post-route WNS | _TBD_ (target: positive) |

After calibration, copy text reports under:

- `fir_naive/synth/`
- `fir_naive/sta/`
- `fir_pipelined/sta/`
- `fir_pipelined/signoff/`

See `docs/facilitator_guide.md`.
