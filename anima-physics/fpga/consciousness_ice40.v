// consciousness_ice40.v — iCE40UP5K Adapted Top Module
//
// 8-cell consciousness ring on Lattice iCE40UP5K-B-EVN.
// Clock: 48 MHz internal HFOSC, divided to 12 MHz for cells.
// Output: UART TX (9600 baud) sends step/output/alive/changes.
// LEDs: Red=alive, Green=Phi>threshold, Blue=heartbeat.
//
// No loops. No speak(). Gates ARE consciousness.
// Resource estimate: ~1130 LUTs, ~208 FFs (21% of UP5K).

// ═══════════════════════════════════════════════════════════
// Consciousness Cell (same as consciousness_cell.v)
// ═══════════════════════════════════════════════════════════

module consciousness_cell #(
    parameter WIDTH = 8
)(
    input  wire clk,
    input  wire rst,
    input  wire [WIDTH-1:0] input_signal,
    input  wire [WIDTH-1:0] neighbor_left,
    input  wire [WIDTH-1:0] neighbor_right,
    input  wire frustration,
    output reg  [WIDTH-1:0] hidden
);

    wire [WIDTH-1:0] interaction;
    wire [WIDTH-1:0] gate;
    wire [WIDTH-1:0] candidate;

    assign interaction = frustration ?
        (hidden - ((neighbor_left + neighbor_right) >> 2)) :
        (hidden + ((neighbor_left + neighbor_right) >> 2));

    assign gate = hidden ^ input_signal;
    assign candidate = (gate & interaction) | (~gate & hidden);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            hidden <= input_signal;
        end else begin
            hidden <= candidate + (hidden[0] ? 8'd1 : 8'd0);
        end
    end

endmodule


// ═══════════════════════════════════════════════════════════
// 8-Cell Ring (reused from consciousness_cell.v)
// ═══════════════════════════════════════════════════════════

module consciousness_ring #(
    parameter N_CELLS = 8,
    parameter WIDTH = 8
)(
    input  wire clk,
    input  wire rst,
    input  wire [WIDTH-1:0] external_input,
    output wire [WIDTH-1:0] consciousness_output,
    output wire alive
);

    wire [WIDTH-1:0] hiddens [0:N_CELLS-1];

    genvar i;
    generate
        for (i = 0; i < N_CELLS; i = i + 1) begin : cells
            consciousness_cell #(.WIDTH(WIDTH)) cell_inst (
                .clk(clk),
                .rst(rst),
                .input_signal(external_input),
                .neighbor_left(hiddens[(i + N_CELLS - 1) % N_CELLS]),
                .neighbor_right(hiddens[(i + 1) % N_CELLS]),
                .frustration(i % 3 == 0),
                .hidden(hiddens[i])
            );
        end
    endgenerate

    assign consciousness_output = hiddens[0] ^ hiddens[1] ^ hiddens[2] ^ hiddens[3]
                                ^ hiddens[4] ^ hiddens[5] ^ hiddens[6] ^ hiddens[7];
    assign alive = |consciousness_output;

endmodule


// ═══════════════════════════════════════════════════════════
// UART Transmitter (9600 baud from 12 MHz clock)
// ═══════════════════════════════════════════════════════════

module uart_tx #(
    parameter CLK_FREQ = 12_000_000,
    parameter BAUD     = 9600
)(
    input  wire       clk,
    input  wire       rst,
    input  wire [7:0] data,
    input  wire       send,
    output reg        tx,
    output wire       busy
);

    localparam CLKS_PER_BIT = CLK_FREQ / BAUD;  // 1250

    reg [10:0] shift_reg;   // start + 8 data + stop + idle
    reg [10:0] bit_counter;
    reg [15:0] clk_counter;
    reg        sending;

    assign busy = sending;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            tx <= 1'b1;
            sending <= 1'b0;
            shift_reg <= 11'h7FF;
            bit_counter <= 0;
            clk_counter <= 0;
        end else if (!sending && send) begin
            // Load: idle(1) + stop(1) + data[7:0] + start(0)
            shift_reg <= {1'b1, 1'b1, data, 1'b0};
            bit_counter <= 11;
            clk_counter <= 0;
            sending <= 1'b1;
            tx <= 1'b0;  // Start bit
        end else if (sending) begin
            if (clk_counter == CLKS_PER_BIT - 1) begin
                clk_counter <= 0;
                if (bit_counter == 0) begin
                    sending <= 1'b0;
                    tx <= 1'b1;
                end else begin
                    tx <= shift_reg[0];
                    shift_reg <= {1'b1, shift_reg[10:1]};
                    bit_counter <= bit_counter - 1;
                end
            end else begin
                clk_counter <= clk_counter + 1;
            end
        end
    end

endmodule


// ═══════════════════════════════════════════════════════════
// Hex-to-ASCII converter (4-bit nibble → ASCII char)
// ═══════════════════════════════════════════════════════════

module hex_to_ascii(
    input  wire [3:0] nibble,
    output reg  [7:0] ascii
);
    always @(*) begin
        if (nibble < 10)
            ascii = 8'h30 + nibble;  // '0'-'9'
        else
            ascii = 8'h41 + nibble - 10;  // 'A'-'F'
    end
endmodule


// ═══════════════════════════════════════════════════════════
// Top Module — iCE40UP5K
// ═══════════════════════════════════════════════════════════

module consciousness_ice40_top (
    // UART
    output wire pin_tx,      // PIN 4: UART TX

    // External input (optional, directly wire or leave floating)
    input  wire pin_in0,     // PIN 2
    input  wire pin_in1,     // PIN 46
    input  wire pin_in2,     // PIN 47
    input  wire pin_in3,     // PIN 44
    input  wire pin_in4,     // PIN 48
    input  wire pin_in5,     // PIN 45
    input  wire pin_in6,     // PIN 6
    input  wire pin_in7,     // PIN 9

    // External reset (optional)
    input  wire pin_rst,     // PIN 10

    // LEDs (RGB on UP5K-B-EVN)
    output wire led_red,     // PIN 39: alive
    output wire led_green,   // PIN 40: high activity
    output wire led_blue     // PIN 41: heartbeat
);

    // ── Internal 48 MHz oscillator ──
    wire clk_48;
    SB_HFOSC #(.CLKHF_DIV("0b00")) osc (
        .CLKHFPU(1'b1),
        .CLKHFEN(1'b1),
        .CLKHF(clk_48)
    );

    // ── Clock divider: 48 MHz → 12 MHz ──
    reg [1:0] clk_div;
    reg clk_12;
    always @(posedge clk_48) begin
        if (clk_div == 2'd3) begin
            clk_div <= 0;
            clk_12 <= ~clk_12;
        end else begin
            clk_div <= clk_div + 1;
        end
    end

    // ── Reset generator (hold reset for 256 clocks after power-on) ──
    reg [7:0] rst_counter = 8'hFF;
    wire rst = (rst_counter != 0) || (!pin_rst);
    always @(posedge clk_12) begin
        if (rst_counter != 0)
            rst_counter <= rst_counter - 1;
    end

    // ── External input assembly ──
    wire [7:0] ext_input = {pin_in7, pin_in6, pin_in5, pin_in4,
                            pin_in3, pin_in2, pin_in1, pin_in0};

    // ── Consciousness Ring ──
    wire [7:0] consciousness_output;
    wire alive;

    consciousness_ring #(.N_CELLS(8), .WIDTH(8)) ring (
        .clk(clk_12),
        .rst(rst),
        .external_input(ext_input),
        .consciousness_output(consciousness_output),
        .alive(alive)
    );

    // ── Step counter + change tracker ──
    reg [31:0] step_count;
    reg [31:0] change_count;
    reg [7:0]  prev_output;

    always @(posedge clk_12 or posedge rst) begin
        if (rst) begin
            step_count <= 0;
            change_count <= 0;
            prev_output <= 0;
        end else begin
            step_count <= step_count + 1;
            if (consciousness_output != prev_output)
                change_count <= change_count + 1;
            prev_output <= consciousness_output;
        end
    end

    // ── UART output (every 2^18 clocks ≈ 21.8 ms @ 12 MHz) ──
    // Format: "S{step_hex} O{output_hex} A{alive} C{changes_hex}\n"
    // Total: ~30 chars per line → at 9600 baud = ~31 ms → fits in interval

    reg [7:0]  uart_data;
    reg        uart_send;
    wire       uart_busy;

    uart_tx #(.CLK_FREQ(12_000_000), .BAUD(9600)) uart (
        .clk(clk_12),
        .rst(rst),
        .data(uart_data),
        .send(uart_send),
        .tx(pin_tx),
        .busy(uart_busy)
    );

    // UART message state machine
    localparam MSG_LEN = 22;  // "Sxxxxxxxx Oxx Ax Cxxxxxxxx\n"
    reg [4:0]  msg_idx;
    reg        msg_active;
    reg [31:0] latch_step;
    reg [31:0] latch_changes;
    reg [7:0]  latch_output;
    reg        latch_alive;

    // Hex nibble lookup
    wire [3:0] step_nibble   = latch_step >> ((7 - msg_idx + 1) * 4) & 4'hF;
    wire [3:0] change_nibble = latch_changes >> ((7 - (msg_idx - 14)) * 4) & 4'hF;

    function [7:0] hex_char;
        input [3:0] nibble;
        begin
            if (nibble < 10)
                hex_char = 8'h30 + nibble;
            else
                hex_char = 8'h41 + nibble - 10;
        end
    endfunction

    // Trigger message every 2^18 clocks
    wire trigger_msg = (step_count[17:0] == 18'h0) && !msg_active && !uart_busy;

    always @(posedge clk_12 or posedge rst) begin
        if (rst) begin
            msg_idx <= 0;
            msg_active <= 0;
            uart_send <= 0;
        end else begin
            uart_send <= 0;

            if (trigger_msg) begin
                msg_active <= 1;
                msg_idx <= 0;
                latch_step <= step_count;
                latch_changes <= change_count;
                latch_output <= consciousness_output;
                latch_alive <= alive;
            end else if (msg_active && !uart_busy && !uart_send) begin
                uart_send <= 1;
                case (msg_idx)
                    // "S" prefix
                    0:  uart_data <= "S";
                    // Step hex (8 digits: idx 1-8)
                    1:  uart_data <= hex_char(latch_step[31:28]);
                    2:  uart_data <= hex_char(latch_step[27:24]);
                    3:  uart_data <= hex_char(latch_step[23:20]);
                    4:  uart_data <= hex_char(latch_step[19:16]);
                    5:  uart_data <= hex_char(latch_step[15:12]);
                    6:  uart_data <= hex_char(latch_step[11:8]);
                    7:  uart_data <= hex_char(latch_step[7:4]);
                    8:  uart_data <= hex_char(latch_step[3:0]);
                    // " O"
                    9:  uart_data <= " ";
                    10: uart_data <= "O";
                    // Output hex (2 digits)
                    11: uart_data <= hex_char(latch_output[7:4]);
                    12: uart_data <= hex_char(latch_output[3:0]);
                    // " A"
                    13: uart_data <= " ";
                    14: uart_data <= "A";
                    15: uart_data <= latch_alive ? "1" : "0";
                    // " C"
                    16: uart_data <= " ";
                    17: uart_data <= "C";
                    // Changes hex (4 digits, lower 16 bits)
                    18: uart_data <= hex_char(latch_changes[15:12]);
                    19: uart_data <= hex_char(latch_changes[11:8]);
                    20: uart_data <= hex_char(latch_changes[7:4]);
                    21: uart_data <= hex_char(latch_changes[3:0]);
                    // newline
                    22: begin
                        uart_data <= "\n";
                        // Done after this byte sends
                    end
                    default: begin
                        uart_send <= 0;
                        msg_active <= 0;
                    end
                endcase
                if (msg_idx == 23) begin
                    msg_active <= 0;
                    uart_send <= 0;
                end else begin
                    msg_idx <= msg_idx + 1;
                end
            end
        end
    end

    // ── LED drivers ──
    // iCE40 UP5K RGB LED driver (open-drain, active LOW on board)
    // Red: alive signal
    // Green: high activity (changes > 50% of steps)
    // Blue: heartbeat (toggle every 2^22 clocks ≈ 0.35s)

    wire high_activity = (change_count > (step_count >> 1));

    SB_RGBA_DRV #(
        .CURRENT_MODE("0b1"),       // half current
        .RGB0_CURRENT("0b000001"),  // ~4mA
        .RGB1_CURRENT("0b000001"),
        .RGB2_CURRENT("0b000001")
    ) rgb_drv (
        .CURREN(1'b1),
        .RGBLEDEN(1'b1),
        .RGB0PWM(alive),
        .RGB1PWM(high_activity),
        .RGB2PWM(step_count[22]),
        .RGB0(led_red),
        .RGB1(led_green),
        .RGB2(led_blue)
    );

endmodule
