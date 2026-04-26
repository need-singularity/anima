// anima-physics/fpga/cmos_8bit_ring_lfsr.sv
// 8-bit Galois LFSR + 8-bit ring counter coupled — Verilator/Icarus testbench.
// raw#9 sibling RTL (emitted via hexa cloud_facade_poc.hexa, frozen seed=0x42).
//
// Galois LFSR polynomial taps = [8,6,5,4]  (x^8 + x^6 + x^5 + x^4 + 1, max-length)
// Ring counter 8-bit feedback = lfsr[0] xor ring[7]   (entropy injection)
// Output bitstream = lfsr_out (bit-0) per cycle for N_CYCLES=1024.
//
// reset_mode (plus-arg):
//   +mode=positive  → de-assert rst after 2 cycles, normal LFSR
//   +mode=negative  → keep rst=1 forever (output stuck at 0)
//
// Output: each clock tick prints `bitline=<0|1>` to stdout.
// Final summary line: `done positive_run=<n>` (debug).

`timescale 1ns/1ps

module top;

    reg clk;
    reg rst;
    reg [7:0] lfsr;
    reg [7:0] ring;
    wire fb;
    wire bit_out;

    // Galois LFSR8 taps [8,6,5,4]: feedback = lfsr[0]
    // shift right; if feedback bit set, xor with poly mask.
    // Taps as bit positions (1-indexed) → mask covering positions [6,5,4,1]
    // For Galois form: when bit 0 is shifted out, XOR mask = 0x2D
    //   bits set at indices (5,3,2,0) → 0b00101101 = 0x2D  (Wikipedia 8-bit max-len 0xB8 reverse)
    // We choose canonical Fibonacci-equivalent Galois mask 0xB8 with feedback=lsb.
    localparam [7:0] POLY_MASK = 8'hB8;

    integer i;
    integer pos_count;
    integer N_CYCLES;
    reg [255:0] mode_str;
    integer is_negative;

    initial begin
        N_CYCLES = 1024;
        pos_count = 0;
        is_negative = 0;
        if ($value$plusargs("mode=%s", mode_str)) begin
            // crude string compare — first two chars
            if (mode_str[15:8] == "n" || mode_str[7:0] == "n") begin
                is_negative = 1;
            end
            // simpler: check if string starts with 'n'
            // mode_str is right-padded, so leading char in low byte after $value$plusargs
        end
        // robust: check argv via $test$plusargs for "mode=negative"
        if ($test$plusargs("mode=negative")) is_negative = 1;

        // init state — frozen seed
        lfsr = 8'h42;
        ring = 8'hA5;
        clk = 0;
        rst = 1;

        // hold reset for 2 cycles
        #1; clk = 1; #1; clk = 0;
        #1; clk = 1; #1; clk = 0;

        if (is_negative == 0) begin
            rst = 0;
        end
        // negative path: rst stays 1 forever → lfsr/ring stuck at reset value; bit_out = 0

        for (i = 0; i < N_CYCLES; i = i + 1) begin
            #1; clk = 1; #1; clk = 0;
            $display("bitline=%0d", bit_out);
            if (bit_out == 1) pos_count = pos_count + 1;
        end
        $display("done positive_run=%0d mode_negative=%0d", pos_count, is_negative);
        $finish;
    end

    // bit_out = LSB of lfsr xor LSB of ring  → coupled
    assign bit_out = (rst == 1) ? 1'b0 : (lfsr[0] ^ ring[0]);

    always @(posedge clk) begin
        if (rst) begin
            lfsr <= 8'h42;
            ring <= 8'hA5;
        end else begin
            // Galois LFSR step: shift right, XOR mask if bit-0 == 1
            if (lfsr[0]) begin
                lfsr <= (lfsr >> 1) ^ POLY_MASK;
            end else begin
                lfsr <= (lfsr >> 1);
            end
            // Ring counter rotate-left, with feedback from lfsr[0]
            ring <= {ring[6:0], ring[7] ^ lfsr[0]};
        end
    end

endmodule
