# Golden reports

Pre-calibrated reference outputs for the workshop narrative.

## Expected contents (after facilitator calibration)

```
fir_naive/
  synth/report_checks.rpt      # small positive WNS
  synth/synth_stat.rpt
  sta/report_checks.rpt        # clearly negative WNS (SPEF)
  sta/worst_path.rpt
fir_pipelined/
  sta/report_checks.rpt        # positive WNS post-route
  signoff/drc.rpt
  signoff/lvs.rpt
CALIBRATION.md                 # recorded period, image digest, WNS numbers
```

Large `.odb` / `.gds` binaries are **not** stored here — keep them as release assets or a local cache volume.

## Status

`PLACEHOLDER` — run the calibration checklist in `docs/facilitator_guide.md` on the pinned workshop image, then copy text reports into this tree and commit.
