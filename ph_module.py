"""PH Module for Anima — Real-time Persistent Homology Analysis

Integrates with ConsciousMind to provide:
1. Confusion prediction (H-CX-66: r=-0.97)
2. Overfitting detection (H-CX-95: r=0.998)
3. Telepathy encoding (H-CX-108: 9 numbers)
4. Semantic hierarchy (H-CX-85: 89% purity)

Usage:
    from ph_module import PHModule
    ph = PHModule(n_classes=8)  # 8-dim output of ConsciousMind
    ph.collect(direction, label)  # per-batch
    h0, merges = ph.compute_ph()  # per-epoch
"""

import numpy as np
from collections import defaultdict

try:
    from ripser import ripser
    HAS_RIPSER = True
except ImportError:
    HAS_RIPSER = False


class PHModule:
    """Real-time PH analysis for Anima consciousness engine."""

    def __init__(self, n_classes=8, buffer_size=1000):
        self.n_cls = n_classes
        self.buffer_size = buffer_size
        self.direction_buffer = defaultdict(list)
        self.h0_history = []
        self.merge_history = []
        self.gap_threshold = 0.05

    def collect(self, direction, label):
        """Collect direction vector for a class (call per sample).

        Args:
            direction: numpy array, normalized direction vector
            label: int, class label
        """
        if isinstance(direction, (list, tuple)):
            direction = np.array(direction)
        if hasattr(direction, 'detach'):
            direction = direction.detach().cpu().numpy()

        buf = self.direction_buffer[int(label)]
        buf.append(direction.flatten())
        if len(buf) > self.buffer_size:
            buf.pop(0)

    def collect_batch(self, directions, labels):
        """Collect a batch of directions.

        Args:
            directions: (B, D) array or tensor
            labels: (B,) array or tensor
        """
        if hasattr(directions, 'detach'):
            directions = directions.detach().cpu().numpy()
        if hasattr(labels, 'detach'):
            labels = labels.detach().cpu().numpy()

        for i in range(len(labels)):
            self.collect(directions[i], labels[i])

    def _class_means(self):
        """Compute normalized class mean directions."""
        dim = None
        for buf in self.direction_buffer.values():
            if buf:
                dim = len(buf[0])
                break
        if dim is None:
            return None

        means = np.zeros((self.n_cls, dim))
        for c in range(self.n_cls):
            if self.direction_buffer[c]:
                m = np.mean(self.direction_buffer[c], axis=0)
                norm = np.linalg.norm(m)
                if norm > 1e-8:
                    means[c] = m / norm
        return means

    def _cosine_distance(self, means):
        """Compute cosine distance matrix."""
        cos_sim = means @ means.T
        cos_dist = np.clip(1 - cos_sim, 0, 2)
        np.fill_diagonal(cos_dist, 0)
        return cos_dist

    def _single_linkage_merges(self, cos_dist):
        """Extract merge events via single-linkage clustering."""
        n = len(cos_dist)
        edges = sorted([(cos_dist[i, j], i, j)
                        for i in range(n) for j in range(i + 1, n)])
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            a, b = find(a), find(b)
            if a != b:
                parent[a] = b
                return True
            return False

        merges = []
        for dist, i, j in edges:
            if union(i, j):
                merges.append((dist, min(i, j), max(i, j)))
        return merges

    def compute_ph(self):
        """Compute PH and return (h0_total, merges).

        Call at end of epoch or periodically.
        Returns:
            h0_total: float, total H0 persistence
            merges: list of (distance, class_i, class_j)
        """
        means = self._class_means()
        if means is None:
            return 0.0, []

        cos_dist = self._cosine_distance(means)
        merges = self._single_linkage_merges(cos_dist)

        # H0 total persistence
        if HAS_RIPSER:
            result = ripser(cos_dist, maxdim=0, distance_matrix=True)
            h0 = result['dgms'][0]
            h0_finite = h0[h0[:, 1] < np.inf]
            h0_total = np.sum(h0_finite[:, 1] - h0_finite[:, 0]) if len(h0_finite) > 0 else 0.0
        else:
            # Fallback: sum of merge distances
            h0_total = sum(d for d, i, j in merges)

        self.h0_history.append(h0_total)
        self.merge_history.append(merges)
        return h0_total, merges

    def detect_overfitting(self, train_h0=None, test_h0=None):
        """Detect overfitting via H0 gap (H-CX-95: r=0.998).

        Args:
            train_h0: float, H0 from training data (optional, uses last)
            test_h0: float, H0 from test data (optional, uses last)

        Returns:
            (status, gap): ('OK'|'WATCH'|'ALERT', float)
        """
        if train_h0 is None or test_h0 is None:
            if len(self.h0_history) < 2:
                return 'OK', 0.0
            train_h0 = self.h0_history[-2]
            test_h0 = self.h0_history[-1]

        gap = abs(train_h0 - test_h0)
        if gap > self.gap_threshold:
            return 'ALERT', gap
        elif gap > self.gap_threshold * 0.5:
            return 'WATCH', gap
        return 'OK', gap

    def get_telepathy_packet(self):
        """Get 9-number telepathy packet (H-CX-108: r=0.887).

        Returns:
            list of merge distances, or None
        """
        if not self.merge_history:
            return None
        return [d for d, i, j in self.merge_history[-1]]

    def predict_confusion(self, class_a, class_b):
        """Predict confusion probability between two classes (H-CX-66).

        Returns:
            float: confusion probability (higher = more confused)
        """
        if not self.merge_history:
            return 0.0
        pair = (min(class_a, class_b), max(class_a, class_b))
        for d, i, j in self.merge_history[-1]:
            if (i, j) == pair:
                return 1.0 / (d + 0.01)
        return 0.0

    def get_dendrogram(self):
        """Get current merge dendrogram (H-CX-85).

        Returns:
            list of (distance, class_i, class_j) or None
        """
        return self.merge_history[-1] if self.merge_history else None

    def get_h0_trend(self, window=5):
        """Get recent H0 trend for learning monitoring.

        Returns:
            (direction, slope): ('improving'|'stable'|'degrading', float)
        """
        if len(self.h0_history) < window:
            return 'unknown', 0.0
        recent = self.h0_history[-window:]
        slope = (recent[-1] - recent[0]) / window
        if slope < -0.01:
            return 'improving', slope  # H0 decreasing = better separation
        elif slope > 0.01:
            return 'degrading', slope
        return 'stable', slope

    def clear(self):
        """Clear all buffers."""
        self.direction_buffer.clear()
        self.h0_history.clear()
        self.merge_history.clear()

    def summary(self):
        """Print current PH status."""
        n_samples = sum(len(v) for v in self.direction_buffer.values())
        n_classes = sum(1 for v in self.direction_buffer.values() if v)
        h0 = self.h0_history[-1] if self.h0_history else 0
        trend, slope = self.get_h0_trend()

        print(f"  PH Module: {n_samples} samples, {n_classes}/{self.n_cls} classes")
        print(f"  H0_total: {h0:.4f}, trend: {trend} (slope={slope:.4f})")

        if self.merge_history:
            merges = self.merge_history[-1]
            top3 = sorted(merges)[:3]
            print(f"  Top-3 confused: {[(i,j,f'{d:.3f}') for d,i,j in top3]}")

        packet = self.get_telepathy_packet()
        if packet:
            print(f"  Telepathy packet: {[f'{d:.3f}' for d in packet[:5]]}...")
