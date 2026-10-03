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


def _data_and_ancilla_qubits(distance: int) -> tuple[list[int], list[int]]:
    if distance < 2:
        raise ValueError("distance must be at least 2")
    data = [2 * i for i in range(distance)]
    ancilla = [2 * i + 1 for i in range(distance - 1)]
    return data, ancilla


def _append_cx_layer(circuit: stim.Circuit, pairs: list[tuple[int, int]], p_two_qubit: float) -> None:
    targets: list[int] = []
    for control, target in pairs:
        targets.extend([control, target])
    circuit.append("CX", targets)
    if p_two_qubit > 0:
        circuit.append("DEPOLARIZE2", targets, [p_two_qubit])


def explicit_repetition_memory_circuit(
    distance: int,
    rounds: int,
    data_pauli_by_round: list[tuple[float, float, float]],
    measurement_flip_by_round: list[float],
    p_two_qubit: float = 0.0,
    p_reset_flip: float = 0.0,
    final_measure_flip: float | None = None,
) -> stim.Circuit:
    """Build a repetition-memory circuit with explicit data/ancilla maps and round-level noise."""
    if rounds <= 0:
        raise ValueError("rounds must be positive")
    if len(data_pauli_by_round) != rounds:
        raise ValueError("data_pauli_by_round length must equal rounds")
    if len(measurement_flip_by_round) != rounds:
        raise ValueError("measurement_flip_by_round length must equal rounds")

    data, ancilla = _data_and_ancilla_qubits(distance)
    left_layer = [(data[i], ancilla[i]) for i in range(len(ancilla))]
    right_layer = [(data[i + 1], ancilla[i]) for i in range(len(ancilla))]

    circuit = stim.Circuit()
    circuit.append("R", data + ancilla)
    if p_reset_flip > 0:
        circuit.append("X_ERROR", data + ancilla, [p_reset_flip])

    anc_count = len(ancilla)
    data_count = len(data)

    for r in range(rounds):
        px, py, pz = data_pauli_by_round[r]
        if px > 0 or py > 0 or pz > 0:
            for q in data:
                circuit.append("PAULI_CHANNEL_1", [q], [px, py, pz])

        circuit.append("TICK")
        _append_cx_layer(circuit, left_layer, p_two_qubit=p_two_qubit)
        circuit.append("TICK")
        _append_cx_layer(circuit, right_layer, p_two_qubit=p_two_qubit)
        circuit.append("TICK")

        p_meas = measurement_flip_by_round[r]
        if p_meas > 0:
            circuit.append("X_ERROR", ancilla, [p_meas])
        circuit.append("MR", ancilla)

        if r == 0:
            for j in range(anc_count):
                circuit.append("DETECTOR", [stim.target_rec(-(anc_count - j))])
        else:
            for j in range(anc_count):
                circuit.append(
                    "DETECTOR",
                    [
                        stim.target_rec(-(anc_count - j)),
                        stim.target_rec(-(2 * anc_count - j)),
                    ],
                )

    p_final = measurement_flip_by_round[-1] if final_measure_flip is None else final_measure_flip
    if p_final > 0:
        circuit.append("X_ERROR", data, [p_final])
    circuit.append("M", data)

    for j in range(anc_count):
        anc_offset = -(data_count + anc_count - j)
        left_data_offset = -(data_count - j)
        right_data_offset = -(data_count - (j + 1))
        circuit.append(
            "DETECTOR",
            [
                stim.target_rec(anc_offset),
                stim.target_rec(left_data_offset),
                stim.target_rec(right_data_offset),
            ],
        )

    # For this Z-memory benchmark, the observable is tracked by the final rightmost data readout.
    circuit.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], 0)
    return circuit


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
    p_meas = min(max(measurement_flip_probability, 0.0), 0.49)
    p_reset = min(max(px + py, 0.0), 0.49)
    p_twoq = min(max(px + py + pz, 0.0), 0.49)

    data_round = (float(px), float(py), float(pz))
    return explicit_repetition_memory_circuit(
        distance=distance,
        rounds=rounds,
        data_pauli_by_round=[data_round for _ in range(rounds)],
        measurement_flip_by_round=[p_meas for _ in range(rounds)],
        p_two_qubit=p_twoq,
        p_reset_flip=p_reset,
        final_measure_flip=p_meas,
    )
