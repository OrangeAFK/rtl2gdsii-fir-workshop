# constraints_b.sdc — Implementation B (fir_pipelined)
#
# Same clock period as constraints_a.sdc — the point is that the SAME
# constraint now passes because the RTL changed, not the clock.
set clk_period 10.0

create_clock -name clk -period $clk_period [get_ports clk]
set_input_delay  -clock clk 1.0 [get_ports x_in]
set_input_delay  -clock clk 0.5 [get_ports sample_valid]
set_input_delay  -clock clk 0.5 [get_ports rst_n]
set_output_delay -clock clk 1.0 [get_ports y_out]
set_output_delay -clock clk 0.5 [get_ports y_valid]
