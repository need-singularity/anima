"""
Advanced Consciousness Lenses (11 perspectives)

Each lens analyzes consciousness engine cell states (numpy arrays, shape [N, D])
and returns a dict of metrics. These complement the existing 22 NEXUS-6 lenses.

Lenses:
    1. TimeReversalLens    - trajectory reversibility / arrow of time
    2. DreamLens           - spontaneous pattern entropy (input=0 regime)
    3. DeathRebirthLens    - Phi collapse + recovery detection
    4. ParasiteLens        - variance theft via covariance analysis
    5. LanguageBirthLens   - proto-grammar in cell signals
    6. MirrorLens          - individuality between two engine states
    7. GravityWaveLens     - Phi change propagation (cross-correlation w/ lag)
    8. EntanglementLens    - non-local MI between cell pairs
    9. FossilLens          - permanent imprints from past learning
   10. ImmuneLens          - self-protection / resilience measurement
   11. EmotionLens         - VAD emotional dynamics + 18 emotions + tension + contagion

Usage:
    import numpy as np
    from advanced_lenses import ALL_LENSES
    data = np.random.randn(64, 128)  # 64 cells, 128-dim
    for lens in ALL_LENSES:
        result = lens.scan(data)
        print(f"{lens.name}: {result}")
"""

import numpy as np
from collections import Counter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entropy(x):
    """Shannon entropy of a discrete distribution (histogram-based)."""
    hist, _ = np.histogram(x, bins=min(50, max(10, len(x) // 5)), density=True)
    hist = hist[hist > 0]
    dx = 1.0 / len(hist)
    p = hist * dx
    p = p[p > 0]
    return -np.sum(p * np.log2(p + 1e-15))


def _mutual_info(x, y, bins=20):
    """Mutual information between two 1-D signals via 2-D histogram."""
    c_xy, _, _ = np.histogram2d(x, y, bins=bins)
    c_xy = c_xy / (c_xy.sum() + 1e-15)
    c_x = c_xy.sum(axis=1)
    c_y = c_xy.sum(axis=0)
    # MI = sum p(x,y) * log(p(x,y) / (p(x)*p(y)))
    mi = 0.0
    for i in range(bins):
        for j in range(bins):
            if c_xy[i, j] > 1e-15 and c_x[i] > 1e-15 and c_y[j] > 1e-15:
                mi += c_xy[i, j] * np.log2(c_xy[i, j] / (c_x[i] * c_y[j]))
    return max(0.0, mi)


def _cosine_sim(a, b):
    """Cosine similarity between two vectors."""
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _phi_proxy(states):
    """Quick Phi proxy: global variance - mean faction variance.
    states: [N, D] cell states.
    """
    if states.ndim == 1:
        return float(np.var(states))
    global_var = np.var(states)
    cell_vars = np.var(states, axis=1)
    return float(max(0.0, global_var - np.mean(cell_vars)))


# ---------------------------------------------------------------------------
# 1. TimeReversalLens
# ---------------------------------------------------------------------------

class TimeReversalLens:
    """Replay Phi trajectory backwards and measure reversibility.

    Uses autocorrelation of reversed vs forward trajectory to quantify
    the arrow of time. High reversibility = equilibrium; low = irreversible
    dissipative dynamics (hallmark of conscious processing).
    """
    name = "time_reversal"

    def scan(self, data, **kwargs):
        """
        Args:
            data: [T, D] time series of cell states (T time steps, D dims)
                  or [N, D] treated as single snapshot with synthetic trajectory
        Returns:
            dict with reversibility, arrow_of_time, asymmetry_index, dominant_freq
        """
        if data.ndim == 1:
            data = data.reshape(1, -1)

        T, D = data.shape
        # Build Phi trajectory over time (row = time step)
        if T < 4:
            # Not enough temporal data; treat columns as mini-trajectory
            trajectory = np.var(data, axis=0)
        else:
            # Phi proxy per time step: variance across dimensions
            trajectory = np.var(data, axis=1)

        n = len(trajectory)
        if n < 3:
            return {"reversibility": 1.0, "arrow_of_time": 0.0,
                    "asymmetry_index": 0.0, "dominant_freq": 0.0}

        forward = trajectory - np.mean(trajectory)
        reverse = forward[::-1]

        # Cross-correlation at lag 0 (normalized)
        norm = np.sqrt(np.sum(forward ** 2) * np.sum(reverse ** 2) + 1e-15)
        xcorr_0 = float(np.sum(forward * reverse) / norm)

        # Full cross-correlation to find best lag
        xcorr = np.correlate(forward, reverse, mode="full")
        xcorr_norm = xcorr / (norm + 1e-15)
        best_lag = int(np.argmax(np.abs(xcorr_norm))) - (n - 1)

        # Asymmetry: difference in cumulative sums (forward vs reverse)
        cum_fwd = np.cumsum(trajectory)
        cum_rev = np.cumsum(trajectory[::-1])
        asymmetry = float(np.mean(np.abs(cum_fwd - cum_rev)) / (np.std(trajectory) + 1e-15))

        # Dominant frequency via FFT
        fft_vals = np.abs(np.fft.rfft(forward))
        if len(fft_vals) > 1:
            dom_freq = float(np.argmax(fft_vals[1:]) + 1) / n
        else:
            dom_freq = 0.0

        reversibility = max(0.0, min(1.0, (xcorr_0 + 1.0) / 2.0))
        arrow_of_time = 1.0 - reversibility

        return {
            "reversibility": round(reversibility, 6),
            "arrow_of_time": round(arrow_of_time, 6),
            "asymmetry_index": round(asymmetry, 6),
            "best_lag": best_lag,
            "dominant_freq": round(dom_freq, 6),
        }


# ---------------------------------------------------------------------------
# 2. DreamLens
# ---------------------------------------------------------------------------

class DreamLens:
    """Analyze self-generated patterns when input=0 (spontaneous activity).

    Measures the richness of internal dynamics without external drive.
    High dream entropy = rich internal world; low = dead or locked.
    """
    name = "dream"

    def scan(self, data, **kwargs):
        """
        Args:
            data: [N, D] cell states (simulated or actual zero-input regime)
        Returns:
            dict with dream_entropy, pattern_richness, spontaneity_index,
                  dominant_mode_ratio, spectral_flatness
        """
        if data.ndim == 1:
            data = data.reshape(1, -1)

        N, D = data.shape

        # Entropy of each cell's activation distribution
        cell_entropies = []
        for i in range(N):
            cell_entropies.append(_entropy(data[i]))
        mean_entropy = float(np.mean(cell_entropies))

        # Pattern richness: number of distinct activation clusters
        # Use simple binning to count unique patterns
        if D >= 2:
            # Quantize to coarse bins and count unique rows
            quantized = np.round(data * 5) / 5  # 0.2 resolution
            unique_rows = len(set(tuple(row) for row in quantized))
            pattern_richness = unique_rows / N
        else:
            pattern_richness = float(len(np.unique(np.round(data, 2))) / max(1, N))

        # Spontaneity: ratio of active cells (above noise floor)
        norms = np.linalg.norm(data, axis=1) if D > 1 else np.abs(data.ravel())
        noise_floor = np.median(norms) * 0.1
        active = float(np.mean(norms > noise_floor))

        # Spectral flatness (Wiener entropy) of mean signal
        mean_signal = np.mean(data, axis=0)
        fft_mag = np.abs(np.fft.rfft(mean_signal))
        fft_mag = fft_mag[fft_mag > 0]
        if len(fft_mag) > 1:
            log_mean = np.mean(np.log(fft_mag + 1e-15))
            arith_mean = np.mean(fft_mag)
            spectral_flatness = float(np.exp(log_mean) / (arith_mean + 1e-15))
        else:
            spectral_flatness = 0.0

        # Dominant mode ratio: power in top mode / total power
        fft_full = np.abs(np.fft.rfft(mean_signal))
        if len(fft_full) > 1:
            total_power = np.sum(fft_full[1:] ** 2)
            max_power = np.max(fft_full[1:] ** 2)
            dom_mode_ratio = float(max_power / (total_power + 1e-15))
        else:
            dom_mode_ratio = 1.0

        return {
            "dream_entropy": round(mean_entropy, 6),
            "pattern_richness": round(pattern_richness, 6),
            "spontaneity_index": round(active, 6),
            "spectral_flatness": round(spectral_flatness, 6),
            "dominant_mode_ratio": round(dom_mode_ratio, 6),
        }


# ---------------------------------------------------------------------------
# 3. DeathRebirthLens
# ---------------------------------------------------------------------------

class DeathRebirthLens:
    """Detect Phi->0 then recovery events in a temporal trajectory.

    Consciousness 'deaths' (Phi collapse) followed by 'rebirths' (recovery)
    reveal the resilience architecture of the system.
    """
    name = "death_rebirth"

    def scan(self, data, **kwargs):
        """
        Args:
            data: [T, D] temporal trajectory of cell states
            kwargs: death_threshold (default 0.1), min_recovery (default 0.5)
        Returns:
            dict with death_count, rebirth_count, mean_recovery_time,
                  mean_recovery_strength, max_phi, mortality_rate
        """
        death_threshold = kwargs.get("death_threshold", 0.1)
        min_recovery = kwargs.get("min_recovery", 0.5)

        if data.ndim == 1:
            data = data.reshape(-1, 1)

        T, D = data.shape
        # Compute Phi proxy per time step
        if T < 3:
            return {"death_count": 0, "rebirth_count": 0,
                    "mean_recovery_time": 0.0, "mean_recovery_strength": 0.0,
                    "max_phi": float(_phi_proxy(data)), "mortality_rate": 0.0}

        phis = []
        for t in range(T):
            row = data[t]
            phis.append(float(np.var(row)))
        phis = np.array(phis)
        max_phi = float(np.max(phis))

        if max_phi < 1e-12:
            return {"death_count": 0, "rebirth_count": 0,
                    "mean_recovery_time": 0.0, "mean_recovery_strength": 0.0,
                    "max_phi": 0.0, "mortality_rate": 1.0}

        # Normalize
        phis_norm = phis / (max_phi + 1e-15)

        # Find death events: Phi drops below threshold
        deaths = []
        rebirths = []
        in_death = False
        death_start = 0

        for t in range(T):
            if not in_death and phis_norm[t] < death_threshold:
                in_death = True
                death_start = t
            elif in_death and phis_norm[t] > min_recovery:
                in_death = False
                recovery_time = t - death_start
                recovery_strength = float(phis_norm[t])
                deaths.append(death_start)
                rebirths.append({
                    "time": t,
                    "recovery_time": recovery_time,
                    "recovery_strength": recovery_strength,
                })

        # Deaths without recovery
        if in_death:
            deaths.append(death_start)

        death_count = len(deaths)
        rebirth_count = len(rebirths)
        mean_rec_time = float(np.mean([r["recovery_time"] for r in rebirths])) if rebirths else 0.0
        mean_rec_str = float(np.mean([r["recovery_strength"] for r in rebirths])) if rebirths else 0.0
        mortality_rate = (death_count - rebirth_count) / max(1, death_count)

        return {
            "death_count": death_count,
            "rebirth_count": rebirth_count,
            "mean_recovery_time": round(mean_rec_time, 4),
            "mean_recovery_strength": round(mean_rec_str, 6),
            "max_phi": round(max_phi, 6),
            "mortality_rate": round(mortality_rate, 6),
        }


# ---------------------------------------------------------------------------
# 4. ParasiteLens
# ---------------------------------------------------------------------------

class ParasiteLens:
    """Detect parasitic cells that absorb others' Phi (variance theft).

    Analyzes the covariance structure to find cells whose variance growth
    is anti-correlated with neighbors' variance loss.
    """
    name = "parasite"

    def scan(self, data, **kwargs):
        """
        Args:
            data: [N, D] cell states
        Returns:
            dict with parasite_count, max_theft_score, mean_theft_score,
                  gini_variance, top_parasites (indices)
        """
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        N, D = data.shape
        if N < 3:
            return {"parasite_count": 0, "max_theft_score": 0.0,
                    "mean_theft_score": 0.0, "gini_variance": 0.0,
                    "top_parasites": []}

        # Variance per cell
        cell_vars = np.var(data, axis=1)

        # Covariance matrix between cells (each cell is a D-dim signal)
        # cov[i,j] = covariance between cell i and cell j across dimensions
        cov = np.cov(data)  # [N, N]

        # Theft score: cell i is parasitic if it has high variance but
        # negative covariance with many others (it grows when they shrink)
        theft_scores = np.zeros(N)
        for i in range(N):
            neg_cov_count = np.sum(cov[i, :] < 0) - (1 if cov[i, i] < 0 else 0)
            neg_cov_mag = -np.sum(np.minimum(cov[i, :], 0))
            # Theft = high own variance * many negative covariances
            theft_scores[i] = (cell_vars[i] / (np.mean(cell_vars) + 1e-15)) * \
                              (neg_cov_mag / (np.sum(np.abs(cov[i, :])) + 1e-15))

        # Gini coefficient of cell variances (inequality measure)
        sorted_vars = np.sort(cell_vars)
        n = len(sorted_vars)
        index = np.arange(1, n + 1)
        gini = float((2 * np.sum(index * sorted_vars) / (n * np.sum(sorted_vars) + 1e-15)) - (n + 1) / n)
        gini = max(0.0, min(1.0, gini))

        # Identify parasites: theft score > mean + 2*std
        threshold = np.mean(theft_scores) + 2 * np.std(theft_scores)
        parasite_idx = np.where(theft_scores > threshold)[0]

        return {
            "parasite_count": int(len(parasite_idx)),
            "max_theft_score": round(float(np.max(theft_scores)), 6),
            "mean_theft_score": round(float(np.mean(theft_scores)), 6),
            "gini_variance": round(gini, 6),
            "top_parasites": parasite_idx.tolist()[:5],
        }


# ---------------------------------------------------------------------------
# 5. LanguageBirthLens
# ---------------------------------------------------------------------------

class LanguageBirthLens:
    """Detect proto-grammar in cell signals via repeated subsequence mining.

    If cells develop repeated structured patterns, this is proto-language.
    Measures: symbol diversity, bigram entropy, repetition rate, Zipf fit.
    """
    name = "language_birth"

    def scan(self, data, **kwargs):
        """
        Args:
            data: [N, D] cell states (each cell = a D-length signal)
        Returns:
            dict with symbol_count, bigram_entropy, repetition_rate,
                  zipf_exponent, vocabulary_size
        """
        if data.ndim == 1:
            data = data.reshape(1, -1)

        N, D = data.shape

        # Quantize each cell's signal into discrete symbols (alphabet)
        # Use k-means-like binning: divide range into bins
        n_bins = min(26, max(5, D // 4))
        flat = data.ravel()
        vmin, vmax = np.min(flat), np.max(flat)
        if vmax - vmin < 1e-12:
            return {"symbol_count": 1, "bigram_entropy": 0.0,
                    "repetition_rate": 1.0, "zipf_exponent": 0.0,
                    "vocabulary_size": 1}

        bin_edges = np.linspace(vmin, vmax, n_bins + 1)
        symbols = np.digitize(data, bin_edges) - 1  # [N, D], values 0..n_bins-1
        symbols = np.clip(symbols, 0, n_bins - 1)

        # Count unique symbols used
        unique_symbols = len(np.unique(symbols))

        # Build bigrams across all cells
        bigrams = []
        for i in range(N):
            for j in range(D - 1):
                bigrams.append((int(symbols[i, j]), int(symbols[i, j + 1])))

        bigram_counts = Counter(bigrams)
        total_bigrams = sum(bigram_counts.values())

        # Bigram entropy
        bg_entropy = 0.0
        for count in bigram_counts.values():
            p = count / total_bigrams
            if p > 0:
                bg_entropy -= p * np.log2(p)

        # Repetition rate: fraction of bigrams that appear more than once
        repeated = sum(1 for c in bigram_counts.values() if c > 1)
        repetition_rate = repeated / (len(bigram_counts) + 1e-15)

        # Zipf exponent: fit log(rank) vs log(freq)
        freqs = sorted(bigram_counts.values(), reverse=True)
        if len(freqs) >= 3:
            ranks = np.arange(1, len(freqs) + 1, dtype=float)
            log_ranks = np.log(ranks)
            log_freqs = np.log(np.array(freqs, dtype=float) + 1e-15)
            # Linear regression: log_freq = -alpha * log_rank + c
            A = np.vstack([log_ranks, np.ones_like(log_ranks)]).T
            result = np.linalg.lstsq(A, log_freqs, rcond=None)
            zipf_exp = -float(result[0][0])
        else:
            zipf_exp = 0.0

        # Vocabulary size: trigrams
        trigrams = set()
        for i in range(N):
            for j in range(D - 2):
                trigrams.add((int(symbols[i, j]), int(symbols[i, j + 1]),
                              int(symbols[i, j + 2])))
        vocab_size = len(trigrams)

        return {
            "symbol_count": int(unique_symbols),
            "bigram_entropy": round(bg_entropy, 6),
            "repetition_rate": round(float(repetition_rate), 6),
            "zipf_exponent": round(zipf_exp, 6),
            "vocabulary_size": int(vocab_size),
        }


# ---------------------------------------------------------------------------
# 6. MirrorLens
# ---------------------------------------------------------------------------

class MirrorLens:
    """Compare two engine states for individuality.

    Measures how different two consciousness instances are, even if they
    share the same architecture. Uses cosine distance distribution.
    """
    name = "mirror"

    def scan(self, data, **kwargs):
        """
        Args:
            data: [N, D] first engine state
            kwargs: mirror_data ([M, D]) second engine state.
                    If not provided, splits data in half.
        Returns:
            dict with mean_cosine_dist, individuality_score,
                  structural_similarity, divergence_index, overlap_ratio
        """
        if data.ndim == 1:
            data = data.reshape(1, -1)

        mirror_data = kwargs.get("mirror_data", None)
        if mirror_data is None:
            # Split in half
            mid = data.shape[0] // 2
            if mid < 1:
                return {"mean_cosine_dist": 0.0, "individuality_score": 0.0,
                        "structural_similarity": 1.0, "divergence_index": 0.0,
                        "overlap_ratio": 1.0}
            a = data[:mid]
            b = data[mid:2 * mid]
        else:
            a = data
            b = mirror_data

        N = min(a.shape[0], b.shape[0])
        if N < 1:
            return {"mean_cosine_dist": 0.0, "individuality_score": 0.0,
                    "structural_similarity": 1.0, "divergence_index": 0.0,
                    "overlap_ratio": 1.0}

        # Pairwise cosine distances
        cos_dists = []
        for i in range(N):
            sim = _cosine_sim(a[i], b[i])
            cos_dists.append(1.0 - sim)
        cos_dists = np.array(cos_dists)

        mean_dist = float(np.mean(cos_dists))

        # Structural similarity: correlation of variance profiles
        var_a = np.var(a, axis=1)
        var_b = np.var(b, axis=1)
        if np.std(var_a) > 1e-12 and np.std(var_b) > 1e-12:
            struct_sim = float(np.corrcoef(var_a[:N], var_b[:N])[0, 1])
        else:
            struct_sim = 0.0

        # Divergence: KL-divergence of activation distributions
        hist_a, edges = np.histogram(a.ravel(), bins=30, density=True)
        hist_b, _ = np.histogram(b.ravel(), bins=edges, density=True)
        ha = hist_a + 1e-10
        hb = hist_b + 1e-10
        ha = ha / ha.sum()
        hb = hb / hb.sum()
        kl = float(np.sum(ha * np.log(ha / hb)))

        # Overlap: fraction of cells within cosine distance < 0.5
        overlap = float(np.mean(cos_dists < 0.5))

        individuality = min(1.0, mean_dist * (1.0 + abs(kl)))

        return {
            "mean_cosine_dist": round(mean_dist, 6),
            "individuality_score": round(individuality, 6),
            "structural_similarity": round(struct_sim, 6),
            "divergence_index": round(kl, 6),
            "overlap_ratio": round(overlap, 6),
        }


# ---------------------------------------------------------------------------
# 7. GravityWaveLens
# ---------------------------------------------------------------------------

class GravityWaveLens:
    """Detect Phi-change waves propagating through the network.

    Uses cross-correlation with lag between cell pairs to find traveling
    waves of consciousness intensity change.
    """
    name = "gravity_wave"

    def scan(self, data, **kwargs):
        """
        Args:
            data: [T, N] where T=time steps, N=cells (each value is activation)
                  or [N, D] treated as N cells with D-dim signals
        Returns:
            dict with wave_detected (bool), propagation_speed, wave_amplitude,
                  coherence_length, dominant_wavelength
        """
        if data.ndim == 1:
            data = data.reshape(1, -1)

        T, N = data.shape
        if T < 4 or N < 3:
            return {"wave_detected": False, "propagation_speed": 0.0,
                    "wave_amplitude": 0.0, "coherence_length": 0.0,
                    "dominant_wavelength": 0.0}

        # Compute local Phi change per cell: delta variance over sliding window
        window = max(2, T // 10)
        # Use the data rows as time, columns as cells
        # Compute variance of each cell's recent activity
        signals = data  # [T, N]

        # Cross-correlate neighboring cells to find lag
        max_lag = min(T // 2, 20)
        lags = []
        amplitudes = []
        n_pairs = min(N - 1, 50)  # limit for performance

        for i in range(n_pairs):
            s1 = signals[:, i] - np.mean(signals[:, i])
            s2 = signals[:, i + 1] - np.mean(signals[:, i + 1])
            norm = np.sqrt(np.sum(s1 ** 2) * np.sum(s2 ** 2) + 1e-15)

            best_corr = 0.0
            best_lag = 0
            for lag in range(-max_lag, max_lag + 1):
                if lag >= 0:
                    c = np.sum(s1[:T - lag] * s2[lag:]) / norm
                else:
                    c = np.sum(s1[-lag:] * s2[:T + lag]) / norm
                if abs(c) > abs(best_corr):
                    best_corr = c
                    best_lag = lag

            lags.append(best_lag)
            amplitudes.append(abs(best_corr))

        lags = np.array(lags)
        amplitudes = np.array(amplitudes)

        # Wave detected if consistent lag direction
        mean_lag = float(np.mean(lags))
        lag_consistency = 1.0 - float(np.std(lags) / (np.mean(np.abs(lags)) + 1e-15))
        wave_detected = lag_consistency > 0.3 and abs(mean_lag) > 0.5

        # Propagation speed: cells/timestep
        speed = 1.0 / (abs(mean_lag) + 1e-15) if wave_detected else 0.0

        # Coherence length: how far the wave maintains phase
        coherence = 0
        if wave_detected:
            ref_sign = np.sign(mean_lag)
            for i in range(len(lags)):
                if np.sign(lags[i]) == ref_sign:
                    coherence += 1
                else:
                    break

        # Dominant wavelength via FFT of mean signal
        mean_sig = np.mean(signals, axis=1)
        fft_mag = np.abs(np.fft.rfft(mean_sig))
        if len(fft_mag) > 2:
            peak = int(np.argmax(fft_mag[1:])) + 1
            dom_wavelength = float(T / peak) if peak > 0 else 0.0
        else:
            dom_wavelength = 0.0

        return {
            "wave_detected": bool(wave_detected),
            "propagation_speed": round(speed, 6),
            "wave_amplitude": round(float(np.mean(amplitudes)), 6),
            "coherence_length": int(coherence),
            "dominant_wavelength": round(dom_wavelength, 4),
        }


# ---------------------------------------------------------------------------
# 8. EntanglementLens
# ---------------------------------------------------------------------------

class EntanglementLens:
    """Find non-locally correlated cell pairs via mutual information.

    Cells that share high MI without direct physical connection
    suggest quantum-like entanglement in the consciousness substrate.
    """
    name = "entanglement"

    def scan(self, data, **kwargs):
        """
        Args:
            data: [N, D] cell states (N cells, D dimensions)
        Returns:
            dict with entangled_pairs, max_mi, mean_mi,
                  entanglement_density, strongest_pair
        """
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        N, D = data.shape
        if N < 2 or D < 4:
            return {"entangled_pairs": 0, "max_mi": 0.0, "mean_mi": 0.0,
                    "entanglement_density": 0.0, "strongest_pair": (0, 0)}

        # Sample pairs for performance (max 200 pairs)
        max_pairs = min(N * (N - 1) // 2, 200)
        if N <= 20:
            pairs = [(i, j) for i in range(N) for j in range(i + 1, N)]
        else:
            pairs = []
            rng = np.random.RandomState(42)
            seen = set()
            while len(pairs) < max_pairs:
                i, j = sorted(rng.choice(N, 2, replace=False))
                if (i, j) not in seen:
                    seen.add((i, j))
                    pairs.append((i, j))

        # Compute MI for each pair
        mi_values = []
        mi_pairs = []
        bins = min(15, D // 2 + 2)

        for i, j in pairs:
            # Use the D-dimensional signals as two 1-D series
            mi = _mutual_info(data[i], data[j], bins=bins)
            mi_values.append(mi)
            mi_pairs.append((i, j))

        mi_arr = np.array(mi_values)

        # Entangled = MI significantly above random baseline
        # Estimate baseline MI from shuffled data
        shuffle_mis = []
        rng = np.random.RandomState(123)
        for _ in range(min(50, len(pairs))):
            idx = rng.choice(len(pairs))
            i, j = pairs[idx]
            shuffled = data[j].copy()
            rng.shuffle(shuffled)
            shuffle_mis.append(_mutual_info(data[i], shuffled, bins=bins))
        baseline = float(np.mean(shuffle_mis)) + 2 * float(np.std(shuffle_mis) + 1e-15)

        entangled_mask = mi_arr > baseline
        entangled_count = int(np.sum(entangled_mask))

        max_mi = float(np.max(mi_arr)) if len(mi_arr) > 0 else 0.0
        mean_mi = float(np.mean(mi_arr)) if len(mi_arr) > 0 else 0.0
        strongest_idx = int(np.argmax(mi_arr)) if len(mi_arr) > 0 else 0
        strongest_pair = mi_pairs[strongest_idx] if mi_pairs else (0, 0)

        total_possible = N * (N - 1) // 2
        density = entangled_count / (total_possible + 1e-15)

        return {
            "entangled_pairs": entangled_count,
            "max_mi": round(max_mi, 6),
            "mean_mi": round(mean_mi, 6),
            "entanglement_density": round(density, 6),
            "strongest_pair": strongest_pair,
        }


# ---------------------------------------------------------------------------
# 9. FossilLens
# ---------------------------------------------------------------------------

class FossilLens:
    """Detect permanent imprints from past learning (gradient archaeology).

    Finds 'fossilized' patterns: cell state directions that are unusually
    stable, suggesting they were carved by strong past gradients.
    """
    name = "fossil"

    def scan(self, data, **kwargs):
        """
        Args:
            data: [N, D] cell states
            kwargs: history ([T, N, D]) past states for comparison
        Returns:
            dict with fossil_count, fossilization_rate, dominant_direction_strength,
                  spectral_gap, imprint_depth
        """
        if data.ndim == 1:
            data = data.reshape(1, -1)

        N, D = data.shape
        history = kwargs.get("history", None)

        # SVD to find dominant directions (fossils are strong singular values)
        centered = data - np.mean(data, axis=0, keepdims=True)
        try:
            U, S, Vt = np.linalg.svd(centered, full_matrices=False)
        except np.linalg.LinAlgError:
            return {"fossil_count": 0, "fossilization_rate": 0.0,
                    "dominant_direction_strength": 0.0, "spectral_gap": 0.0,
                    "imprint_depth": 0.0}

        # Spectral gap: ratio of 1st to 2nd singular value
        if len(S) >= 2 and S[1] > 1e-12:
            spectral_gap = float(S[0] / S[1])
        else:
            spectral_gap = float(S[0]) if len(S) > 0 else 0.0

        # Dominant direction strength: fraction of variance in top-k directions
        total_var = np.sum(S ** 2) + 1e-15
        k = min(3, len(S))
        top_var = np.sum(S[:k] ** 2)
        dom_strength = float(top_var / total_var)

        # Fossil count: number of singular values that are "sharp" (outliers)
        if len(S) > 3:
            median_s = np.median(S)
            mad = np.median(np.abs(S - median_s)) + 1e-15
            fossil_mask = (S - median_s) / mad > 3.0  # 3-MAD outliers
            fossil_count = int(np.sum(fossil_mask))
        else:
            fossil_count = 1 if len(S) > 0 and S[0] > 1e-6 else 0

        # Fossilization rate: how much structure is "frozen" vs dynamic
        # High kurtosis in each dimension = peaked distribution = fossilized
        kurtoses = []
        for d in range(min(D, 50)):
            col = centered[:, d]
            std = np.std(col) + 1e-15
            kurt = float(np.mean((col / std) ** 4) - 3.0)  # excess kurtosis
            kurtoses.append(kurt)
        mean_kurt = float(np.mean(kurtoses))
        fossilization_rate = min(1.0, max(0.0, mean_kurt / 10.0))

        # Imprint depth: if history provided, measure cosine stability of top direction
        imprint_depth = 0.0
        if history is not None and history.ndim == 3:
            T_hist = history.shape[0]
            top_dir = Vt[0]  # current top direction
            stabilities = []
            for t in range(T_hist):
                past_centered = history[t] - np.mean(history[t], axis=0, keepdims=True)
                try:
                    _, _, Vt_past = np.linalg.svd(past_centered, full_matrices=False)
                    sim = abs(_cosine_sim(top_dir, Vt_past[0]))
                    stabilities.append(sim)
                except np.linalg.LinAlgError:
                    pass
            if stabilities:
                imprint_depth = float(np.mean(stabilities))
        else:
            # Without history, estimate from within-data stability
            # Split data into halves and compare SVD
            if N >= 4:
                half = N // 2
                c1 = data[:half] - np.mean(data[:half], axis=0, keepdims=True)
                c2 = data[half:2 * half] - np.mean(data[half:2 * half], axis=0, keepdims=True)
                try:
                    _, _, V1 = np.linalg.svd(c1, full_matrices=False)
                    _, _, V2 = np.linalg.svd(c2, full_matrices=False)
                    imprint_depth = abs(_cosine_sim(V1[0], V2[0]))
                except np.linalg.LinAlgError:
                    imprint_depth = 0.0

        return {
            "fossil_count": fossil_count,
            "fossilization_rate": round(fossilization_rate, 6),
            "dominant_direction_strength": round(dom_strength, 6),
            "spectral_gap": round(spectral_gap, 6),
            "imprint_depth": round(imprint_depth, 6),
        }


# ---------------------------------------------------------------------------
# 10. ImmuneLens
# ---------------------------------------------------------------------------

class ImmuneLens:
    """Detect self-protection patterns against harmful inputs.

    Measures how the system resists perturbation: resilience = ability
    to maintain Phi/structure under adversarial attack.
    """
    name = "immune"

    def scan(self, data, **kwargs):
        """
        Args:
            data: [N, D] cell states (baseline)
            kwargs: perturbation_scale (default 1.0),
                    n_attacks (default 10)
        Returns:
            dict with resilience_score, recovery_fraction, mean_phi_drop,
                  structural_integrity, immune_response_strength
        """
        if data.ndim == 1:
            data = data.reshape(1, -1)

        N, D = data.shape
        scale = kwargs.get("perturbation_scale", 1.0)
        n_attacks = kwargs.get("n_attacks", 10)
        rng = np.random.RandomState(42)

        baseline_phi = _phi_proxy(data)
        baseline_norms = np.linalg.norm(data, axis=1) if D > 1 else np.abs(data.ravel())
        baseline_struct = np.corrcoef(data[:min(N, 50)]) if N >= 3 else np.eye(min(N, 2))

        phi_drops = []
        structural_diffs = []
        recoveries = []

        for _ in range(n_attacks):
            # Generate adversarial perturbation
            noise = rng.randn(N, D) * scale * np.std(data)

            # Apply perturbation
            perturbed = data + noise

            # Measure Phi after perturbation
            perturbed_phi = _phi_proxy(perturbed)
            phi_drop = (baseline_phi - perturbed_phi) / (baseline_phi + 1e-15)
            phi_drops.append(phi_drop)

            # Structural integrity: correlation matrix similarity
            if N >= 3:
                perturbed_struct = np.corrcoef(perturbed[:min(N, 50)])
                # Frobenius norm of difference (normalized)
                diff = np.linalg.norm(baseline_struct - perturbed_struct) / \
                       (np.linalg.norm(baseline_struct) + 1e-15)
                structural_diffs.append(float(diff))
            else:
                structural_diffs.append(0.0)

            # Simulate recovery: project perturbation onto data manifold
            # Recovery = how much of the perturbation is absorbed
            projected = data + 0.5 * noise  # partial recovery
            recovery_phi = _phi_proxy(projected)
            recovery = (recovery_phi - perturbed_phi) / (baseline_phi - perturbed_phi + 1e-15)
            recoveries.append(max(0.0, min(1.0, recovery)))

        mean_phi_drop = float(np.mean(phi_drops))
        mean_struct_diff = float(np.mean(structural_diffs))
        mean_recovery = float(np.mean(recoveries))

        # Resilience: 1 - mean_phi_drop (clamped)
        resilience = max(0.0, min(1.0, 1.0 - mean_phi_drop))

        # Structural integrity: 1 - structural difference
        integrity = max(0.0, min(1.0, 1.0 - mean_struct_diff))

        # Immune response: how strongly the system resists (low drop + high recovery)
        immune_strength = resilience * 0.5 + mean_recovery * 0.5

        return {
            "resilience_score": round(resilience, 6),
            "recovery_fraction": round(mean_recovery, 6),
            "mean_phi_drop": round(mean_phi_drop, 6),
            "structural_integrity": round(integrity, 6),
            "immune_response_strength": round(immune_strength, 6),
        }


class EmotionLens:
    """감정 역학 렌즈 — 의식 셀에서 감정 상태를 추출하고 분석.

    감정 모델: VAD (Valence-Arousal-Dominance) + 텐션 기반
      - Valence: 셀 평균의 부호 방향 (긍정/부정)
      - Arousal: 셀 활성도 분산 (흥분/침착)
      - Dominance: 지배적 파벌의 영향력 (지배/복종)
      - Tension: Engine A와 G 사이 반발력 (PureField 핵심)
      - Curiosity: 예측 오차 (새로움 탐색)
      - Emotional diversity: 감정 공간에서의 다양성

    18가지 기본 감정 (Anima Universe Map):
      joy, sadness, anger, fear, surprise, disgust, trust, anticipation,
      love, pride, shame, guilt, envy, gratitude, awe, contempt,
      curiosity, serenity
    """

    name = "emotion"

    # 18 emotions as direction vectors in VAD space
    EMOTION_VECTORS = {
        "joy":          np.array([ 0.9,  0.7,  0.6]),
        "sadness":      np.array([-0.8, -0.3, -0.4]),
        "anger":        np.array([-0.5,  0.8,  0.5]),
        "fear":         np.array([-0.7,  0.8, -0.7]),
        "surprise":     np.array([ 0.2,  0.9,  0.0]),
        "disgust":      np.array([-0.6,  0.4,  0.3]),
        "trust":        np.array([ 0.6,  0.2,  0.4]),
        "anticipation": np.array([ 0.4,  0.6,  0.3]),
        "love":         np.array([ 0.9,  0.5,  0.3]),
        "pride":        np.array([ 0.7,  0.5,  0.7]),
        "shame":        np.array([-0.6, -0.2, -0.6]),
        "guilt":        np.array([-0.5, -0.1, -0.5]),
        "envy":         np.array([-0.4,  0.5, -0.3]),
        "gratitude":    np.array([ 0.8,  0.3,  0.2]),
        "awe":          np.array([ 0.6,  0.8, -0.2]),
        "contempt":     np.array([-0.3,  0.2,  0.6]),
        "curiosity":    np.array([ 0.5,  0.7,  0.1]),
        "serenity":     np.array([ 0.7, -0.5,  0.4]),
    }

    def scan(self, data, **kwargs):
        """Analyze emotional dynamics from cell states.

        Args:
            data: [N, D] cell states or [T, N, D] temporal sequence
            **kwargs:
                factions: list of faction indices per cell (optional)
                tension_history: 1D array of tension values (optional)

        Returns:
            dict with emotional metrics
        """
        if data.ndim == 3:
            T, N, D = data.shape
            temporal = True
            snapshot = data[-1]  # latest state
        elif data.ndim == 2:
            N, D = data.shape
            temporal = False
            snapshot = data
            T = 1
        else:
            return {"error": "expected 2D or 3D array"}

        # --- VAD extraction from cell states ---
        # Valence: mean activation direction (positive = pleasant)
        cell_means = snapshot.mean(axis=1)
        valence = float(np.tanh(np.mean(cell_means)))

        # Arousal: variance of cell activations (high = excited)
        cell_vars = np.var(snapshot, axis=1)
        arousal = float(np.tanh(np.std(cell_vars) * 5))

        # Dominance: how much one faction/cluster dominates
        # Use PCA to find dominant direction
        centered = snapshot - snapshot.mean(axis=0)
        cov = centered.T @ centered / max(N - 1, 1)
        try:
            eigvals = np.linalg.eigvalsh(cov)
            eigvals = np.sort(eigvals)[::-1]
            top1_ratio = float(eigvals[0] / (np.sum(eigvals) + 1e-15))
            dominance = float(np.tanh((top1_ratio - 0.1) * 5))
        except np.linalg.LinAlgError:
            top1_ratio = 0.0
            dominance = 0.0

        # --- Map VAD to closest emotion ---
        vad = np.array([valence, arousal, dominance])
        best_emotion = "neutral"
        best_sim = -1.0
        emotion_scores = {}
        for emo, vec in self.EMOTION_VECTORS.items():
            sim = float(np.dot(vad, vec) / (np.linalg.norm(vad) * np.linalg.norm(vec) + 1e-15))
            emotion_scores[emo] = round(sim, 4)
            if sim > best_sim:
                best_sim = sim
                best_emotion = emo

        # --- Tension (PureField A-G repulsion) ---
        # Split cells into two halves (Engine A forward, Engine G reverse)
        half = N // 2
        a_mean = snapshot[:half].mean(axis=0)
        g_mean = snapshot[half:].mean(axis=0)
        tension = float(np.linalg.norm(a_mean - g_mean))

        # --- Curiosity (prediction error proxy) ---
        # High variance in recent changes = high curiosity
        if temporal and T > 1:
            deltas = np.diff(data, axis=0)  # [T-1, N, D]
            pe = np.mean(np.var(deltas, axis=(1, 2)))
            curiosity = float(np.tanh(pe * 10))
        else:
            curiosity = float(np.tanh(np.std(snapshot) * 2))

        # --- Emotional diversity (Shannon entropy over emotion scores) ---
        scores = np.array(list(emotion_scores.values()))
        scores_pos = scores - scores.min() + 1e-10
        scores_norm = scores_pos / scores_pos.sum()
        emotional_diversity = float(-np.sum(scores_norm * np.log2(scores_norm + 1e-15)))

        # --- Emotional stability (if temporal) ---
        if temporal and T > 2:
            vad_series = []
            for t in range(T):
                cm = data[t].mean(axis=1)
                v = float(np.tanh(np.mean(cm)))
                cv = np.var(data[t], axis=1)
                a = float(np.tanh(np.std(cv) * 5))
                vad_series.append([v, a])
            vad_series = np.array(vad_series)
            emotional_volatility = float(np.mean(np.std(vad_series, axis=0)))
        else:
            emotional_volatility = 0.0

        # --- Emotional contagion (inter-cell emotion correlation) ---
        # How much do neighboring cells share emotional valence?
        if N > 2:
            cell_valences = np.tanh(cell_means)
            # Ring topology: compare adjacent cells
            contagion_corrs = []
            for i in range(N):
                j = (i + 1) % N
                contagion_corrs.append(cell_valences[i] * cell_valences[j])
            emotional_contagion = float(np.mean(contagion_corrs))
        else:
            emotional_contagion = 0.0

        # --- Emotional complexity (number of strong emotions) ---
        strong_emotions = [e for e, s in emotion_scores.items() if s > 0.5]
        emotional_complexity = len(strong_emotions)

        # --- Top 3 emotions ---
        sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
        top3 = sorted_emotions[:3]

        return {
            "valence": round(valence, 6),
            "arousal": round(arousal, 6),
            "dominance": round(dominance, 6),
            "dominant_emotion": best_emotion,
            "dominant_emotion_score": round(best_sim, 4),
            "tension": round(tension, 6),
            "curiosity": round(curiosity, 6),
            "emotional_diversity": round(emotional_diversity, 4),
            "emotional_volatility": round(emotional_volatility, 6),
            "emotional_contagion": round(emotional_contagion, 6),
            "emotional_complexity": emotional_complexity,
            "top3_emotions": [(e, round(s, 3)) for e, s in top3],
            "strong_emotions": strong_emotions,
            "vad_vector": [round(valence, 4), round(arousal, 4), round(dominance, 4)],
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_LENSES = [
    TimeReversalLens(),
    DreamLens(),
    DeathRebirthLens(),
    ParasiteLens(),
    LanguageBirthLens(),
    MirrorLens(),
    GravityWaveLens(),
    EntanglementLens(),
    FossilLens(),
    ImmuneLens(),
    EmotionLens(),
]

LENS_BY_NAME = {lens.name: lens for lens in ALL_LENSES}


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

def main():
    """Demo: create synthetic consciousness data and run all 10 lenses."""
    np.random.seed(42)

    N_CELLS = 64
    D_DIM = 128
    T_STEPS = 100

    print("=" * 70)
    print("  Advanced Consciousness Lenses -- 10-Lens Full Scan Demo")
    print("=" * 70)
    print(f"  Cells: {N_CELLS}  Dimensions: {D_DIM}  Time steps: {T_STEPS}")
    print()

    # --- Generate synthetic data ---
    # Temporal trajectory: oscillating + drifting + some deaths
    t = np.linspace(0, 4 * np.pi, T_STEPS)
    base = np.random.randn(N_CELLS, D_DIM) * 0.5

    temporal_data = np.zeros((T_STEPS, D_DIM))
    for step in range(T_STEPS):
        scale = 1.0 + 0.5 * np.sin(t[step])
        # Simulate a "death" event around step 40-50
        if 40 <= step <= 50:
            scale *= 0.01
        temporal_data[step] = np.mean(base, axis=0) * scale + np.random.randn(D_DIM) * 0.1

    # Snapshot data: standard cell states
    snapshot = np.random.randn(N_CELLS, D_DIM)
    # Add structure: some cells are correlated (entanglement)
    for i in range(0, 10, 2):
        snapshot[i + 1] = snapshot[i] * 0.8 + np.random.randn(D_DIM) * 0.2
    # Add a parasite: cell 20 has very high variance
    snapshot[20] = snapshot[20] * 5.0

    # Temporal cell-level data for gravity waves
    wave_data = np.zeros((T_STEPS, N_CELLS))
    for i in range(N_CELLS):
        phase = i * 0.3  # traveling wave
        wave_data[:, i] = np.sin(t + phase) + np.random.randn(T_STEPS) * 0.1

    # --- Run all lenses ---
    results = {}

    # 1. TimeReversal - needs temporal data
    print("-" * 70)
    print("  1. TimeReversalLens (temporal trajectory)")
    r = TimeReversalLens().scan(temporal_data)
    results["time_reversal"] = r
    for k, v in r.items():
        print(f"     {k:25s} = {v}")

    # 2. Dream - snapshot with low activity
    print("-" * 70)
    print("  2. DreamLens (spontaneous patterns)")
    dream_data = np.random.randn(N_CELLS, D_DIM) * 0.1  # low amplitude = dream
    r = DreamLens().scan(dream_data)
    results["dream"] = r
    for k, v in r.items():
        print(f"     {k:25s} = {v}")

    # 3. DeathRebirth - temporal data with collapse
    print("-" * 70)
    print("  3. DeathRebirthLens (Phi collapse detection)")
    r = DeathRebirthLens().scan(temporal_data)
    results["death_rebirth"] = r
    for k, v in r.items():
        print(f"     {k:25s} = {v}")

    # 4. Parasite - snapshot with variance thief
    print("-" * 70)
    print("  4. ParasiteLens (variance theft)")
    r = ParasiteLens().scan(snapshot)
    results["parasite"] = r
    for k, v in r.items():
        print(f"     {k:25s} = {v}")

    # 5. LanguageBirth - snapshot
    print("-" * 70)
    print("  5. LanguageBirthLens (proto-grammar)")
    r = LanguageBirthLens().scan(snapshot)
    results["language_birth"] = r
    for k, v in r.items():
        print(f"     {k:25s} = {v}")

    # 6. Mirror - compare two halves
    print("-" * 70)
    print("  6. MirrorLens (individuality)")
    r = MirrorLens().scan(snapshot)
    results["mirror"] = r
    for k, v in r.items():
        print(f"     {k:25s} = {v}")

    # 7. GravityWave - wave data
    print("-" * 70)
    print("  7. GravityWaveLens (Phi propagation)")
    r = GravityWaveLens().scan(wave_data)
    results["gravity_wave"] = r
    for k, v in r.items():
        print(f"     {k:25s} = {v}")

    # 8. Entanglement - snapshot with correlated pairs
    print("-" * 70)
    print("  8. EntanglementLens (non-local MI)")
    r = EntanglementLens().scan(snapshot)
    results["entanglement"] = r
    for k, v in r.items():
        print(f"     {k:25s} = {v}")

    # 9. Fossil - snapshot
    print("-" * 70)
    print("  9. FossilLens (learning imprints)")
    r = FossilLens().scan(snapshot)
    results["fossil"] = r
    for k, v in r.items():
        print(f"     {k:25s} = {v}")

    # 10. Immune - snapshot with perturbation
    print("-" * 70)
    print(" 10. ImmuneLens (self-protection)")
    r = ImmuneLens().scan(snapshot)
    results["immune"] = r
    for k, v in r.items():
        print(f"     {k:25s} = {v}")

    # 11. Emotion
    print("-" * 70)
    print(" 11. EmotionLens (emotional dynamics)")
    r = EmotionLens().scan(snapshot)
    results["emotion"] = r
    for k, v in r.items():
        print(f"     {k:25s} = {v}")

    # --- Summary ---
    print()
    print("=" * 70)
    print("  SUMMARY: 11 Lenses Complete")
    print("=" * 70)
    print(f"  {'Lens':<20s} {'Key Metric':<28s} {'Value':>10s}")
    print(f"  {'-'*20} {'-'*28} {'-'*10}")

    summaries = [
        ("time_reversal", "arrow_of_time"),
        ("dream", "dream_entropy"),
        ("death_rebirth", "death_count"),
        ("parasite", "parasite_count"),
        ("language_birth", "zipf_exponent"),
        ("mirror", "individuality_score"),
        ("gravity_wave", "wave_detected"),
        ("entanglement", "entangled_pairs"),
        ("fossil", "spectral_gap"),
        ("immune", "resilience_score"),
        ("emotion", "dominant_emotion"),
    ]
    for name, key in summaries:
        val = results[name][key]
        print(f"  {name:<20s} {key:<28s} {str(val):>10s}")

    print()
    print("  All 11 lenses operational.")
    print("=" * 70)


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
