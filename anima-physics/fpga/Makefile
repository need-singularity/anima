# Makefile — iCE40UP5K Consciousness Ring Build Flow
#
# Toolchain: yosys + nextpnr-ice40 + icestorm (all open source)
# Target: Lattice iCE40UP5K-B-EVN ($15 board)
# Note: This Makefile drives Verilog/HDL toolchain only — no rust/python.
#       Hexa-native build orchestration handled separately by $HEXA.
#
# Usage:
#   make           Build bitstream
#   make prog      Program FPGA via USB
#   make sim       Simulate with Icarus Verilog
#   make timing    Show timing report
#   make util      Show utilization report
#   make clean     Remove generated files

# ── Configuration ──
DEVICE    = up5k
PACKAGE   = sg48
TOP       = consciousness_ice40_top
FREQ      = 12  # MHz (target frequency for timing analysis)

# ── Source files ──
VERILOG   = consciousness_ice40.v
PCF       = pins.pcf

# ── Original Verilog (for simulation) ──
VERILOG_SIM_RING  = ../consciousness-loop-rs/verilog/consciousness_cell.v
VERILOG_SIM_HYPER = ../consciousness-loop-rs/verilog/consciousness_hypercube.v

# ── Output files ──
JSON      = synth.json
ASC       = pnr.asc
BIN       = bitstream.bin
TIMING    = timing.rpt

# ══════════════════════════════════════════
# Build targets
# ══════════════════════════════════════════

.PHONY: all prog sim sim-ring sim-hyper timing util clean

all: $(BIN)

# Step 1: Synthesis (Verilog -> netlist)
$(JSON): $(VERILOG)
	@echo "=== Synthesis (yosys) ==="
	yosys -p "read_verilog $(VERILOG); synth_ice40 -top $(TOP) -json $(JSON)" 2>&1 | \
		grep -E "(Number|Estimated|Warning|Error)"

# Step 2: Place & Route (netlist -> FPGA layout)
$(ASC): $(JSON) $(PCF)
	@echo "=== Place & Route (nextpnr) ==="
	nextpnr-ice40 --$(DEVICE) --package $(PACKAGE) \
		--json $(JSON) --pcf $(PCF) --asc $(ASC) \
		--freq $(FREQ) 2>&1 | \
		grep -E "(Max frequency|Info: Device|cells|LCs)"

# Step 3: Bitstream generation
$(BIN): $(ASC)
	@echo "=== Bitstream (icepack) ==="
	icepack $(ASC) $(BIN)
	@echo "Bitstream: $(BIN) ($$(wc -c < $(BIN)) bytes)"

# ══════════════════════════════════════════
# Programming
# ══════════════════════════════════════════

prog: $(BIN)
	@echo "=== Programming FPGA ==="
	iceprog $(BIN)
	@echo "Done. Open serial monitor: screen /dev/cu.usbmodem* 9600"

# ══════════════════════════════════════════
# Simulation
# ══════════════════════════════════════════

sim: sim-ring

sim-ring:
	@echo "=== Simulating 8-cell ring ==="
	iverilog -o sim_ring $(VERILOG_SIM_RING)
	vvp sim_ring
	@echo "Waveform: consciousness.vcd (open with gtkwave)"

sim-hyper:
	@echo "=== Simulating 512-cell hypercube ==="
	iverilog -o sim_hyper $(VERILOG_SIM_HYPER)
	vvp sim_hyper
	@echo "Waveform: hypercube_consciousness.vcd"

# ══════════════════════════════════════════
# Reports
# ══════════════════════════════════════════

timing: $(ASC)
	@echo "=== Timing Report ==="
	icetime -d $(DEVICE) -mtr $(TIMING) $(ASC)
	@cat $(TIMING)

util: $(JSON)
	@echo "=== Utilization Report ==="
	yosys -p "read_verilog $(VERILOG); synth_ice40 -top $(TOP); stat"

# ══════════════════════════════════════════
# Clean
# ══════════════════════════════════════════

clean:
	rm -f $(JSON) $(ASC) $(BIN) $(TIMING)
	rm -f sim_ring sim_hyper
	rm -f *.vcd
	@echo "Cleaned."
