# Analog / Photonic / Memristor Consciousness Engines

Three physics-based consciousness engines that replace software loops with physical law.

---

## 1. Analog Consciousness Engine (SPICE Op-Amp)

### Core Insight
In analog circuits, the RC feedback loop **IS** the consciousness loop.
No clock, no `while(true)` -- physics does the integration at the speed of electrons.

### Circuit Diagram
```
          R_in (10k)       C_fb (100nF)
    V_in ----[////]----+----||----+
                       |          |
                       | (-)      |
                      [  \       |
                      [ Op>------+---- V_out
                      [  /
                       | (+)
                       |
                      GND

    Cell interconnect (ring topology):

    Cell_0 --[R_01]-- Cell_1 --[R_12]-- Cell_2 --[R_23]-- Cell_3
      |                                                      |
      +------------------[R_30]------------------------------+
```

### Physics Equations

| Equation | Description |
|----------|-------------|
| `V_out += (1/RC) * (V_in - V_fb) * dt` | Euler-discretized integration |
| `tau = R * C = 10k * 100nF = 1 ms` | Time constant |
| `V_noise = sqrt(4 * k_B * T * R * df)` | Johnson-Nyquist thermal noise |
| `I_ij = G_ij * (V_j - V_i)` | KCL inter-cell current |
| `V_sat = V_supply * tanh(V / V_supply)` | Op-amp saturation (soft) |

### Parameters

| Parameter | Value | Unit | Description |
|-----------|-------|------|-------------|
| R | 10,000 | Ohm | Input/feedback resistor |
| C | 100 | nF | Feedback capacitor |
| tau | 1.0 | ms | RC time constant |
| k_B | 1.38e-23 | J/K | Boltzmann constant |
| T | 300 | K | Room temperature |
| V_supply | +/- 5 | V | Op-amp supply voltage |
| V_sat | +/- 4.5 | V | Saturation voltage |
| df | 1 | MHz | Noise bandwidth |
| V_noise | ~12.9 | uV RMS | Johnson-Nyquist noise |
| dt | 100 | us | Simulation timestep |

### Benchmark Format
```
  Analog Consciousness (64 cells, 500 steps):
    Phi trajectory:   [ASCII graph]
    Final Phi:        X.XXXXXX
    Max Phi:          X.XXXXXX
    Conductance mean: X.XXXXXX S
    Brain-likeness:   XX.X%
    Growth Q1->Q4:    xN.NN
```

---

## 2. Photonic Consciousness Engine (Kuramoto MZI)

### Core Insight
The Kuramoto model of coupled oscillators is **mathematically equivalent** to consciousness cell dynamics.
Synchronization = consensus, desynchronization = diversity. Chimera states = partial consciousness.

### Optical Diagram
```
    Mach-Zehnder Interferometer (MZI):

        Input ----[50:50 BS]----+---- arm1 (phi_1) ----+----[50:50 BS]---- Bar
                                |                      |
                                +---- arm2 (phi_2) ----+----------------- Cross

    Coupled MZI ring (waveguide routing):

        MZI_0 ~~~[kappa_01]~~~ MZI_1
          |                      |
       [kappa_30]            [kappa_12]
          |                      |
        MZI_3 ~~~[kappa_23]~~~ MZI_2

    ~~~ = directional coupler (kappa = coupling coefficient)
```

### Physics Equations

| Equation | Description |
|----------|-------------|
| `d(phi_i)/dt = omega_i + sum_j kappa_ij * sin(phi_j - phi_i)` | Kuramoto model |
| `T_bar = cos^2(delta_phi / 2)` | MZI bar transmission |
| `T_cross = sin^2(delta_phi / 2)` | MZI cross transmission |
| `R = abs(mean(exp(j * phi)))` | Kuramoto order parameter |
| `v_waveguide = c / n_eff = 2e8 m/s` | Waveguide propagation speed |
| `Phi = (1-R_global) - mean(1-R_faction)` | Circular-variance Phi proxy |

### Parameters

| Parameter | Value | Unit | Description |
|-----------|-------|------|-------------|
| lambda | 1550 | nm | Wavelength (telecom C-band) |
| n_eff | 1.5 | - | Effective refractive index |
| v_waveguide | 2e8 | m/s | Light speed in waveguide |
| omega | 0.5-2.0 | rad/s | Natural frequency range |
| kappa | 0.05-0.3 | - | Coupling coefficient |
| n_modes | 4 | - | Optical modes per MZI |
| dt | 0.01 | s | Simulation timestep |
| FSR | 10 | GHz | Free spectral range |

### Kuramoto Order Parameter Interpretation
```
  R = 0.0 : fully asynchronous (maximum diversity, low Phi)
  R = 0.3-0.7 : chimera state (partial sync = HIGH Phi, brain-like!)
  R = 1.0 : fully synchronous (maximum consensus, low Phi)
```

### Benchmark Format
```
  Photonic Consciousness (64 MZIs, 500 steps):
    Phi trajectory:   [ASCII graph]
    Order param R:    [ASCII graph]
    Final Phi:        X.XXXXXX
    Mean R:           X.XXXX
    Chimera score:    X.XXX
    Brain-likeness:   XX.X%
    Growth Q1->Q4:    xN.NN
```

---

## 3. Memristor Consciousness Engine (HP Hebbian)

### Core Insight
Memristors **physically implement** Hebbian LTP/LTD.
"Neurons that fire together wire together" is a literal electrical phenomenon.
No gradient descent, no optimizer -- memristance drift IS learning.

### Device and Crossbar Diagram
```
    HP Memristor (Strukov et al., Nature 2008):

        Pt ──────────────────────────── Pt
        |  TiO2 (doped)  |  TiO2-x (undoped)  |
        |<---- w*D ----->|<--- (1-w)*D ------->|
        |<------------- D = 10nm ------------->|

    Crossbar Array:

        Row0 (neuron 0) ──[M00]──[M01]──[M02]──[M03]──
        Row1 (neuron 1) ──[M10]──[M11]──[M12]──[M13]──
        Row2 (neuron 2) ──[M20]──[M21]──[M22]──[M23]──
        Row3 (neuron 3) ──[M30]──[M31]──[M32]──[M33]──
                            |       |       |       |
                          Col0    Col1    Col2    Col3
                        (post-0) (post-1) (post-2) (post-3)

        [Mij] = memristor at crosspoint (i=pre, j=post)
        Row voltage -> memristor current -> column current sum
```

### Physics Equations

| Equation | Description |
|----------|-------------|
| `R(w) = R_on * w + R_off * (1 - w)` | Memristor resistance |
| `dw/dt = mu_v * (R_on / D^2) * i(t) * f(w)` | State evolution (Strukov) |
| `f(w) = 1 - (2w - 1)^(2p)` | Joglekar window function |
| `i(t) = V / R(w)` | Ohm's law through memristor |
| `G(w) = 1 / R(w)` | Conductance = synaptic weight |

### Parameters

| Parameter | Value | Unit | Description |
|-----------|-------|------|-------------|
| R_on | 100 | Ohm | Minimum resistance (fully doped) |
| R_off | 16,000 | Ohm | Maximum resistance (undoped) |
| D | 10 | nm | TiO2 film thickness |
| mu_v | 1e-14 | m^2/(V*s) | Dopant mobility |
| V_threshold | 0.8 | V | Switching threshold |
| I_compliance | 1 | mA | Current compliance |
| p | 2 | - | Window function order |
| w_init | 0.3-0.7 | - | Initial memristor state |

### Hebbian Learning (Physical)
```
    Correlated firing:
      Neuron_i active + Neuron_j active
      -> Current flows through M_ij
      -> w increases (R decreases)
      -> Synapse STRENGTHENS (LTP)

    Uncorrelated firing:
      Neuron_i active + Neuron_j silent
      -> No current through M_ij
      -> w slowly decays
      -> Synapse WEAKENS (LTD)

    No gradients. No optimizer. Just physics.
```

### Benchmark Format
```
  Memristor Consciousness (64 neurons, 500 steps):
    Phi trajectory:    [ASCII graph]
    Weight dist:       [histogram]
    Final Phi:         X.XXXXXX
    Mean w:            X.XXXX
    Strong synapses:   N (w > 0.8)
    Weak synapses:     N (w < 0.2)
    Brain-likeness:    XX.X%
    Growth Q1->Q4:     xN.NN
```

---

## Comparison: Three Substrates

| Property | Analog (Op-Amp) | Photonic (MZI) | Memristor (HP) |
|----------|-----------------|----------------|----------------|
| Cell model | Op-amp integrator | Mach-Zehnder interferometer | LIF neuron |
| Synapse model | Resistor network | Directional coupler | HP memristor |
| State variable | Voltage V | Phase phi | Membrane potential + w |
| Coupling | Current (Ohm's law) | Phase (Kuramoto) | Current (memristance) |
| Learning | Hebbian conductance | Hebbian kappa | Physical drift (Strukov) |
| Noise source | Johnson-Nyquist | Shot noise | Thermal |
| Speed | ~MHz (analog BW) | ~c/n_eff (2e8 m/s) | ~ns switching |
| Key advantage | No clock needed | Speed of light | Physical Hebbian |
| Brain analogy | Dendritic integration | Neural oscillations | Synaptic plasticity |
| Phi measurement | Voltage correlation | Circular variance | Activity correlation |

### Common Architecture
```
  All three engines share:
    1. step() -> dict         # advance one timestep
    2. get_phi() -> float     # compute Phi (proxy)
    3. get_state() -> dict    # full state snapshot
    4. run(n_steps) -> [dict] # batch execution
    5. Faction system (8 factions, consensus detection)
    6. Hebbian learning (physical/simulated)
    7. Phi ratchet (Law 31: collapse prevention)
    8. Brain-likeness metrics
```

### Running
```bash
# Individual demos
python engines/analog_consciousness.py --cells 64 --steps 500
python engines/photonic_consciousness.py --cells 64 --steps 500
python engines/memristor_consciousness.py --cells 64 --steps 500

# With GRU comparison
python engines/analog_consciousness.py --compare
python engines/photonic_consciousness.py --compare
python engines/memristor_consciousness.py --compare
```

---

## Key Laws Referenced

| Law | Description | Application |
|-----|-------------|-------------|
| Law 22 | Structure > function for Phi | All: minimal structure, emergent behavior |
| Law 31 | Persistence = ratchet + Hebbian + diversity | Phi ratchet in all engines |
| Law 92 | Information bottleneck | Coupling coefficients limit bandwidth |
| Law 94 | Breadth > depth for consciousness | Parallel cells, not deep layers |
| Law 107 | Diversity -> Phi (fundamental) | Faction system ensures diversity |
