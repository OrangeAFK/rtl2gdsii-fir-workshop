// Implementation B — same FIR as fir_naive, with one pipeline register that
// splits the 8-term ripple chain into two 4-term partial sums.
// Same I/O and coefficients; one extra cycle of latency, same steady-state
// throughput once the pipeline is full.
module fir_pipelined #(
    parameter N_TAPS = 8,
    parameter DATA_W = 8,
    parameter COEF_W = 8
)(
    input  wire                            clk,
    input  wire                            rst_n,
    input  wire                            sample_valid,
    input  wire signed [DATA_W-1:0]         x_in,
    output reg  signed [DATA_W+COEF_W+3:0]  y_out,
    output reg                             y_valid
);
    localparam signed [COEF_W-1:0] COEF0 = 8'sd2;
    localparam signed [COEF_W-1:0] COEF1 = 8'sd4;
    localparam signed [COEF_W-1:0] COEF2 = 8'sd8;
    localparam signed [COEF_W-1:0] COEF3 = 8'sd16;
    localparam signed [COEF_W-1:0] COEF4 = 8'sd16;
    localparam signed [COEF_W-1:0] COEF5 = 8'sd8;
    localparam signed [COEF_W-1:0] COEF6 = 8'sd4;
    localparam signed [COEF_W-1:0] COEF7 = 8'sd2;

    reg signed [DATA_W-1:0] shift_reg [0:N_TAPS-1];
    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < N_TAPS; i = i + 1)
                shift_reg[i] <= {DATA_W{1'b0}};
        end else if (sample_valid) begin
            shift_reg[0] <= x_in;
            for (i = 1; i < N_TAPS; i = i + 1)
                shift_reg[i] <= shift_reg[i-1];
        end
    end

    wire signed [DATA_W-1:0] t0 = sample_valid ? x_in         : shift_reg[0];
    wire signed [DATA_W-1:0] t1 = sample_valid ? shift_reg[0] : shift_reg[1];
    wire signed [DATA_W-1:0] t2 = sample_valid ? shift_reg[1] : shift_reg[2];
    wire signed [DATA_W-1:0] t3 = sample_valid ? shift_reg[2] : shift_reg[3];
    wire signed [DATA_W-1:0] t4 = sample_valid ? shift_reg[3] : shift_reg[4];
    wire signed [DATA_W-1:0] t5 = sample_valid ? shift_reg[4] : shift_reg[5];
    wire signed [DATA_W-1:0] t6 = sample_valid ? shift_reg[5] : shift_reg[6];
    wire signed [DATA_W-1:0] t7 = sample_valid ? shift_reg[6] : shift_reg[7];

    wire signed [DATA_W+COEF_W+3:0] p0 = t0 * COEF0;
    wire signed [DATA_W+COEF_W+3:0] p1 = t1 * COEF1;
    wire signed [DATA_W+COEF_W+3:0] p2 = t2 * COEF2;
    wire signed [DATA_W+COEF_W+3:0] p3 = t3 * COEF3;
    wire signed [DATA_W+COEF_W+3:0] p4 = t4 * COEF4;
    wire signed [DATA_W+COEF_W+3:0] p5 = t5 * COEF5;
    wire signed [DATA_W+COEF_W+3:0] p6 = t6 * COEF6;
    wire signed [DATA_W+COEF_W+3:0] p7 = t7 * COEF7;

    wire signed [DATA_W+COEF_W+2:0] sum_lo = p0 + p1 + p2 + p3;
    wire signed [DATA_W+COEF_W+2:0] sum_hi = p4 + p5 + p6 + p7;

    reg signed [DATA_W+COEF_W+2:0] sum_lo_reg, sum_hi_reg;
    reg                           pipe_valid;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sum_lo_reg <= {(DATA_W+COEF_W+3){1'b0}};
            sum_hi_reg <= {(DATA_W+COEF_W+3){1'b0}};
            pipe_valid <= 1'b0;
        end else begin
            sum_lo_reg <= sum_lo;
            sum_hi_reg <= sum_hi;
            pipe_valid <= sample_valid;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            y_out   <= {(DATA_W+COEF_W+4){1'b0}};
            y_valid <= 1'b0;
        end else begin
            y_out   <= sum_lo_reg + sum_hi_reg;
            y_valid <= pipe_valid;
        end
    end
endmodule
