// Self-checking testbench for fir_naive / fir_pipelined.
// Select DUT with +define+DUT_PIPELINED (default: fir_naive).
//
// Both DUTs register the MAC result, so y_* is one cycle after sample_valid
// for the naive design, and two cycles for the pipelined design.
`timescale 1ns/1ps

module tb_fir;
    localparam DATA_W = 8;
    localparam COEF_W = 8;
    localparam N_TAPS = 8;
    localparam OUT_W  = DATA_W + COEF_W + 4;

// After the capturing posedge, naive y_* reflects this cycle's sample (reg'd).
// Pipelined adds one extra register stage on the sum.
`ifdef DUT_PIPELINED
    localparam integer LATENCY = 1;
`else
    localparam integer LATENCY = 0;
`endif

    reg                         clk;
    reg                         rst_n;
    reg                         sample_valid;
    reg  signed [DATA_W-1:0]    x_in;
    wire signed [OUT_W-1:0]     y_out;
    wire                        y_valid;

    integer errors;
    integer cycles;
    integer i;
    integer k;

    reg signed [DATA_W-1:0] ref_shift [0:N_TAPS-1];
    reg signed [OUT_W-1:0]  expect_y_q [0:3];
    reg                     expect_v_q [0:3];

    function signed [COEF_W-1:0] coef;
        input integer idx;
        begin
            case (idx)
                0: coef = 8'sd2;
                1: coef = 8'sd4;
                2: coef = 8'sd8;
                3: coef = 8'sd16;
                4: coef = 8'sd16;
                5: coef = 8'sd8;
                6: coef = 8'sd4;
                7: coef = 8'sd2;
                default: coef = 8'sd0;
            endcase
        end
    endfunction

    function signed [OUT_W-1:0] fir_sum;
        integer t;
        reg signed [OUT_W-1:0] acc;
        begin
            acc = 0;
            for (t = 0; t < N_TAPS; t = t + 1)
                acc = acc + (ref_shift[t] * coef(t));
            fir_sum = acc;
        end
    endfunction

`ifdef DUT_PIPELINED
    fir_pipelined dut (
`else
    fir_naive dut (
`endif
        .clk(clk),
        .rst_n(rst_n),
        .sample_valid(sample_valid),
        .x_in(x_in),
        .y_out(y_out),
        .y_valid(y_valid)
    );

    initial clk = 1'b0;
    always #5 clk = ~clk;

    task apply_reset;
        begin
            rst_n = 1'b0;
            sample_valid = 1'b0;
            x_in = 0;
            for (i = 0; i < N_TAPS; i = i + 1)
                ref_shift[i] = 0;
            for (i = 0; i < 4; i = i + 1) begin
                expect_y_q[i] = 0;
                expect_v_q[i] = 1'b0;
            end
            repeat (4) @(posedge clk);
            @(negedge clk);
            rst_n = 1'b1;
            @(posedge clk);
        end
    endtask

    task push_expect;
        input signed [OUT_W-1:0] y;
        input v;
        integer q;
        begin
            for (q = 3; q > 0; q = q - 1) begin
                expect_y_q[q] = expect_y_q[q-1];
                expect_v_q[q] = expect_v_q[q-1];
            end
            expect_y_q[0] = y;
            expect_v_q[0] = v;
        end
    endtask

    task drive_and_check;
        input signed [DATA_W-1:0] sample;
        input valid;
        reg signed [OUT_W-1:0] mac;
        reg signed [OUT_W-1:0] exp_y;
        reg exp_v;
        begin
            @(negedge clk);
            x_in = sample;
            sample_valid = valid;

            if (valid) begin
                for (k = N_TAPS-1; k > 0; k = k - 1)
                    ref_shift[k] = ref_shift[k-1];
                ref_shift[0] = sample;
            end
            mac = fir_sum();
            // Registered output path: enqueue expected result with design latency.
            push_expect(mac, valid);

            @(posedge clk);
            #1;

            exp_y = expect_y_q[LATENCY];
            exp_v = expect_v_q[LATENCY];

            if (y_valid !== exp_v || (exp_v && y_out !== exp_y)) begin
                $display("FAIL cycle %0d: y_valid=%b (exp %b) y_out=%0d (exp %0d)",
                         cycles, y_valid, exp_v, y_out, exp_y);
                errors = errors + 1;
            end
            cycles = cycles + 1;
        end
    endtask

    initial begin
        errors = 0;
        cycles = 0;
        apply_reset();

        drive_and_check(8'sd1, 1'b1);
        for (i = 0; i < 10; i = i + 1)
            drive_and_check(8'sd0, 1'b1);

        for (i = 0; i < 12; i = i + 1)
            drive_and_check(8'sd3, 1'b1);

        drive_and_check(8'sd7, 1'b1);
        drive_and_check(8'sd0, 1'b0);
        drive_and_check(-8'sd5, 1'b1);
        drive_and_check(8'sd0, 1'b0);
        drive_and_check(8'sd9, 1'b1);

        for (i = 0; i < 8; i = i + 1)
            drive_and_check(8'sd0, 1'b1);

        // Drain pipeline
        for (i = 0; i < LATENCY + 1; i = i + 1)
            drive_and_check(8'sd0, 1'b0);

        if (errors == 0)
            $display("PASS: tb_fir (%0d cycles checked)", cycles);
        else
            $display("FAIL: %0d errors", errors);

        $finish;
    end
endmodule
