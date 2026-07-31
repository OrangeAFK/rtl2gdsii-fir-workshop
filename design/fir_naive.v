// Implementation A — naive direct-form 8-tap FIR with a ripple-chain sum.
// The long combinational MAC chain is intentional: synthesis-stage STA can
// look fine while post-route STA with extracted parasitics fails.
module fir_naive #(
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
    // Fixed linear-phase coeffs {2,4,8,16,16,8,4,2}
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

    // Taps as seen by the MAC this cycle (include the incoming sample).
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

    // Naive ripple-chain sum — critical path grows with N_TAPS.
    wire signed [DATA_W+COEF_W+3:0] chain_sum =
        p0 + p1 + p2 + p3 + p4 + p5 + p6 + p7;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            y_out   <= {(DATA_W+COEF_W+4){1'b0}};
            y_valid <= 1'b0;
        end else begin
            y_out   <= chain_sum;
            y_valid <= sample_valid;
        end
    end
endmodule
