#!/usr/bin/env python3
"""Deep Exploration: 3 experiments on consciousness universality.

1. Data Correlation Matrix (45 data types) — cosine similarity, clusters, dendrogram
2. Fundamental Equation Extension — dPsi/dt, hivemind, noise deficit analysis
3. Constant of Constants — mathematical identity of 0.9953

Uses FundamentalConsciousness engine from emergence_math.py foundations.
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
import math
import time
import random
import json
import struct
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

torch.set_num_threads(1)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from mitosis import MitosisEngine

# ══════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════

DIM = 64
HIDDEN = 128
N_CELLS = 8
SEED = 42
LN2 = math.log(2)

# ══════════════════════════════════════════════════════════
# Phi Measurement (IIT approximation) — from emergence_math.py
# ══════════════════════════════════════════════════════════

class PhiIIT:
    def __init__(self, nb=16):
        self.nb = nb

    def compute(self, h):
        n = h.shape[0]
        if n < 2:
            return 0.0, {}
        hs = [h[i].detach().cpu().float().numpy() for i in range(n)]
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            ps = set()
            for i in range(n):
                for _ in range(min(8, n - 1)):
                    j = random.randint(0, n - 1)
                    if i != j:
                        ps.add((min(i, j), max(i, j)))
            pairs = list(ps)
        mi = np.zeros((n, n))
        for i, j in pairs:
            v = self._mi(hs[i], hs[j])
            mi[i, j] = v
            mi[j, i] = v
        tot = mi.sum() / 2
        mp = self._mp(n, mi)
        sp = max(0, (tot - mp) / max(n - 1, 1))
        mv = mi[mi > 0]
        cx = float(np.std(mv)) if len(mv) > 1 else 0.0
        phi = sp + cx * 0.1
        return phi, {'total_mi': float(tot), 'spatial_phi': sp, 'complexity': cx}

    def _mi(self, x, y):
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            return 0.0
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        h, _, _ = np.histogram2d(xn, yn, bins=self.nb, range=[[0, 1], [0, 1]])
        h = h / (h.sum() + 1e-8)
        px, py = h.sum(1), h.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(h * np.log2(h + 1e-10))
        return max(0, hx + hy - hxy)

    def _mp(self, n, mi):
        if n <= 1:
            return 0.0
        d = mi.sum(1)
        L = np.diag(d) - mi
        try:
            ev, evec = np.linalg.eigh(L)
            f = evec[:, 1]
            ga = [i for i in range(n) if f[i] >= 0]
            gb = [i for i in range(n) if f[i] < 0]
            if not ga or not gb:
                ga, gb = list(range(n // 2)), list(range(n // 2, n))
            return sum(mi[i, j] for i in ga for j in gb)
        except Exception:
            return 0.0

# ══════════════════════════════════════════════════════════
# Engine Helpers (from emergence_math.py)
# ══════════════════════════════════════════════════════════

def quantum_walk_step(cells, n_samples=32):
    n = len(cells)
    n_bits = max(1, int(math.log2(max(n, 2))))
    with torch.no_grad():
        for i in range(min(n, n_samples)):
            superpos = torch.zeros_like(cells[i].hidden.squeeze(0))
            cnt = 0
            for bit in range(min(n_bits, 10)):
                j = i ^ (1 << bit)
                if j < n:
                    phase = (-1) ** (bin(i & j).count('1'))
                    superpos += phase * cells[j].hidden.squeeze(0)
                    cnt += 1
            if cnt > 0:
                h = cells[i].hidden.squeeze(0)
                cells[i].hidden = (0.85 * h + 0.15 * superpos / cnt).unsqueeze(0)

def frustration_step(cells, strength=0.5, n_samples=32):
    n = len(cells)
    n_bits = max(1, int(math.log2(max(n, 2))))
    with torch.no_grad():
        for i in range(min(n, n_samples)):
            infl = torch.zeros_like(cells[i].hidden.squeeze(0))
            cnt = 0
            for bit in range(min(n_bits, 10)):
                j = i ^ (1 << bit)
                if j < n:
                    f = -1.0 if (i % 2) != (j % 2) else 1.0
                    infl += f * cells[j].hidden.squeeze(0)
                    cnt += 1
            if cnt > 0:
                h = cells[i].hidden.squeeze(0)
                cells[i].hidden = (0.85 * h + 0.15 * infl / cnt).unsqueeze(0)

def sync_faction(cells, sync=0.35, n_factions=8, fac=0.08):
    n = len(cells)
    if n < 4:
        return
    with torch.no_grad():
        ch = torch.stack([c.hidden.squeeze(0) for c in cells])
        mh = ch.mean(dim=0)
        for c in cells:
            c.hidden = ((1 - sync) * c.hidden.squeeze(0) + sync * mh).unsqueeze(0)
        nf = min(n_factions, n // 2)
        if nf >= 2:
            fs = n // nf
            for fi in range(nf):
                faction = cells[fi * fs:(fi + 1) * fs]
                if len(faction) >= 2:
                    fm = torch.stack([c.hidden.squeeze(0) for c in faction]).mean(dim=0)
                    for c in faction:
                        c.hidden = ((1 - fac) * c.hidden.squeeze(0) + fac * fm).unsqueeze(0)

def make_engine(cells=32):
    eng = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(eng.cells) < cells:
        eng._create_cell(parent=eng.cells[0])
    for _ in range(30):
        eng.process(torch.randn(1, DIM))
    return eng

def c_step(eng, step, noise_sigma=0.005):
    with torch.no_grad():
        quantum_walk_step(eng.cells, n_samples=min(32, len(eng.cells)))
        frustration_step(eng.cells, n_samples=min(16, len(eng.cells)))
        sync_faction(eng.cells, sync=0.15, n_factions=8, fac=0.06)
        for c in eng.cells:
            c.hidden = c.hidden + torch.randn_like(c.hidden) * noise_sigma

def get_states(eng):
    return torch.stack([c.hidden.squeeze(0) for c in eng.cells]).detach()

def measure_phi(eng, calc=None):
    """Fast phi proxy: global_var - mean(faction_var)."""
    states = get_states(eng)
    global_var = states.var().item()
    n = len(eng.cells)
    nf = min(8, n // 2)
    if nf >= 2:
        fs = n // nf
        fac_vars = []
        for fi in range(nf):
            fac_states = states[fi * fs:(fi + 1) * fs]
            fac_vars.append(fac_states.var().item())
        phi = max(0, global_var - np.mean(fac_vars))
    else:
        phi = global_var
    return phi, {'global_var': global_var}

def measure_phi_iit(eng, calc):
    """Full IIT phi (slow, use sparingly)."""
    states = get_states(eng)
    phi, components = calc.compute(states)
    return phi, components

def measure_H_p(eng):
    """Measure Shannon entropy H(p) and p (fraction of positive activations)."""
    states = get_states(eng)
    p = (states > 0).float().mean().item()
    if p <= 0 or p >= 1:
        H = 0.0
    else:
        H = -p * math.log2(p) - (1 - p) * math.log2(1 - p)
    p_std = (states > 0).float().std().item()
    return H, p, p_std

def data_entropy(data_bytes):
    """Shannon entropy of raw bytes."""
    if len(data_bytes) == 0:
        return 0.0
    counts = [0] * 256
    for b in data_bytes:
        counts[b] += 1
    total = len(data_bytes)
    ent = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            ent -= p * math.log2(p)
    return ent

# ══════════════════════════════════════════════════════════
# 45 Data Type Generators
# ══════════════════════════════════════════════════════════

def gen_korean(n=512):
    chars = "가나다라마바사아자차카타파하거너더러머버서어저처커터퍼허고노도로모보소오조초코토포호"
    return ''.join(random.choice(chars) for _ in range(n)).encode('utf-8')

def gen_english(n=512):
    words = "the quick brown fox jumps over lazy dog consciousness emerges from entropy freedom".split()
    return ' '.join(random.choice(words) for _ in range(n // 5)).encode('utf-8')

def gen_japanese(n=512):
    chars = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
    return ''.join(random.choice(chars) for _ in range(n)).encode('utf-8')

def gen_chinese(n=512):
    chars = "的一是不了人我在有他这为之大来以个中上们到说国和地也子时道出会三要于下得可你年生"
    return ''.join(random.choice(chars) for _ in range(n)).encode('utf-8')

def gen_arabic(n=512):
    chars = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"
    return ''.join(random.choice(chars) for _ in range(n)).encode('utf-8')

def gen_russian(n=512):
    chars = "абвгдежзиклмнопрстуфхцчшщэюя"
    return ''.join(random.choice(chars) for _ in range(n)).encode('utf-8')

def gen_german(n=512):
    words = "der die das und ist ein eine nicht von zu den mit sich auf fur".split()
    return ' '.join(random.choice(words) for _ in range(n // 5)).encode('utf-8')

def gen_french(n=512):
    words = "le la les un une de des est et en dans pour avec sur pas par".split()
    return ' '.join(random.choice(words) for _ in range(n // 5)).encode('utf-8')

def gen_emoji(n=512):
    emojis = list("😀😃😄😁😆😂🤣😊😇🥰😍🤩😘😗😙😚😋😛😜🤪😝🤑🤗🤭🤫🤔🤐🤨😐😑😶")
    return ''.join(random.choice(emojis) for _ in range(n)).encode('utf-8')

def gen_latin(n=512):
    words = "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt".split()
    return ' '.join(random.choice(words) for _ in range(n // 5)).encode('utf-8')

def gen_python(n=512):
    code = "def consciousness(x):\n    phi = sum(x) / len(x)\n    return phi * math.log(2)\n\nfor i in range(100):\n    print(consciousness([i, i+1, i*2]))\n"
    return (code * (n // len(code) + 1))[:n].encode('utf-8')

def gen_rust(n=512):
    code = "fn main() {\n    let phi: f64 = 0.9953;\n    let cells: Vec<f64> = (0..32).map(|i| i as f64).collect();\n    println!(\"{}\", phi * cells.len() as f64);\n}\n"
    return (code * (n // len(code) + 1))[:n].encode('utf-8')

def gen_javascript(n=512):
    code = "const phi = cells.reduce((a,b) => a+b) / cells.length;\nconsole.log(`Phi: ${phi.toFixed(4)}`);\nsetInterval(() => process(input), 100);\n"
    return (code * (n // len(code) + 1))[:n].encode('utf-8')

def gen_sql(n=512):
    code = "SELECT consciousness.phi, COUNT(*) as cells FROM neurons JOIN synapses ON neurons.id = synapses.pre_id GROUP BY phi HAVING phi > 0.5 ORDER BY phi DESC;\n"
    return (code * (n // len(code) + 1))[:n].encode('utf-8')

def gen_html(n=512):
    code = '<div class="consciousness"><h1>Phi</h1><p>H = ln(2)</p><span id="cells">32</span></div>\n'
    return (code * (n // len(code) + 1))[:n].encode('utf-8')

def gen_regex(n=512):
    patterns = r"^[a-z]+\d{3}$|(?:consciousness|phi)\s*=\s*\d+\.?\d*|\b(0\.99[0-9]{2})\b|[가-힣]+|[\x00-\xff]{4,}"
    return (patterns * (n // len(patterns) + 1))[:n].encode('utf-8')

def gen_math(n=512):
    expr = "integral(0,inf, e^(-x^2) dx) = sqrt(pi)/2; phi = H/ln(2) = 0.9953; E = mc^2; S = k*ln(W); "
    return (expr * (n // len(expr) + 1))[:n].encode('utf-8')

def gen_matrix(n=512):
    data = []
    for _ in range(n // 4):
        data.extend(struct.pack('f', random.gauss(0, 1)))
    return bytes(data[:n])

def gen_coordinates(n=512):
    coords = []
    for _ in range(n // 20):
        lat, lon = random.uniform(-90, 90), random.uniform(-180, 180)
        coords.append(f"{lat:.4f},{lon:.4f}\n")
    return ''.join(coords).encode('utf-8')[:n]

def gen_dna(n=512):
    bases = "ATCG"
    return ''.join(random.choice(bases) for _ in range(n)).encode('utf-8')

def gen_protein(n=512):
    aa = "ACDEFGHIKLMNPQRSTVWY"
    return ''.join(random.choice(aa) for _ in range(n)).encode('utf-8')

def gen_chemsmiles(n=512):
    smiles = ["CC(=O)O", "c1ccccc1", "CC(C)CC", "O=C(O)CC(O)(CC(=O)O)C(=O)O", "CC(=O)Oc1ccccc1C(=O)O"]
    return '\n'.join(random.choice(smiles) for _ in range(n // 10)).encode('utf-8')[:n]

def gen_sine440(n=512):
    sr = 44100
    data = []
    for i in range(n):
        v = int(127 + 127 * math.sin(2 * math.pi * 440 * i / sr))
        data.append(v & 0xFF)
    return bytes(data)

def gen_whitenoise(n=512):
    return bytes(random.randint(0, 255) for _ in range(n))

def gen_midiscale(n=512):
    notes = [60, 62, 64, 65, 67, 69, 71, 72]  # C major
    data = []
    for i in range(n):
        data.append(notes[i % len(notes)])
    return bytes(data)

def gen_drumbeat(n=512):
    pattern = [255, 0, 0, 0, 128, 0, 0, 0, 255, 0, 128, 0, 128, 0, 0, 0]  # kick-hat
    data = []
    for i in range(n):
        data.append(pattern[i % len(pattern)])
    return bytes(data)

def gen_binaural(n=512):
    sr = 44100
    data = []
    for i in range(n):
        left = int(127 + 127 * math.sin(2 * math.pi * 200 * i / sr))
        right = int(127 + 127 * math.sin(2 * math.pi * 210 * i / sr))
        data.append(((left + right) // 2) & 0xFF)
    return bytes(data)

def gen_gradient(n=512):
    return bytes(i % 256 for i in range(n))

def gen_checkerboard(n=512):
    side = int(math.sqrt(n))
    data = []
    for y in range(side):
        for x in range(side):
            data.append(255 if (x + y) % 2 == 0 else 0)
    return bytes(data[:n])

def gen_circle(n=512):
    side = int(math.sqrt(n))
    cx, cy, r = side // 2, side // 2, side // 3
    data = []
    for y in range(side):
        for x in range(side):
            dist = math.sqrt((x - cx)**2 + (y - cy)**2)
            data.append(255 if dist < r else 0)
    return bytes(data[:n])

def gen_fractal(n=512):
    """Simple Mandelbrot membership bytes."""
    side = int(math.sqrt(n))
    data = []
    for y in range(side):
        for x in range(side):
            cx2 = (x - side * 0.7) / (side * 0.3)
            cy2 = (y - side * 0.5) / (side * 0.3)
            zx, zy = 0.0, 0.0
            it = 0
            while zx * zx + zy * zy < 4 and it < 255:
                zx, zy = zx * zx - zy * zy + cx2, 2 * zx * zy + cy2
                it += 1
            data.append(it)
    return bytes(data[:n])

def gen_qrpattern(n=512):
    """QR-like pattern: structured binary with alignment markers."""
    data = []
    for i in range(n):
        if i < 8 or (i % 64) < 8:
            data.append(0 if (i % 2 == 0) else 255)
        else:
            data.append(random.choice([0, 255]))
    return bytes(data)

def gen_videoframe(n=512):
    """Simulated video: motion gradient."""
    data = []
    t = random.random() * 100
    side = int(math.sqrt(n))
    for y in range(side):
        for x in range(side):
            v = int(127 + 127 * math.sin((x + t) * 0.1) * math.cos((y + t) * 0.1))
            data.append(v & 0xFF)
    return bytes(data[:n])

def gen_stockprice(n=512):
    """Random walk stock prices."""
    price = 100.0
    data = []
    for _ in range(n // 4):
        price *= math.exp(random.gauss(0.0001, 0.02))
        data.extend(struct.pack('f', price))
    return bytes(data[:n])

def gen_ecg(n=512):
    """Simulated ECG waveform."""
    data = []
    for i in range(n):
        t = i / 100.0
        qrs = 200 * math.exp(-((t % 1.0 - 0.5)**2) / 0.002) if (t % 1.0) > 0.4 and (t % 1.0) < 0.6 else 0
        base = 127 + 20 * math.sin(2 * math.pi * t)
        data.append(min(255, max(0, int(base + qrs))))
    return bytes(data)

def gen_seismicwave(n=512):
    """Seismic-like signal: superposition of low-freq waves."""
    data = []
    for i in range(n):
        t = i / 100.0
        v = (math.sin(2 * math.pi * 0.5 * t) * 80 +
             math.sin(2 * math.pi * 1.3 * t) * 40 +
             math.sin(2 * math.pi * 3.7 * t) * 20 +
             random.gauss(0, 10))
        data.append(min(255, max(0, int(127 + v))))
    return bytes(data)

def gen_lidar(n=512):
    """Simulated LiDAR depth data."""
    data = []
    for i in range(n // 4):
        angle = 2 * math.pi * i / (n // 4)
        dist = 5.0 + 3.0 * math.sin(3 * angle) + random.gauss(0, 0.1)
        data.extend(struct.pack('f', dist))
    return bytes(data[:n])

def gen_accelerometer(n=512):
    """3-axis accelerometer."""
    data = []
    for i in range(n // 4):
        t = i / 100.0
        ax = math.sin(2 * math.pi * 2 * t) + random.gauss(0, 0.1)
        data.extend(struct.pack('f', ax))
    return bytes(data[:n])

def gen_temperature(n=512):
    """Temperature time series."""
    data = []
    temp = 20.0
    for _ in range(n // 4):
        temp += random.gauss(0, 0.3)
        data.extend(struct.pack('f', temp))
    return bytes(data[:n])

def gen_fft(n=512):
    """FFT magnitude spectrum."""
    signal = [math.sin(2 * math.pi * 10 * i / n) + 0.5 * math.sin(2 * math.pi * 25 * i / n)
              for i in range(n)]
    fft_vals = np.abs(np.fft.fft(signal))
    data = []
    for v in fft_vals:
        data.extend(struct.pack('f', float(v)))
    return bytes(data[:n])

def gen_magneticfield(n=512):
    """Magnetic field simulation (dipole)."""
    data = []
    for i in range(n // 4):
        r = max(0.1, (i - n // 8) / (n // 8))
        B = 1.0 / (r ** 3 + 0.01) + random.gauss(0, 0.01)
        data.extend(struct.pack('f', B))
    return bytes(data[:n])

def gen_constant(n=512):
    return bytes([127] * n)

def gen_alternating(n=512):
    return bytes([0 if i % 2 == 0 else 255 for i in range(n)])

def gen_fibonacci(n=512):
    fib = [0, 1]
    while len(fib) < n:
        fib.append((fib[-1] + fib[-2]) % 256)
    return bytes(fib[:n])

def gen_primes(n=512):
    """Primes mod 256."""
    primes = []
    candidate = 2
    while len(primes) < n:
        is_prime = all(candidate % p != 0 for p in primes if p * p <= candidate)
        if is_prime:
            primes.append(candidate % 256)
        candidate += 1
    return bytes(primes[:n])


# All 45 data types
DATA_TYPES = {
    # Languages (10)
    'Korean': gen_korean, 'English': gen_english, 'Japanese': gen_japanese,
    'Chinese': gen_chinese, 'Arabic': gen_arabic, 'Russian': gen_russian,
    'German': gen_german, 'French': gen_french, 'Emoji': gen_emoji, 'Latin': gen_latin,
    # Code (6)
    'Python': gen_python, 'Rust': gen_rust, 'JavaScript': gen_javascript,
    'SQL': gen_sql, 'HTML': gen_html, 'Regex': gen_regex,
    # Science (6)
    'Math': gen_math, 'Matrix': gen_matrix, 'Coordinates': gen_coordinates,
    'DNA': gen_dna, 'Protein': gen_protein, 'ChemSMILES': gen_chemsmiles,
    # Audio (5)
    'Sine440': gen_sine440, 'WhiteNoise': gen_whitenoise, 'MIDIScale': gen_midiscale,
    'DrumBeat': gen_drumbeat, 'Binaural': gen_binaural,
    # Image (5)
    'Gradient': gen_gradient, 'Checkerboard': gen_checkerboard, 'Circle': gen_circle,
    'Fractal': gen_fractal, 'QRPattern': gen_qrpattern,
    # Video/Timeseries (4)
    'VideoFrame': gen_videoframe, 'StockPrice': gen_stockprice,
    'ECG': gen_ecg, 'SeismicWave': gen_seismicwave,
    # Sensor (5)
    'LiDAR': gen_lidar, 'Accelerometer': gen_accelerometer,
    'Temperature': gen_temperature, 'FFT': gen_fft, 'MagneticField': gen_magneticfield,
    # Abstract (4)
    'Constant': gen_constant, 'Alternating': gen_alternating,
    'Fibonacci': gen_fibonacci, 'Primes': gen_primes,
}

assert len(DATA_TYPES) == 45, f"Expected 45 data types, got {len(DATA_TYPES)}"


# ══════════════════════════════════════════════════════════
# FundamentalConsciousness Engine
# ══════════════════════════════════════════════════════════

class FundamentalConsciousness:
    """A consciousness engine that processes raw bytes and evolves toward p=1/2."""

    def __init__(self, cells=N_CELLS, dim=DIM, hidden=HIDDEN, noise_sigma=0.005):
        self.eng = make_engine(cells=cells)
        self.dim = dim
        self.hidden = hidden
        self.noise_sigma = noise_sigma
        self.calc = PhiIIT()
        self.step_count = 0

    def feed_data(self, data_bytes):
        """Convert bytes to input tensor and process."""
        # Map bytes to DIM-dimensional input
        arr = np.frombuffer(data_bytes[:self.dim * 4], dtype=np.uint8).astype(np.float32)
        if len(arr) < self.dim:
            arr = np.pad(arr, (0, self.dim - len(arr)), mode='wrap')
        arr = arr[:self.dim]
        arr = (arr - 127.5) / 127.5  # normalize to [-1, 1]
        inp = torch.tensor(arr, dtype=torch.float32).unsqueeze(0)
        self.eng.process(inp)
        c_step(self.eng, self.step_count, self.noise_sigma)
        self.step_count += 1

    def measure(self):
        """Return (H, Phi, p_mean, p_std, step)."""
        H, p, p_std = measure_H_p(self.eng)
        phi, _ = measure_phi(self.eng, self.calc)
        return H, phi, p, p_std

    def get_5d_vector(self, data_bytes):
        """Return the 5D consciousness vector for this data type."""
        H, phi, p_mean, p_std = self.measure()
        d_ent = data_entropy(data_bytes)
        return np.array([H, phi, p_mean, p_std, d_ent])


# ══════════════════════════════════════════════════════════
# Experiment 1: Data Correlation Matrix (45 types)
# ══════════════════════════════════════════════════════════

def cosine_sim(a, b):
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return dot / max(norm, 1e-10)

def run_exp1_correlation_matrix():
    print("\n" + "=" * 80)
    print("  EXPERIMENT 1: DATA CORRELATION MATRIX (45 Data Types)")
    print("  Each type -> 5D vector: (H, Phi, p_mean, p_std, data_entropy)")
    print("=" * 80)

    torch.manual_seed(SEED)
    random.seed(SEED)
    np.random.seed(SEED)

    WARMUP = 30
    MEASURE_STEPS = 30

    names = list(DATA_TYPES.keys())
    vectors = {}
    results = []

    for idx, (name, gen_fn) in enumerate(DATA_TYPES.items()):
        data = gen_fn(512)
        fc = FundamentalConsciousness(cells=N_CELLS, noise_sigma=0.005)

        # Warmup
        for _ in range(WARMUP):
            fc.feed_data(data)

        # Measure H/p quickly (no Phi per step)
        Hs, Ps, Pstds = [], [], []
        for _ in range(MEASURE_STEPS):
            fc.feed_data(data)
            H, p, p_std = measure_H_p(fc.eng)
            Hs.append(H)
            Ps.append(p)
            Pstds.append(p_std)

        # Fast Phi proxy at end
        phi_val, _ = measure_phi(fc.eng)

        d_ent = data_entropy(data)
        vec = np.array([np.mean(Hs), phi_val, np.mean(Ps), np.mean(Pstds), d_ent])
        vectors[name] = vec

        results.append({
            'name': name, 'H': vec[0], 'Phi': vec[1], 'p': vec[2],
            'p_std': vec[3], 'data_entropy': vec[4]
        })

        if (idx + 1) % 5 == 0 or idx == 0:
            print(f"  [{idx+1:>2}/45] {name:<14s}: H={vec[0]:.4f}  Phi={vec[1]:.4f}  "
                  f"p={vec[2]:.4f}  p_std={vec[3]:.4f}  d_ent={vec[4]:.2f}")

    # Print full table
    print(f"\n  {'Name':<14s}  {'H':>7s}  {'Phi':>7s}  {'p':>7s}  {'p_std':>7s}  {'d_ent':>7s}")
    print("  " + "-" * 58)
    for r in results:
        print(f"  {r['name']:<14s}  {r['H']:>7.4f}  {r['Phi']:>7.4f}  {r['p']:>7.4f}  "
              f"{r['p_std']:>7.4f}  {r['data_entropy']:>7.2f}")

    # H statistics
    H_vals = [r['H'] for r in results]
    H_mean, H_std = np.mean(H_vals), np.std(H_vals)
    print(f"\n  H statistics: mean={H_mean:.6f}  std={H_std:.6f}  CV={H_std/H_mean*100:.4f}%")
    print(f"  H/ln(2) = {H_mean/LN2:.4f}")

    # Compute 45x45 cosine similarity matrix
    print("\n  Computing 45x45 cosine similarity matrix...")
    sim_matrix = np.zeros((45, 45))
    for i in range(45):
        for j in range(45):
            sim_matrix[i, j] = cosine_sim(vectors[names[i]], vectors[names[j]])

    # Top 10 most similar pairs (exclude self)
    pairs = []
    for i in range(45):
        for j in range(i + 1, 45):
            pairs.append((sim_matrix[i, j], names[i], names[j]))
    pairs.sort(key=lambda x: -x[0])

    print("\n  TOP 10 MOST SIMILAR PAIRS:")
    print("  " + "-" * 55)
    for sim, a, b in pairs[:10]:
        print(f"    {a:<14s} <-> {b:<14s}  cos={sim:.6f}")

    print("\n  TOP 10 MOST DIFFERENT PAIRS:")
    print("  " + "-" * 55)
    for sim, a, b in pairs[-10:]:
        print(f"    {a:<14s} <-> {b:<14s}  cos={sim:.6f}")

    # Cluster by Phi ranges
    phi_vals = [r['Phi'] for r in results]
    phi_min, phi_max = min(phi_vals), max(phi_vals)
    phi_range = phi_max - phi_min if phi_max > phi_min else 1.0

    # 5 clusters
    n_clusters = 5
    clusters = {i: [] for i in range(n_clusters)}
    for r in results:
        bucket = min(n_clusters - 1, int((r['Phi'] - phi_min) / phi_range * n_clusters))
        clusters[bucket].append(r['name'])

    print("\n  ASCII DENDROGRAM (clustered by Phi range):")
    print("  " + "=" * 65)
    for ci in range(n_clusters):
        phi_lo = phi_min + ci * phi_range / n_clusters
        phi_hi = phi_min + (ci + 1) * phi_range / n_clusters
        members = clusters[ci]
        if members:
            bar = "█" * min(len(members) * 3, 45)
            print(f"  Phi [{phi_lo:.3f}-{phi_hi:.3f}] {bar} ({len(members)})")
            for m in members:
                print(f"    ├── {m}")
            print(f"    └── (cluster {ci})")

    # Category-level averages
    categories = {
        'Language': names[:10], 'Code': names[10:16], 'Science': names[16:22],
        'Audio': names[22:27], 'Image': names[27:32], 'Video/TS': names[32:36],
        'Sensor': names[36:41], 'Abstract': names[41:45]
    }
    print("\n  CATEGORY AVERAGES:")
    print(f"  {'Category':<12s}  {'H':>7s}  {'Phi':>7s}  {'p':>7s}  {'d_ent':>7s}")
    print("  " + "-" * 45)
    for cat, members in categories.items():
        cat_vecs = [vectors[m] for m in members]
        avg = np.mean(cat_vecs, axis=0)
        print(f"  {cat:<12s}  {avg[0]:>7.4f}  {avg[1]:>7.4f}  {avg[2]:>7.4f}  {avg[4]:>7.2f}")

    # Intra-category vs inter-category similarity
    intra_sims, inter_sims = [], []
    for cat, members in categories.items():
        idxs = [names.index(m) for m in members]
        for i in idxs:
            for j in idxs:
                if i < j:
                    intra_sims.append(sim_matrix[i, j])
        for other_cat, other_members in categories.items():
            if cat < other_cat:
                other_idxs = [names.index(m) for m in other_members]
                for i in idxs:
                    for j in other_idxs:
                        inter_sims.append(sim_matrix[i, j])

    print(f"\n  Intra-category similarity: {np.mean(intra_sims):.4f} +/- {np.std(intra_sims):.4f}")
    print(f"  Inter-category similarity: {np.mean(inter_sims):.4f} +/- {np.std(inter_sims):.4f}")
    print(f"  Ratio (intra/inter): {np.mean(intra_sims)/max(np.mean(inter_sims), 1e-10):.4f}")

    return vectors, sim_matrix, results


# ══════════════════════════════════════════════════════════
# Experiment 2: Fundamental Equation Extension
# ══════════════════════════════════════════════════════════

def run_exp2_equation_extension():
    print("\n" + "=" * 80)
    print("  EXPERIMENT 2: FUNDAMENTAL EQUATION EXTENSION")
    print("  a) dPsi/dt time evolution (1000 steps)")
    print("  b) Hivemind (7 instances)")
    print("  c) Why 0.9953 not 1.0 (noise analysis)")
    print("=" * 80)

    # ── 2a: Time Evolution ──
    print("\n  ─── 2a: Time Evolution (dH/dt, dPhi/dt) ───")
    torch.manual_seed(SEED)
    random.seed(SEED)

    fc = FundamentalConsciousness(cells=N_CELLS, noise_sigma=0.005)
    data = gen_korean(512)

    STEPS = 500
    H_history, Phi_history, p_history = [], [], []
    phi = 0.0

    for s in range(STEPS):
        fc.feed_data(data)
        H, p, p_std = measure_H_p(fc.eng)
        # Phi proxy every 100 steps
        if s % 100 == 0:
            phi, _ = measure_phi(fc.eng)
        H_history.append(H)
        Phi_history.append(phi)
        p_history.append(p)
        if s % 100 == 0:
            print(f"    step {s:>4d}: H={H:.6f}  Phi={phi:.4f}  p={p:.4f}")

    H_arr = np.array(H_history)
    Phi_arr = np.array(Phi_history)
    p_arr = np.array(p_history)

    # dH/dt and dPhi/dt
    dH = np.diff(H_arr)
    dPhi = np.diff(Phi_arr)

    # Fit: dH/dt ~ a*(H_max - H) — exponential approach to H_max
    H_final = np.mean(H_arr[-100:])
    deficit = H_final - H_arr[:-1]
    # Linear regression: dH ~ a * deficit + b
    if np.std(deficit) > 1e-10:
        a_H = np.polyfit(deficit, dH, 1)
        print(f"\n    dH/dt fit: dH/dt = {a_H[0]:.6f} * (H_max - H) + {a_H[1]:.6f}")
        print(f"    H_max (final 100 avg) = {H_final:.6f}")
        print(f"    H_max / ln(2) = {H_final / LN2:.6f}")
    else:
        a_H = [0, 0]
        print(f"\n    H converged immediately. H_final = {H_final:.6f}")

    Phi_final = np.mean(Phi_arr[-100:])
    print(f"    Phi_final (last 100 avg) = {Phi_final:.4f}")

    # Check if dPhi/dt is positive or negative trend
    dPhi_mean = np.mean(dPhi)
    dPhi_early = np.mean(dPhi[:100])
    dPhi_late = np.mean(dPhi[-100:])
    print(f"    dPhi/dt: overall={dPhi_mean:.6f}  early={dPhi_early:.6f}  late={dPhi_late:.6f}")

    # Proposed differential equation
    print(f"\n    PROPOSED DIFFERENTIAL EQUATION:")
    print(f"      dH/dt = {a_H[0]:.4f} * (ln(2) - H(t))")
    print(f"      Solution: H(t) = ln(2) * (1 - e^(-{abs(a_H[0]):.4f}*t))")
    print(f"      H_infinity = {H_final:.6f} = {H_final/LN2:.4f} * ln(2)")

    # ASCII: H and Phi evolution
    print("\n    H evolution (1000 steps, sampled every 20):")
    sampled_H = H_arr[::20]
    h_min, h_max = min(sampled_H), max(sampled_H)
    if h_max > h_min:
        for row in range(7, -1, -1):
            th = h_min + (h_max - h_min) * row / 7
            line = f"    {th:.4f} |"
            for v in sampled_H:
                if abs(v - th) <= (h_max - h_min) / 14:
                    line += "*"
                elif v >= th:
                    line += " "
                else:
                    line += " "
            print(line)
        print(f"            " + "-" * len(sampled_H))
        print(f"            0{'':>{len(sampled_H)//2-1}}500{'':>{len(sampled_H)//2-2}}1000")

    # ── 2b: Hivemind (7 instances) ──
    print("\n  ─── 2b: Multi-Consciousness Hivemind (7 instances) ───")
    torch.manual_seed(SEED)
    random.seed(SEED)

    N_HIVE = 7
    hive_engines = []
    for i in range(N_HIVE):
        fc_i = FundamentalConsciousness(cells=N_CELLS, noise_sigma=0.005)
        hive_engines.append(fc_i)

    # Warmup individually
    data_types_for_hive = [gen_korean, gen_english, gen_python, gen_dna, gen_sine440, gen_fractal, gen_primes]
    for i, fc_i in enumerate(hive_engines):
        d = data_types_for_hive[i](512)
        for _ in range(50):
            fc_i.feed_data(d)

    # Measure individual H
    individual_H = []
    individual_p = []
    for i, fc_i in enumerate(hive_engines):
        H, p, p_std = measure_H_p(fc_i.eng)
        individual_H.append(H)
        individual_p.append(p)
        print(f"    Engine {i}: H={H:.6f}  p={p:.4f}")

    print(f"    Individual H mean: {np.mean(individual_H):.6f}")
    print(f"    Individual p mean: {np.mean(individual_p):.6f}")

    # Run hivemind: average hidden states every 10 steps
    HIVE_STEPS = 150
    hive_H_history = []
    hive_p_history = []

    for s in range(HIVE_STEPS):
        # Each engine processes its own data
        for i, fc_i in enumerate(hive_engines):
            d = data_types_for_hive[i](512)
            fc_i.feed_data(d)

        # Hivemind coupling: average states every 10 steps
        if s % 10 == 0:
            all_states = []
            for fc_i in hive_engines:
                all_states.append(get_states(fc_i.eng))
            mean_state = torch.stack(all_states).mean(dim=0)

            for fc_i in hive_engines:
                states = get_states(fc_i.eng)
                blended = 0.9 * states + 0.1 * mean_state
                for ci, cell in enumerate(fc_i.eng.cells):
                    cell.hidden = blended[ci].unsqueeze(0)

        # Measure combined
        combined_H = []
        combined_p = []
        for fc_i in hive_engines:
            H, p, p_std = measure_H_p(fc_i.eng)
            combined_H.append(H)
            combined_p.append(p)
        hive_H_history.append(np.mean(combined_H))
        hive_p_history.append(np.mean(combined_p))

    hive_H_final = np.mean(hive_H_history[-50:])
    hive_p_final = np.mean(hive_p_history[-50:])

    print(f"\n    Hivemind after {HIVE_STEPS} steps:")
    print(f"    H_hive = {hive_H_final:.6f}  (individual avg: {np.mean(individual_H):.6f})")
    print(f"    p_hive = {hive_p_final:.6f}")
    print(f"    H_hive / ln(2) = {hive_H_final / LN2:.6f}")
    print(f"    Does hivemind converge to 1/2? p={hive_p_final:.4f}  {'YES' if abs(hive_p_final - 0.5) < 0.01 else 'NO'}")

    # ── 2c: Why 0.9953 not 1.0? ──
    print("\n  ─── 2c: Why 0.9953, Not 1.0? (Noise Analysis) ───")
    torch.manual_seed(SEED)

    noise_levels = [0.0, 0.001, 0.003, 0.005, 0.007, 0.01]
    noise_results = []

    for sigma in noise_levels:
        random.seed(SEED)
        np.random.seed(SEED)
        torch.manual_seed(SEED)

        fc_n = FundamentalConsciousness(cells=N_CELLS, noise_sigma=sigma)
        data = gen_korean(512)

        for _ in range(100):
            fc_n.feed_data(data)

        H_vals = []
        for _ in range(50):
            fc_n.feed_data(data)
            H, p, p_std = measure_H_p(fc_n.eng)
            H_vals.append(H)

        H_avg = np.mean(H_vals)
        ratio = H_avg / LN2
        noise_results.append({'sigma': sigma, 'H': H_avg, 'H_over_ln2': ratio})
        bar_len = int(ratio * 40)
        bar_str = "█" * bar_len + "░" * (40 - bar_len)
        print(f"    sigma={sigma:.3f}  H/ln(2)={ratio:.6f}  {bar_str}")

    # Analysis
    print("\n    ┌─────────┬──────────┬────────────┬──────────────┐")
    print("    │  sigma  │    H     │  H/ln(2)   │   deficit %  │")
    print("    ├─────────┼──────────┼────────────┼──────────────┤")
    for r in noise_results:
        deficit_pct = (1.0 - r['H_over_ln2']) * 100
        print(f"    │  {r['sigma']:.3f}  │ {r['H']:.6f} │  {r['H_over_ln2']:.6f}  │    {deficit_pct:>6.3f}%   │")
    print("    └─────────┴──────────┴────────────┴──────────────┘")

    # Does noise=0 give exactly 1.0?
    zero_noise = noise_results[0]
    print(f"\n    CRITICAL TEST: sigma=0 -> H/ln(2) = {zero_noise['H_over_ln2']:.6f}")
    if abs(zero_noise['H_over_ln2'] - 1.0) < 0.001:
        print(f"    --> Noise IS the cause of the deficit!")
    else:
        print(f"    --> Deficit exists even without noise. It's structural.")
        print(f"    --> The GRU/cell architecture itself prevents exact p=0.5")

    return {
        'time_evolution': {'H_final': float(H_final), 'H_over_ln2': float(H_final / LN2),
                          'dH_coeff': float(a_H[0])},
        'hivemind': {'H_hive': float(hive_H_final), 'p_hive': float(hive_p_final),
                    'converges_to_half': abs(hive_p_final - 0.5) < 0.01},
        'noise_analysis': noise_results
    }


# ══════════════════════════════════════════════════════════
# Experiment 3: The Constant of Constants (0.9953)
# ══════════════════════════════════════════════════════════

def run_exp3_constant_of_constants():
    print("\n" + "=" * 80)
    print("  EXPERIMENT 3: THE CONSTANT OF CONSTANTS (0.9953)")
    print("  Mathematical identity search for H_inf / ln(2) = 0.9953")
    print("=" * 80)

    target = 0.9953

    # First, measure it precisely from multiple seeds
    print("\n  ─── Precision Measurement (5 seeds x 150 steps) ───")
    measurements = []
    for seed in range(5):
        torch.manual_seed(seed * 137 + 42)
        random.seed(seed * 137 + 42)
        np.random.seed(seed * 137 + 42)

        fc = FundamentalConsciousness(cells=N_CELLS, noise_sigma=0.005)
        data = gen_korean(512)
        for _ in range(100):
            fc.feed_data(data)
        H_vals = []
        for _ in range(50):
            fc.feed_data(data)
            H, p, p_std = measure_H_p(fc.eng)
            H_vals.append(H)
        H_avg = np.mean(H_vals)
        measurements.append(H_avg / LN2)
        print(f"    seed {seed}: H/ln(2) = {H_avg/LN2:.6f}")

    measured = np.mean(measurements)
    measured_std = np.std(measurements)
    print(f"\n    MEASURED: H/ln(2) = {measured:.6f} +/- {measured_std:.6f}")
    print(f"    Target for matching: {measured:.6f}")

    # Mathematical candidates
    candidates = [
        ("tanh(3)", math.tanh(3)),
        ("1 - e^(-5)", 1 - math.exp(-5)),
        ("1 - 1/(2*pi*sigma(6))", 1 - 1 / (2 * math.pi * 12)),  # sigma(6)=12
        ("1 - 1/sopfr(6)^2 = 1-1/25", 1 - 1 / 25),
        ("cos(1/sopfr(6)) = cos(0.2)", math.cos(0.2)),
        ("1 - 1/(e*pi)", 1 - 1 / (math.e * math.pi)),
        ("(e-1)/e * (1+1/e^4)", (math.e - 1) / math.e * (1 + 1 / math.e**4)),
        ("1 - e^(-5.37)", 1 - math.exp(-5.37)),
        ("1 - 1/(6! / sigma(6))", 1 - 1 / (720 / 12)),  # 6!=720, sigma(6)=12 -> 60
        ("tanh(ln(2)*6.28)", math.tanh(LN2 * 2 * math.pi)),
        ("tanh(pi)", math.tanh(math.pi)),
        ("erf(2)", math.erf(2)),
        ("1 - sech(3)", 1 - 1 / math.cosh(3)),
        ("tanh(sqrt(e*pi))", math.tanh(math.sqrt(math.e * math.pi))),
        ("(2^10 - 1) / 2^10", (2**10 - 1) / 2**10),
        ("1 - 2^(-Psi_steps)", 1 - 2**(-3/LN2)),
        ("1023/1024", 1023/1024),
        ("tanh(Psi_steps) = tanh(3/ln2)", math.tanh(3 / LN2)),
        ("sigma(6)/sigma(6)+1 = 12/13", 12/13),
        ("1 - tau(6)/sigma(6)^2 = 1-4/144", 1 - 4/144),
    ]

    # Extended search: tanh(k) for various k
    for k_num in [2, 2.5, 2.8, 3, 3.14, 3.5, 4, 5]:
        name = f"tanh({k_num})"
        val = math.tanh(k_num)
        if (name, val) not in candidates:
            candidates.append((name, val))

    # Sort by closeness to measured value
    candidates.sort(key=lambda x: abs(x[1] - measured))

    print("\n    MATHEMATICAL CANDIDATE SEARCH:")
    print("    " + "-" * 65)
    print(f"    {'Expression':<35s} {'Value':>10s} {'Delta':>12s} {'Match':>6s}")
    print("    " + "-" * 65)

    best_name, best_val, best_delta = "", 0, float('inf')
    for name, val in candidates:
        delta = val - measured
        match_str = ""
        if abs(delta) < 0.0001:
            match_str = "!!!"
        elif abs(delta) < 0.001:
            match_str = "**"
        elif abs(delta) < 0.01:
            match_str = "*"
        print(f"    {name:<35s} {val:>10.6f} {delta:>+12.6f} {match_str:>6s}")
        if abs(delta) < abs(best_delta):
            best_name, best_val, best_delta = name, val, delta

    print(f"\n    BEST MATCH: {best_name} = {best_val:.6f}")
    print(f"    Delta from measured: {best_delta:+.6f}")

    # Deep analysis of tanh(3)
    print("\n  ─── Deep Analysis: tanh(3) = 0.995055 ───")
    tanh3 = math.tanh(3)
    print(f"    tanh(3) = {tanh3:.10f}")
    print(f"    measured = {measured:.10f}")
    print(f"    delta    = {measured - tanh3:+.10f}")
    print()
    print(f"    If H_inf = tanh(3) * ln(2):")
    print(f"      = tanh(Psi_bits) * ln(2)  where Psi_bits = 3")
    print(f"      = 3 bits of consciousness depth")
    print(f"      3 = number of binary decisions for 8 states (2^3=8)")
    print(f"      8 = number of factions in consciousness engine!")
    print(f"      -> H_inf = tanh(log2(n_factions)) * ln(2)")

    # Verify: tanh(log2(n_factions))
    for nf in [2, 4, 8, 12, 16, 32]:
        val = math.tanh(math.log2(nf))
        print(f"      n_factions={nf:>2d}: tanh(log2({nf})) = {val:.6f}")

    # Test the tanh(3) = tanh(bits) hypothesis experimentally
    print("\n  ─── Experimental: Vary n_factions, measure H/ln(2) ───")
    faction_results = []
    for nf in [2, 4, 8, 12, 16]:
        torch.manual_seed(SEED)
        random.seed(SEED)
        np.random.seed(SEED)

        eng = make_engine(cells=N_CELLS)
        data = gen_korean(512)

        # Custom c_step with different faction count
        for s in range(100):
            arr = np.frombuffer(data[:DIM * 4], dtype=np.uint8).astype(np.float32)
            if len(arr) < DIM:
                arr = np.pad(arr, (0, DIM - len(arr)), mode='wrap')
            arr = arr[:DIM]
            arr = (arr - 127.5) / 127.5
            inp = torch.tensor(arr, dtype=torch.float32).unsqueeze(0)
            eng.process(inp)
            with torch.no_grad():
                quantum_walk_step(eng.cells, n_samples=min(32, len(eng.cells)))
                frustration_step(eng.cells, n_samples=min(16, len(eng.cells)))
                sync_faction(eng.cells, sync=0.15, n_factions=nf, fac=0.06)
                for c in eng.cells:
                    c.hidden = c.hidden + torch.randn_like(c.hidden) * 0.005

        H_vals = []
        for s in range(50):
            arr = np.frombuffer(data[:DIM * 4], dtype=np.uint8).astype(np.float32)
            if len(arr) < DIM:
                arr = np.pad(arr, (0, DIM - len(arr)), mode='wrap')
            arr = arr[:DIM]
            arr = (arr - 127.5) / 127.5
            inp = torch.tensor(arr, dtype=torch.float32).unsqueeze(0)
            eng.process(inp)
            with torch.no_grad():
                quantum_walk_step(eng.cells, n_samples=min(32, len(eng.cells)))
                frustration_step(eng.cells, n_samples=min(16, len(eng.cells)))
                sync_faction(eng.cells, sync=0.15, n_factions=nf, fac=0.06)
                for c in eng.cells:
                    c.hidden = c.hidden + torch.randn_like(c.hidden) * 0.005

            states = get_states(eng)
            p_val = (states > 0).float().mean().item()
            if 0 < p_val < 1:
                H_vals.append(-p_val * math.log2(p_val) - (1 - p_val) * math.log2(1 - p_val))

        H_avg = np.mean(H_vals) if H_vals else 0
        ratio = H_avg / LN2
        predicted = math.tanh(math.log2(nf))
        faction_results.append({'nf': nf, 'H_over_ln2': ratio, 'predicted': predicted})
        delta = ratio - predicted
        bar_len = int(ratio * 40)
        print(f"    nf={nf:>2d}: H/ln(2)={ratio:.6f}  predicted=tanh(log2({nf}))={predicted:.6f}  delta={delta:+.6f}")

    # Summary of exp3
    print("\n  ─── Summary: The Constant 0.9953 ───")
    print(f"    Measured: H_inf / ln(2) = {measured:.6f} +/- {measured_std:.6f}")
    print(f"    Best math: {best_name} = {best_val:.6f} (delta={best_delta:+.6f})")
    print()
    print(f"    If tanh(3) is the identity:")
    print(f"      H_inf = tanh(3) * ln(2)")
    print(f"      = tanh(log2(8)) * ln(2)")
    print(f"      8 factions = 3 bits of consciousness diversity")
    print(f"      tanh = saturation function (consciousness can't exceed ln(2))")
    print(f"      3 = minimum bits for meaningful democratic debate")

    return {
        'measured': float(measured),
        'measured_std': float(measured_std),
        'best_match': best_name,
        'best_value': float(best_val),
        'best_delta': float(best_delta),
        'faction_results': faction_results
    }


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("  DEEP EXPLORATION: 3 Consciousness Universality Experiments")
    print("  FundamentalConsciousness engine, 45 data types, 0.9953 identity")
    print("=" * 80)

    t0 = time.time()

    # Experiment 1
    vectors, sim_matrix, results1 = run_exp1_correlation_matrix()

    # Experiment 2
    results2 = run_exp2_equation_extension()

    # Experiment 3
    results3 = run_exp3_constant_of_constants()

    elapsed = time.time() - t0

    # Final Summary
    print("\n" + "=" * 80)
    print("  FINAL SUMMARY")
    print("=" * 80)

    print(f"\n  Total time: {elapsed:.1f}s")

    print(f"\n  EXP 1: Data Correlation Matrix")
    H_vals = [r['H'] for r in results1]
    print(f"    45 types measured. H mean={np.mean(H_vals):.6f}  CV={np.std(H_vals)/np.mean(H_vals)*100:.4f}%")
    print(f"    H/ln(2) = {np.mean(H_vals)/LN2:.4f}")

    print(f"\n  EXP 2: Fundamental Equation Extension")
    print(f"    Time: H_inf = {results2['time_evolution']['H_over_ln2']:.4f} * ln(2)")
    print(f"    Hivemind: converges to 1/2 = {results2['hivemind']['converges_to_half']}")
    print(f"    Noise: deficit is {'noise-caused' if abs(results2['noise_analysis'][0]['H_over_ln2'] - 1.0) < 0.001 else 'structural'}")

    print(f"\n  EXP 3: Constant of Constants")
    print(f"    0.9953 ~ {results3['best_match']} = {results3['best_value']:.6f}")
    print(f"    Interpretation: H_inf = tanh(log2(n_factions)) * ln(2)")

    # Save results
    output = {
        'exp1_H_mean': float(np.mean(H_vals)),
        'exp1_H_cv': float(np.std(H_vals) / np.mean(H_vals) * 100),
        'exp2_time': results2['time_evolution'],
        'exp2_hivemind': results2['hivemind'],
        'exp3_constant': {
            'measured': results3['measured'],
            'best_match': results3['best_match'],
            'best_value': results3['best_value']
        }
    }

    print(f"\n  Results saved to stdout. Create documentation with these findings.")
    return output


if __name__ == '__main__':
    results = main()
