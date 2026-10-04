from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit_aer import AerSimulator

from qec_baseline.qiskit_circuits import (
    build_repetition_syndrome_memory_circuit,
    build_unencoded_memory_control_circuit,
)
from qec_cloud.ibm_hardware import (
    _bits_from_memory_str,
    _decode_encoded_shot,
    _decode_final_data_majority_bit,
    _decode_history_matching_bit,
    _decode_unencoded_shot,
    _detection_events_from_bits,
)


def _single_shot_bits(circuit: QuantumCircuit) -> list[int]:
    sim = AerSimulator()
    tqc = transpile(circuit, sim)
    result = sim.run(tqc, shots=1).result()
    counts = result.get_counts(0)
    assert sum(counts.values()) == 1
    bitstring = next(iter(counts.keys()))
    return _bits_from_memory_str(bitstring)


def _build_fault_injected_encoded(
    rounds: int,
    logical_bit: int,
    data_fault_qubit: int | None = None,
    data_fault_stage: int | None = None,
    meas_fault_ancilla: int | None = None,
    meas_fault_round: int | None = None,
    final_readout_flip_qubit: int | None = None,
) -> QuantumCircuit:
    data = QuantumRegister(3, "data")
    anc = QuantumRegister(2, "anc")
    memory = ClassicalRegister(2 * rounds + 3, "m")
    qc = QuantumCircuit(data, anc, memory)

    if logical_bit == 1:
        qc.x(data)

    for r in range(rounds):
        if data_fault_qubit is not None and data_fault_stage == r:
            qc.x(data[data_fault_qubit])

        qc.cx(data[0], anc[0])
        qc.cx(data[1], anc[0])
        qc.cx(data[1], anc[1])
        qc.cx(data[2], anc[1])

        if meas_fault_ancilla is not None and meas_fault_round == r:
            qc.x(anc[meas_fault_ancilla])

        qc.measure(anc[0], memory[2 * r])
        qc.measure(anc[1], memory[2 * r + 1])
        qc.reset(anc)

    if data_fault_qubit is not None and data_fault_stage == rounds:
        qc.x(data[data_fault_qubit])

    if final_readout_flip_qubit is not None:
        qc.x(data[final_readout_flip_qubit])

    qc.measure(data[0], memory[2 * rounds + 0])
    qc.measure(data[1], memory[2 * rounds + 1])
    qc.measure(data[2], memory[2 * rounds + 2])
    return qc


def test_corrected_encoded_circuit_structure():
    qc = build_repetition_syndrome_memory_circuit(rounds=3, delay_dt=256, logical_bit=0)
    assert qc.num_qubits == 5
    assert qc.num_clbits == 9
    ops = qc.count_ops()
    assert ops.get("measure", 0) >= 9
    assert ops.get("reset", 0) >= 3


def test_unencoded_control_structure_and_total_delay_mode():
    qc = build_unencoded_memory_control_circuit(rounds=3, delay_dt=256, logical_bit=1)
    assert qc.num_qubits == 1
    assert qc.num_clbits == 1
    ops = qc.count_ops()
    assert ops.get("delay", 0) == 3

    matched = build_unencoded_memory_control_circuit(rounds=3, delay_dt=256, logical_bit=1, total_delay_dt=777)
    matched_ops = matched.count_ops()
    assert matched_ops.get("delay", 0) == 1


def test_no_noise_decodes_both_logicals_and_rounds():
    for rounds in (1, 3):
        for logical_bit in (0, 1):
            qc = build_repetition_syndrome_memory_circuit(rounds=rounds, delay_dt=0, logical_bit=logical_bit)
            bits = _single_shot_bits(qc)
            assert _decode_final_data_majority_bit(bits, rounds=rounds) == logical_bit
            assert _decode_history_matching_bit(bits, rounds=rounds) == logical_bit


def test_single_data_faults_each_qubit_each_stage():
    rounds = 3
    for logical_bit in (0, 1):
        for qubit in (0, 1, 2):
            for stage in (0, 1, 2, 3):
                qc = _build_fault_injected_encoded(
                    rounds=rounds,
                    logical_bit=logical_bit,
                    data_fault_qubit=qubit,
                    data_fault_stage=stage,
                )
                bits = _single_shot_bits(qc)
                assert _decode_final_data_majority_bit(bits, rounds=rounds) == logical_bit
                assert _decode_history_matching_bit(bits, rounds=rounds) == logical_bit


def test_single_measurement_faults_each_ancilla_each_round():
    rounds = 3
    for logical_bit in (0, 1):
        for ancilla in (0, 1):
            for round_idx in (0, 1, 2):
                qc = _build_fault_injected_encoded(
                    rounds=rounds,
                    logical_bit=logical_bit,
                    meas_fault_ancilla=ancilla,
                    meas_fault_round=round_idx,
                )
                bits = _single_shot_bits(qc)
                assert _decode_final_data_majority_bit(bits, rounds=rounds) == logical_bit
                assert _decode_history_matching_bit(bits, rounds=rounds) == logical_bit


def test_final_data_readout_flip_and_boundaries():
    rounds = 3
    logical_bit = 0
    for qubit in (0, 1, 2):
        qc = _build_fault_injected_encoded(
            rounds=rounds,
            logical_bit=logical_bit,
            final_readout_flip_qubit=qubit,
        )
        bits = _single_shot_bits(qc)
        det = _detection_events_from_bits(bits, rounds=rounds)
        assert len(det) == rounds + 1
        assert _decode_history_matching_bit(bits, rounds=rounds) == logical_bit


def test_selected_two_fault_histories_use_timing_information():
    rounds = 3
    bits_a = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    bits_b = [0, 0, 0, 0, 0, 1, 0, 1, 0]

    assert _decode_final_data_majority_bit(bits_a, rounds=rounds) == _decode_final_data_majority_bit(bits_b, rounds=rounds)
    # These fixtures pin expected outputs for two histories with identical final data bits.
    assert _decode_history_matching_bit(bits_a, rounds=rounds) == 0
    assert _decode_history_matching_bit(bits_b, rounds=rounds) == 1


def test_invalid_or_truncated_records_raise():
    try:
        _decode_history_matching_bit([0, 1, 0], rounds=3)
        assert False, "expected ValueError"
    except ValueError:
        pass

    try:
        _decode_unencoded_shot([], prepared_logical_bit=0)
        assert False, "expected ValueError"
    except ValueError:
        pass

    try:
        _bits_from_memory_str("010210")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_decoder_independence_from_prepared_answer():
    bits = [0, 0, 0, 0, 0]
    a = _decode_encoded_shot(bits, rounds=1, prepared_logical_bit=0)
    b = _decode_encoded_shot(bits, rounds=1, prepared_logical_bit=1)
    assert a == b
