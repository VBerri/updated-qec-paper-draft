from qec_baseline.qiskit_circuits import (
    build_repetition_syndrome_memory_circuit,
    build_unencoded_memory_control_circuit,
)
from qec_cloud.ibm_hardware import _bits_from_memory_str, _decode_encoded_shot, _decode_unencoded_shot


def test_corrected_encoded_circuit_structure():
    qc = build_repetition_syndrome_memory_circuit(rounds=3, delay_dt=256, logical_bit=0)
    assert qc.num_qubits == 5
    assert qc.num_clbits == 9  # 2*rounds syndrome + 3 final data
    ops = qc.count_ops()
    assert ops.get("measure", 0) >= 9
    assert ops.get("reset", 0) >= 3
    assert ops.get("delay", 0) >= 9


def test_unencoded_control_structure():
    qc = build_unencoded_memory_control_circuit(rounds=3, delay_dt=256, logical_bit=1)
    assert qc.num_qubits == 1
    assert qc.num_clbits == 1
    ops = qc.count_ops()
    assert ops.get("delay", 0) == 3
    assert ops.get("measure", 0) == 1


def test_decoder_helpers_parse_bits_and_score():
    bits = _bits_from_memory_str("101001")
    assert bits == [1, 0, 0, 1, 0, 1]

    # rounds=1 -> [s01,s12,d0,d1,d2], pick d bits all zero for logical 0 success
    encoded_bits = [0, 0, 0, 0, 0]
    assert _decode_encoded_shot(encoded_bits, rounds=1, prepared_logical_bit=0) == 1
    assert _decode_unencoded_shot([1], prepared_logical_bit=1) == 1
