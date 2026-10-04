import numpy as np

from qec_stim.noise_models import (
    biased_pauli_rates,
    make_heterogeneous_rates,
    uniform_depolarizing_rates,
)
from qec_stim.stim_circuits import biased_noise_repetition_approximation


def test_biased_pauli_rates():
    px, py, pz = biased_pauli_rates(p_total=0.03, bias_z=10)
    assert abs((px + py + pz) - 0.03) < 1e-12
    assert pz > px


def test_uniform_depolarizing_rates():
    px, py, pz = uniform_depolarizing_rates(0.03)
    assert np.isclose(px, py)
    assert np.isclose(py, pz)


def test_heterogeneous_rates_behavior():
    r0 = make_heterogeneous_rates(distance=7, p_mean=0.01, spread=0.0, seed=1)
    r1 = make_heterogeneous_rates(distance=7, p_mean=0.01, spread=0.5, seed=1)
    assert np.allclose(r0, 0.01)
    assert np.std(r1) > 0


def test_biased_noise_repetition_approximation_keeps_fixed_reset_and_gate_noise():
    counts = []
    for px, py, pz in [(0.005, 0.0, 0.0), (0.02, 0.0, 0.0), (0.0, 0.02, 0.0)]:
        circuit = biased_noise_repetition_approximation(
            distance=3,
            rounds=2,
            px=px,
            py=py,
            pz=pz,
            measurement_flip_probability=1e-3,
            p_reset_flip=1e-3,
            p_two_qubit=1e-3,
        )
        x_error_ops = sum(
            1
            for op in circuit.flattened().flattened_operations()
            if op[0] == "X_ERROR"
        )
        counts.append(x_error_ops)
    assert len(set(counts)) == 1
