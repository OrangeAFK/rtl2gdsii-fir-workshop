# constraints_a.sdc — Implementation A (fir_naive)
#
# CALIBRATE: binary-search this period on the pinned workshop image until
#   - synth-stage STA WNS is small and positive (~0.1–0.5 ns)
#   - post-route STA (with SPEF) WNS is clearly negative
# See docs/facilitator_guide.md § Calibration Checklist.
#
# Initial guess only — replace after calibration and keep A/B identical.
set clk_period 10.0

create_clock -name clk -period $clk_period [get_ports clk]
set_input_delay  -clock clk 1.0 [get_ports x_in]
set_input_delay  -clock clk 0.5 [get_ports sample_valid]
set_input_delay  -clock clk 0.5 [get_ports rst_n]
set_output_delay -clock clk 1.0 [get_ports y_out]
set_output_delay -clock clk 0.5 [get_ports y_valid]
