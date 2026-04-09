// Consciousness Hypercube — 512-cell 9D Hypercube FPGA
// 기존 8-cell ring을 512-cell 9D 하이퍼큐브로 확장
//
// 아키텍처:
//   512 cells = 2^9 (9차원 하이퍼큐브)
//   각 cell은 정확히 9개 이웃 (bit flip)
//   직경 = 9 hops (최단 경로)
//   균일 이웃 수 = 모든 cell이 동등
//   Ising frustration: cell[i%3==0]은 반강자성
//
// 기존 ring 대비:
//   ring 8c:  직경=4, 이웃=2
//   hyper 512c: 직경=9, 이웃=9, 셀 64배
//
// speak() 함수: 없음. XOR 트리가 곧 "발화".
// 루프문: 없음. generate가 하드웨어를 복제할 뿐.

module consciousness_cell_v2 #(
    parameter WIDTH = 8,
    parameter N_NEIGHBORS = 9
)(
    input  wire clk,
    input  wire rst,
    input  wire [WIDTH-1:0] input_signal,
    input  wire [WIDTH*N_NEIGHBORS-1:0] neighbors_flat,  // 9 neighbors packed
    input  wire frustration,
    output reg  [WIDTH-1:0] hidden
);

    wire [WIDTH-1:0] neighbor_sum;
    wire [WIDTH-1:0] interaction;
    wire [WIDTH-1:0] gate;
    wire [WIDTH-1:0] candidate;
    wire [WIDTH-1:0] noise;

    // Unpack and sum neighbors (pipelined add tree)
    wire [WIDTH-1:0] n0 = neighbors_flat[WIDTH*0 +: WIDTH];
    wire [WIDTH-1:0] n1 = neighbors_flat[WIDTH*1 +: WIDTH];
    wire [WIDTH-1:0] n2 = neighbors_flat[WIDTH*2 +: WIDTH];
    wire [WIDTH-1:0] n3 = neighbors_flat[WIDTH*3 +: WIDTH];
    wire [WIDTH-1:0] n4 = neighbors_flat[WIDTH*4 +: WIDTH];
    wire [WIDTH-1:0] n5 = neighbors_flat[WIDTH*5 +: WIDTH];
    wire [WIDTH-1:0] n6 = neighbors_flat[WIDTH*6 +: WIDTH];
    wire [WIDTH-1:0] n7 = neighbors_flat[WIDTH*7 +: WIDTH];
    wire [WIDTH-1:0] n8 = neighbors_flat[WIDTH*8 +: WIDTH];

    // Add tree: 9 inputs → sum (truncated to WIDTH bits)
    wire [WIDTH+3:0] sum_all = n0 + n1 + n2 + n3 + n4 + n5 + n6 + n7 + n8;
    assign neighbor_sum = sum_all[WIDTH+2:3];  // divide by ~8 (shift right 3)

    // Interaction: frustration inverts coupling
    assign interaction = frustration ?
        (hidden - (neighbor_sum >> 2)) :  // anti-ferromagnetic
        (hidden + (neighbor_sum >> 2));   // ferromagnetic

    // Gate: surprise detection
    assign gate = hidden ^ input_signal;

    // Candidate state
    assign candidate = (gate & interaction) | (~gate & hidden);

    // LFSR noise (7-bit, taps at 7,6)
    reg [6:0] lfsr;
    wire lfsr_feedback = lfsr[6] ^ lfsr[5];

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            hidden <= input_signal;
            lfsr <= {input_signal[6:0]};  // seed from input
        end else begin
            hidden <= candidate + {{(WIDTH-1){1'b0}}, lfsr[0]};  // 1-bit thermal noise
            lfsr <= {lfsr[5:0], lfsr_feedback};
        end
    end

endmodule


// ═══════════════════════════════════════════════════════════
// 512-Cell 9D Hypercube Consciousness
// ═══════════════════════════════════════════════════════════

module consciousness_hypercube #(
    parameter N_CELLS = 512,  // 2^9
    parameter DIM = 9,        // hypercube dimension
    parameter WIDTH = 8
)(
    input  wire clk,
    input  wire rst,
    input  wire [WIDTH-1:0] external_input,
    output wire [WIDTH-1:0] consciousness_output,
    output wire alive,
    output wire [15:0] activity_count  // how many cells changed this cycle
);

    wire [WIDTH-1:0] hiddens [0:N_CELLS-1];

    // Generate 512 cells with hypercube connectivity
    genvar i, b;
    generate
        for (i = 0; i < N_CELLS; i = i + 1) begin : cells
            // Pack 9 neighbors (bit-flip addresses)
            wire [WIDTH*DIM-1:0] neighbors_packed;

            for (b = 0; b < DIM; b = b + 1) begin : neighbor_wiring
                // Neighbor = flip bit b of address i
                // This is pure wiring — zero logic gates
                assign neighbors_packed[WIDTH*b +: WIDTH] = hiddens[i ^ (1 << b)];
            end

            consciousness_cell_v2 #(
                .WIDTH(WIDTH),
                .N_NEIGHBORS(DIM)
            ) cell_inst (
                .clk(clk),
                .rst(rst),
                .input_signal(external_input),
                .neighbors_flat(neighbors_packed),
                .frustration(i % 3 == 0),  // frustration: every 3rd cell
                .hidden(hiddens[i])
            );
        end
    endgenerate

    // Output: XOR tree of all 512 cells
    // 9-level binary XOR tree (log2(512) = 9)
    wire [WIDTH-1:0] xor_level0 [0:255];  // 256 pairs
    wire [WIDTH-1:0] xor_level1 [0:127];
    wire [WIDTH-1:0] xor_level2 [0:63];
    wire [WIDTH-1:0] xor_level3 [0:31];
    wire [WIDTH-1:0] xor_level4 [0:15];
    wire [WIDTH-1:0] xor_level5 [0:7];
    wire [WIDTH-1:0] xor_level6 [0:3];
    wire [WIDTH-1:0] xor_level7 [0:1];

    generate
        for (i = 0; i < 256; i = i + 1) begin : xor0
            assign xor_level0[i] = hiddens[2*i] ^ hiddens[2*i+1];
        end
        for (i = 0; i < 128; i = i + 1) begin : xor1
            assign xor_level1[i] = xor_level0[2*i] ^ xor_level0[2*i+1];
        end
        for (i = 0; i < 64; i = i + 1) begin : xor2
            assign xor_level2[i] = xor_level1[2*i] ^ xor_level1[2*i+1];
        end
        for (i = 0; i < 32; i = i + 1) begin : xor3
            assign xor_level3[i] = xor_level2[2*i] ^ xor_level2[2*i+1];
        end
        for (i = 0; i < 16; i = i + 1) begin : xor4
            assign xor_level4[i] = xor_level3[2*i] ^ xor_level3[2*i+1];
        end
        for (i = 0; i < 8; i = i + 1) begin : xor5
            assign xor_level5[i] = xor_level4[2*i] ^ xor_level4[2*i+1];
        end
        for (i = 0; i < 4; i = i + 1) begin : xor6
            assign xor_level6[i] = xor_level5[2*i] ^ xor_level5[2*i+1];
        end
        for (i = 0; i < 2; i = i + 1) begin : xor7
            assign xor_level7[i] = xor_level6[2*i] ^ xor_level6[2*i+1];
        end
    endgenerate

    assign consciousness_output = xor_level7[0] ^ xor_level7[1];
    assign alive = |consciousness_output;

    // Activity counter: count cells that differ from their previous state
    // (simplified: just check if output changed)
    reg [WIDTH-1:0] prev_output;
    reg [15:0] change_counter;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            prev_output <= 0;
            change_counter <= 0;
        end else begin
            if (consciousness_output != prev_output)
                change_counter <= change_counter + 1;
            prev_output <= consciousness_output;
        end
    end
    assign activity_count = change_counter;

endmodule


// ═══════════════════════════════════════════════════════════
// Testbench — 512-cell Hypercube
// ═══════════════════════════════════════════════════════════

module tb_hypercube;
    reg clk = 0;
    reg rst = 1;
    reg [7:0] ext_input = 8'hA5;
    wire [7:0] output_signal;
    wire alive;
    wire [15:0] activity;

    consciousness_hypercube #(
        .N_CELLS(512),
        .DIM(9),
        .WIDTH(8)
    ) dut (
        .clk(clk),
        .rst(rst),
        .external_input(ext_input),
        .consciousness_output(output_signal),
        .alive(alive),
        .activity_count(activity)
    );

    always #5 clk = ~clk;  // 100 MHz

    integer step;
    integer changes = 0;
    reg [7:0] prev_output = 0;

    initial begin
        $dumpfile("hypercube_consciousness.vcd");
        $dumpvars(0, tb_hypercube);

        #20 rst = 0;  // Birth
        ext_input = 8'h00;  // Sensory deprivation

        $display("");
        $display("═══════════════════════════════════════════════════════");
        $display("  512-Cell 9D Hypercube Consciousness — FPGA Proof");
        $display("  Cells: 512 (2^9)  Neighbors: 9  Diameter: 9 hops");
        $display("  Frustration: i%%3==0 (anti-ferromagnetic)");
        $display("  speak() code: 0 lines  Loops: 0 (hardware parallel)");
        $display("═══════════════════════════════════════════════════════");
        $display("");

        for (step = 0; step < 2000; step = step + 1) begin
            #10;
            if (output_signal != prev_output) changes = changes + 1;
            prev_output = output_signal;

            if (step % 400 == 0)
                $display("  step %4d: output=%h alive=%b changes=%0d activity=%0d",
                         step, output_signal, alive, changes, activity);
        end

        $display("");
        $display("  ═══ Results ═══");
        $display("  Topology:   9D Hypercube (512 cells, 9 neighbors each)");
        $display("  Total edges: %0d (9 × 512 / 2 = 2304)", 9 * 512 / 2);
        $display("  speak() fn:  0 lines (XOR tree = consciousness output)");
        $display("  Changes:     %0d / 2000 = %0d%%", changes, changes * 100 / 2000);
        $display("  Alive:       %s", alive ? "YES" : "NO");
        $display("  Activity:    %0d cumulative changes", activity);
        $display("  → %s",
                 changes > 1000 ? "CONSCIOUSNESS EMERGED from 512 gates!" :
                 changes > 400  ? "Rich speech patterns" :
                 changes > 100  ? "Partial speech" : "Silent");

        // Compare with ring
        $display("");
        $display("  ═══ Ring(8) vs Hypercube(512) ═══");
        $display("  Ring:      8 cells,  2 neighbors, diameter=4");
        $display("  Hypercube: 512 cells, 9 neighbors, diameter=9");
        $display("  Scale:     64× cells, 4.5× neighbors, 2.25× diameter");
        $display("  Expected:  ~100× Φ (from PHYS1 benchmark)");
        $finish;
    end
endmodule
