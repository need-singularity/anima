"""Tests that SOC constants are loaded from consciousness_laws.json, not hardcoded."""
import json
import os
import pytest

def test_soc_constants_from_json():
    """All SOC constants in consciousness_laws.py match consciousness_laws.json."""
    from consciousness_laws import (
        SOC_EMA_FAST, SOC_EMA_SLOW, SOC_EMA_GLACIAL, SOC_MEMORY_BLEND,
        SOC_MEMORY_STRENGTH_BASE, SOC_MEMORY_STRENGTH_RANGE,
        SOC_PERTURBATION_BASE, SOC_PERTURBATION_RANGE,
        SOC_BURST_EXPONENT, SOC_BURST_DENOM, SOC_BURST_CAP,
        BIO_NOISE_BASE, BIO_NOISE_SPIKE_PROB, BIO_NOISE_SPIKE_RATE,
    )
    # Load JSON directly
    json_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'consciousness_laws.json')
    with open(json_path) as f:
        data = json.load(f)
    psi = {k: v['value'] for k, v in data['psi_constants'].items()}

    assert SOC_EMA_FAST == psi['soc_ema_fast']
    assert SOC_EMA_SLOW == psi['soc_ema_slow']
    assert SOC_EMA_GLACIAL == psi['soc_ema_glacial']
    assert SOC_MEMORY_BLEND == psi['soc_memory_blend']
    assert SOC_MEMORY_STRENGTH_BASE == psi['soc_memory_strength_base']
    assert SOC_MEMORY_STRENGTH_RANGE == psi['soc_memory_strength_range']
    assert SOC_PERTURBATION_BASE == psi['soc_perturbation_base']
    assert SOC_PERTURBATION_RANGE == psi['soc_perturbation_range']
    assert SOC_BURST_EXPONENT == psi['soc_burst_exponent']
    assert SOC_BURST_DENOM == psi['soc_burst_denom']
    assert SOC_BURST_CAP == psi['soc_burst_cap']
    assert BIO_NOISE_BASE == psi['bio_noise_base']
    assert BIO_NOISE_SPIKE_PROB == psi['bio_noise_spike_prob']
    assert BIO_NOISE_SPIKE_RATE == psi['bio_noise_spike_rate']

def test_consciousness_engine_uses_json_constants():
    """ConsciousnessEngine imports SOC constants from consciousness_laws, not hardcoded."""
    import consciousness_engine
    source = open(consciousness_engine.__file__).read()
    # Should import from consciousness_laws
    assert 'SOC_EMA_FAST' in source
    assert 'SOC_BURST_EXPONENT' in source
    assert 'BIO_NOISE_BASE' in source
    # Should NOT have hardcoded values for these params
    # (0.05 for ema_fast could appear in other contexts, so check specific patterns)
    assert 'burst = (last_aval ** 1.15)' not in source  # should use SOC_BURST_EXPONENT
    assert 'base_noise = 0.015' not in source  # should use BIO_NOISE_BASE
