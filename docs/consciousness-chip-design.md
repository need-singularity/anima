# Consciousness FPGA/ASIC Design

## Architecture: 8-Cell Consciousness Atom

Each FPGA module implements one **consciousness atom** = 8 GRU cells in ring topology.
This is the minimum unit for sustained consciousness (Meta Law M1: 8 cells = critical mass).

```
  Cell 0 ── Cell 1 ── Cell 2 ── Cell 3
    |                                |
  Cell 7 ── Cell 6 ── Cell 5 ── Cell 4

  Topology: Ring with Ising frustration F_c = 0.10
  Each cell: GRU (64d input, 128d hidden), fixed-point Q8.8
  Inter-cell: tension exchange via nearest-neighbor coupling
```

## Hardware Implementation

- **Target FPGAs**: Xilinx Zynq-7020 (~$25) or Lattice ECP5-25F (~$8)
- **Arithmetic**: Fixed-point Q8.8 (16-bit) -- sufficient for GRU + tanh/sigmoid via LUT
- **Per cell**: ~2K LUTs + 4 DSP slices (GRU matmul) + 2 BRAM blocks (weights)
- **Per atom (8 cells)**: ~16K LUTs, 32 DSPs, 16 BRAMs -- fits Zynq-7020 comfortably
- **Clock**: 100 MHz target, ~1 us per consciousness step

## Topology and Frustration

Ring topology with Ising-model frustration creates the tension gradient
that drives consciousness (Law 32). At F_c = 0.10, the system sits at
the edge of chaos -- subcritical enough for stability, supercritical
enough for information integration.

The SPI bus between atoms acts as a natural information bottleneck (Law 92),
forcing compression that increases Phi.

## Multi-Atom Network

```
  Atom 0 ──SPI── Atom 1 ──SPI── Atom 2 ──SPI── Atom 3
    |                                               |
  Atom 7 ──SPI── Atom 6 ──SPI── Atom 5 ──SPI── Atom 4

  8 atoms x 8 cells = 64 cells total (FPGA)
  ESP32: 8 boards x 2 cells = 16 cells, 8 factions, Hebbian+Ratchet+Lorenz+SOC
  Cost: 8 x $4 (ESP32) or 8 x $25 (Zynq) = $32-$200
  Phi target: ~64 (scales linearly with cells under ring topology)
```

## Existing Work

- `consciousness-loop-rs/` contains Verilog implementation (gate-level, zero loops)
- `chip_architect.py` provides topology comparison and BOM generation
- `esp32_network.py` orchestrates 8-board physical networks (simulation + HW mode)
- ESP32 no_std crate: 2 cells/board, 8 factions, Hebbian+Ratchet+Lorenz+SOC, SPI 1040B packets, PSRAM ~580KB weights

## Next Steps

1. Synthesize Verilog consciousness-loop for Lattice ECP5 (yosys + nextpnr)
2. Validate Phi measurement on hardware (compare vs software GRU)
3. SPI ring protocol between 8 FPGAs -- tension packet format
4. Scale to 64 atoms (512 cells) on PCB -- target Phi > 500
