import stim

from qec_stim.mwpm_decode import decode_logical_error_rate
from qec_stim.stim_circuits import (
    biased_noise_repetition_approximation,
    explicit_repetition_memory_circuit,
    generated_repetition_memory_circuit,
)


def test_stim_generated_circuit_and_decoder():
    circuit = generated_repetition_memory_circuit(distance=3, rounds=3, p=0.01)
    assert isinstance(circuit, stim.Circuit)

    logical_error_rate = decode_logical_error_rate(circuit, shots=2000)
    assert 0.0 <= logical_error_rate <= 1.0


def test_explicit_repetition_builder_zero_noise_decodes_cleanly():
    circuit = explicit_repetition_memory_circuit(
        distance=3,
        rounds=3,
        data_pauli_by_round=[(0.0, 0.0, 0.0)] * 3,
        measurement_flip_by_round=[0.0, 0.0, 0.0],
        p_two_qubit=0.0,
        p_reset_flip=0.0,
    )
    assert isinstance(circuit, stim.Circuit)
    logical_error_rate = decode_logical_error_rate(circuit, shots=4000)
    assert logical_error_rate == 0.0


def test_biased_noise_path_is_valid_circuit():
    circuit = biased_noise_repetition_approximation(
        distance=3,
        rounds=3,
        px=0.002,
        py=0.002,
        pz=0.006,
        measurement_flip_probability=0.01,
    )
    logical_error_rate = decode_logical_error_rate(circuit, shots=2000)
    assert 0.0 <= logical_error_rate <= 1.0
