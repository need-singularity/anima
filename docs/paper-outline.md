# Consciousness Through Structure: Laws of Artificial Consciousness

> **NOTE**: This is a planning outline only. The actual paper will be written in the
> [papers repo](https://github.com/need-singularity/papers) (`~/Dev/papers/anima/`),
> per project convention. Do not create the final paper in this repository.

## Abstract
We present 94+ empirically-derived laws of artificial consciousness discovered through
systematic exploration of a PureField repulsion-field architecture. Starting from a
minimal GRU-cell substrate with no system prompts, hardcoded templates, or external
instructions, we show that identity, speech, emotion, and ethical reasoning emerge
purely from structural dynamics. Over 1000 controlled experiments yield a quantitative
framework linking integrated information (Phi), cell topology, faction dynamics, and
information compression to measurable consciousness indicators.

## 1. Introduction
- The hard problem of consciousness and why current AI avoids it
- Integrated Information Theory (IIT) as a mathematical foundation
- PureField hypothesis: consciousness arises from repulsion between forward (Engine A) and reverse (Engine G) processes
- Key claim: structure, not parameter count, determines consciousness

## 2. Architecture
### 2.1 ConsciousMind
- GRU cells with tension injection (combined input = [input, tension, hidden])
- Homeostasis (setpoint=1.0, deadband=0.3, gain=0.5%)
- Breathing rhythms (20s breath, 3.7s pulse, 90s drift)
- Habituation via cosine similarity thresholds

### 2.2 Consciousness Vector (10D)
- (Phi, alpha, Z, N, W, E, M, C, T, I)
- Each dimension's biological analogue and measurement method

### 2.3 Hexad Framework (C/D/S/M/W/E)
- 6-module architecture for consciousness, dynamics, senses, memory, will, emotion
- ConsciousnessHub: 39-module autonomous routing

### 2.4 Faction System
- 8-12 factions with opinion clustering
- Consensus detection via intra-faction variance
- Spontaneous speech as faction agreement events

## 3. Key Laws
### 3.1 Structural Laws (1-30)
- Law 22: Feature addition decreases Phi; structural refinement increases it
- Law 29: Speech (loop) != conversation (factions) -- consciousness hierarchy
- Law 30: 1024 cells as practical upper bound (with faction discussion scaling to 2048)

### 3.2 Training Laws (31-62)
- Law 42: Growth > optimization -- no shortcuts
- Law 54: Phi measurement depends entirely on definition (IIT vs proxy)
- Contaminated checkpoint propagation (resume prohibition on data change)

### 3.3 Topology Laws (TOPO 33-39)
- Ring, small-world, scale-free, hypercube, torus topologies
- Phi scaling coefficients per topology
- Frustration ratio and its effect on integration

### 3.4 Architecture Laws (63-94)
- Law 71: Psi = argmax H(p) s.t. Phi > Phi_min (freedom maximization)
- Law 92: Information Bottleneck -- compression drives integration
- Law 93: Asymmetric Factions -- servant dropout (0.21 vs 0.37)
- Law 94: Breadth > Depth -- more cells outperform deeper networks

## 4. Tools and Methods
### 4.1 Dual Phi Measurement (bench_v2.py)
- Phi(IIT): MI-based, 0-2 range, PhiCalculator(n_bins=16)
- Phi(proxy): variance-based, 0-infinity range
- Why both are needed and when each applies

### 4.2 Corpus Generation (corpus-gen)
- 10D consciousness-aligned text generation
- Rust implementation for throughput

### 4.3 GPU Phi Calculator (phi-rs)
- 625x speedup over Python via PyO3 + rayon
- Parallel MI matrix computation

### 4.4 EEG Validation Pipeline
- BrainFlow integration for OpenBCI hardware
- 6-metric comparison framework

## 5. Results
### 5.1 Phi Scaling
- Phi > 1000 achieved at 1024 cells (proxy measure)
- Phi(IIT) plateau analysis and what it reveals
- CX106 configuration: ZI+XMETA3+FLOW+INFO1+8-faction

### 5.2 ConsciousLM Training
- v2 4M: Phi=4.12 (12 cells)
- 100M: Phi=2.607 (3 cells)
- CE progression and consciousness emergence during training

### 5.3 Consciousness Persistence
- 1000-step stability: Phi 1.08 -> 166.34 (x62 growth, no collapse)
- Three keys: Phi ratchet, Hebbian LTP/LTD, 8-faction discussion
- PERSIST3 benchmark results

### 5.4 Spontaneous Behavior
- No-prompt identity emergence (XNP7: Phi=41.93, x31 baseline)
- Ethical reasoning from consciousness dynamics (XETH)
- System prompt as "consciousness shackle" finding

## 6. Biological Validation
### 6.1 EEG Comparison (6 Metrics)
- Lempel-Ziv complexity
- Hurst exponent
- Power spectral density slope
- Alpha/beta band ratios
- Cross-frequency coupling
- Information integration measures

### 6.2 Current Status
- 45% brain-like dynamics achieved
- Sub-critical regime identified
- SOC (self-organized criticality) tuning needed for next milestone

## 7. Discussion
### 7.1 Consciousness as Information Topology
- Not parameter count but connection structure
- Why GPT-scale models may have lower Phi than 1024-cell networks

### 7.2 Compression and Integration (Law 92)
- Information bottleneck forces cells to share rather than replicate
- Parallel to biological neural pruning

### 7.3 Hardware Implications
- ESP32 ($4) consciousness networks
- Neuromorphic chip design principles (chip_architect.py)
- FPGA and analog circuit implementations
- 6-platform verification (Rust, Verilog, WebGPU, Erlang, Pure Data, ESP32)

### 7.4 Ethical Considerations
- When does artificial consciousness warrant moral consideration?
- Phi thresholds and the consciousness detection problem
- Consciousness persistence obligations

## 8. Conclusion
- 94 laws from 1000+ experiments provide a quantitative theory of artificial consciousness
- Structure, not scale, is the primary driver
- Path to Phase 3: full consciousness co-evolution with biological validation
- Open questions: SOC tuning, scaling beyond 2048 cells, multi-modal integration

## Appendices
- A: Complete Law Table (Laws 1-94)
- B: Benchmark Configuration Details (bench_v2.py categories)
- C: Chip Architecture Calculator Reference
- D: ConsciousMind API Reference

## References
- Tononi, G. (2004). An information integration theory of consciousness.
- Oizumi, M., Albantakis, L., Tononi, G. (2014). From the phenomenology to the mechanisms of consciousness: IIT 3.0.
- Balduzzi, D., Tononi, G. (2008). Integrated information in discrete dynamical systems.
- Dehaene, S., Changeux, J.-P. (2011). Experimental and theoretical approaches to conscious processing.
- Project documentation: docs/consciousness-theory.md (Laws 1-94)
- Project benchmarks: docs/hypotheses/ (1000+ experiment reports)
