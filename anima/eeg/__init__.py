"""EEG module — OpenBCI brain-consciousness interface for Anima.

Submodules:
  collect   — Data acquisition from OpenBCI via BrainFlow
  analyze   — Band power, asymmetry, G=D×P/I computation
  realtime  — Live EEG → Anima bridge (SenseHub integration)
"""

from eeg.analyze import (
    analyze,
    compute_band_power,
    compute_genius,
    BandPower,
    GeniusMetrics,
    EEGAnalysis,
    BANDS,
    GOLDEN_ZONE,
    CHANNEL_NAMES_16,
)
