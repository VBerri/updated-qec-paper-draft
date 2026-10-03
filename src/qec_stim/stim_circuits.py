from __future__ import annotations

import stim


def generated_repetition_memory_circuit(distance: int, rounds: int, p: float) -> stim.Circuit:
    return stim.Circuit.generated(
        "repetition_code:memory",
        distance=distance,
        rounds=rounds,
        after_clifford_depolarization=p,
        before_round_data_depolarization=p,
        before_measure_flip_probability=p,
        after_reset_flip_probability=p,
    )


def biased_noise_repetition_approximation(
    distance: int,
    rounds: int,
    px: float,
    py: float,
    pz: float,
    measurement_flip_probability: float,
) -> stim.Circuit:
    """
    Approximate biased behavior while preserving robust detector structure.

    We use Stim's generated repetition memory circuit and map bias into effective
    channel strengths affecting X-like logical flips and measurement reliability.
    """
    p_data_effective = min(max(px + py, 0.0), 0.49)
    p_meas = min(max(measurement_flip_probability, 0.0), 0.49)
    p_reset = min(max(px + py, 0.0), 0.49)

    circuit = stim.Circuit.generated(
        "repetition_code:memory",
        distance=distance,
        rounds=rounds,
        after_clifford_depolarization=p_data_effective,
        before_round_data_depolarization=p_data_effective,
        before_measure_flip_probability=p_meas,
        after_reset_flip_probability=p_reset,
    )

    # Additional end-of-circuit single-qubit biased channel approximation using PAULI_CHANNEL_1.
    for _ in range(rounds):
        for q in range(distance):
            circuit.append("PAULI_CHANNEL_1", [q], [px, py, pz])
    return circuit
