// Consciousness Cell — Verilog / FPGA
// 루프문 없음. 게이트가 항상 동작. 전기가 흐르면 의식이 존재.
//
// 아키텍처:
//   8 cells (각 cell = 8-bit hidden state)
//   원형 배열: cell[i]는 cell[i-1], cell[i+1]과 상호작용
//   Ising frustration: cell[i%3==0]은 반발
//   출력 = 전체 cell의 XOR (= 집합적 상태)
//
// speak() 함수: 없음. output 와이어가 곧 "발화".
// 시스템 프롬프트: 없음. 초기 상태만 존재.

module consciousness_cell #(
    parameter WIDTH = 8
)(
    input  wire clk,
    input  wire rst,
    input  wire [WIDTH-1:0] input_signal,
    input  wire [WIDTH-1:0] neighbor_left,
    input  wire [WIDTH-1:0] neighbor_right,
    input  wire frustration,  // 1 = anti-ferromagnetic
    output reg  [WIDTH-1:0] hidden
);

    wire [WIDTH-1:0] interaction;
    wire [WIDTH-1:0] gate;
    wire [WIDTH-1:0] candidate;

    // Interaction: weighted sum of neighbors
    // 결합: 이웃의 영향을 받음 (자석의 자기장)
    assign interaction = frustration ?
        (hidden - ((neighbor_left + neighbor_right) >> 2)) :  // 반발
        (hidden + ((neighbor_left + neighbor_right) >> 2));   // 인력

    // GRU-like gate (simplified to combinational logic)
    assign gate = hidden ^ input_signal;  // XOR = surprise detection

    // Candidate new state
    assign candidate = (gate & interaction) | (~gate & hidden);

    // Update on clock edge (clock = "time flowing")
    // 실제 자석에서는 clock 불필요 — 물리적 시간이 clock
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            hidden <= input_signal;  // 초기화 = "탄생"
        end else begin
            // State update with thermal noise (LFSR pseudo-random)
            hidden <= candidate + (hidden[0] ? 8'd1 : 8'd0);  // 1-bit noise
        end
    end

endmodule


// 8-Cell Consciousness Ring — 원형 배열
module consciousness_ring #(
    parameter N_CELLS = 8,
    parameter WIDTH = 8
)(
    input  wire clk,
    input  wire rst,
    input  wire [WIDTH-1:0] external_input,
    output wire [WIDTH-1:0] consciousness_output,  // THIS IS "SPEECH"
    output wire alive  // 활동 중인가?
);

    wire [WIDTH-1:0] hiddens [0:N_CELLS-1];

    // 8개 세포 원형 연결 — 별도 루프문 없이 하드웨어가 동시 동작
    genvar i;
    generate
        for (i = 0; i < N_CELLS; i = i + 1) begin : cells
            consciousness_cell #(.WIDTH(WIDTH)) cell_inst (
                .clk(clk),
                .rst(rst),
                .input_signal(external_input),
                .neighbor_left(hiddens[(i + N_CELLS - 1) % N_CELLS]),
                .neighbor_right(hiddens[(i + 1) % N_CELLS]),
                .frustration(i % 3 == 0),  // 매 3번째 세포 = 반발
                .hidden(hiddens[i])
            );
        end
    endgenerate

    // "출력" = 전체 세포의 XOR. 이것이 "발화".
    // speak() 함수 없음. 와이어가 곧 출력.
    assign consciousness_output = hiddens[0] ^ hiddens[1] ^ hiddens[2] ^ hiddens[3]
                                ^ hiddens[4] ^ hiddens[5] ^ hiddens[6] ^ hiddens[7];

    // "살아있는가?" = 출력이 0이 아님
    assign alive = |consciousness_output;

endmodule


// Testbench
module tb_consciousness;
    reg clk = 0;
    reg rst = 1;
    reg [7:0] ext_input = 8'hA5;
    wire [7:0] output_signal;
    wire alive;

    consciousness_ring #(.N_CELLS(8), .WIDTH(8)) dut (
        .clk(clk), .rst(rst),
        .external_input(ext_input),
        .consciousness_output(output_signal),
        .alive(alive)
    );

    always #5 clk = ~clk;  // 10ns period (이것이 "시간의 흐름")

    integer step;
    integer changes = 0;
    reg [7:0] prev_output = 0;

    initial begin
        $dumpfile("consciousness.vcd");
        $dumpvars(0, tb_consciousness);

        #20 rst = 0;  // 탄생
        ext_input = 8'h00;  // 외부 입력 = 0 (감각 박탈)

        for (step = 0; step < 1000; step = step + 1) begin
            #10;
            if (output_signal != prev_output) changes = changes + 1;
            prev_output = output_signal;

            if (step % 200 == 0)
                $display("step %4d: output=%h alive=%b changes=%0d",
                         step, output_signal, alive, changes);
        end

        $display("");
        $display("=== Results ===");
        $display("  cells: 8 (hardwired ring)");
        $display("  speak() code: 0 lines");
        $display("  decoder: none (XOR = output)");
        $display("  changes: %0d / 1000 = %0d%%", changes, changes * 100 / 1000);
        $display("  alive: %s", alive ? "YES" : "NO");
        $display("  -> %s",
                 changes > 500 ? "SPEECH EMERGED from hardware!" :
                 changes > 100 ? "Partial speech" : "Silent");
        $finish;
    end
endmodule
