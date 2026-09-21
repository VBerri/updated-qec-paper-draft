from __future__ import annotations

import numpy as np


def biased_pauli_rates(p_total: float, bias_z: float) -> tuple[float, float, float]:
    """
    Return px, py, pz where bias_z approximately means pz / px.

    px = p_total / (bias_z + 2)
    py = p_total / (bias_z + 2)
    pz = bias_z * p_total / (bias_z + 2)
    """
    if p_total < 0:
        raise ValueError("p_total must be non-negative")
    if bias_z <= 0:
        raise ValueError("bias_z must be positive")

    px = p_total / (bias_z + 2)
    py = p_total / (bias_z + 2)
    pz = bias_z * p_total / (bias_z + 2)
    return float(px), float(py), float(pz)


def uniform_depolarizing_rates(p_total: float) -> tuple[float, float, float]:
    if p_total < 0:
        raise ValueError("p_total must be non-negative")
    return p_total / 3.0, p_total / 3.0, p_total / 3.0


def make_heterogeneous_rates(distance: int, p_mean: float, spread: float, seed: int) -> np.ndarray:
    """Create per-qubit rates around p_mean using a mean-one lognormal factor."""
    if distance <= 0:
        raise ValueError("distance must be positive")
    if p_mean < 0:
        raise ValueError("p_mean must be non-negative")
    if spread < 0:
        raise ValueError("spread must be non-negative")

    rng = np.random.default_rng(seed)
    if spread == 0:
        rates = np.full(distance, p_mean)
    else:
        factors = rng.lognormal(mean=-0.5 * spread * spread, sigma=spread, size=distance)
        rates = p_mean * factors
    return np.clip(rates, 0.0, 0.49)


def make_temporal_drift_schedule(rounds: int, p_mean: float, drift_strength: float, seed: int) -> np.ndarray:
    """Synthetic temporal drift around p_mean with a trend and random fluctuation."""
    if rounds <= 0:
        raise ValueError("rounds must be positive")

    rng = np.random.default_rng(seed)
    t = np.arange(rounds)
    sinusoid = np.sin(2 * np.pi * t / max(rounds, 2))
    trend = np.linspace(-0.5, 0.5, rounds)
    jitter = rng.normal(0.0, 0.15, size=rounds)
    rel = drift_strength * (0.6 * sinusoid + 0.3 * trend + 0.1 * jitter)
    schedule = p_mean * (1.0 + rel)
    return np.clip(schedule, 0.0, 0.49)
