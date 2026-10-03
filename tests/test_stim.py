import stim

from qec_stim.mwpm_decode import decode_logical_error_rate
from qec_stim.stim_circuits import generated_repetition_memory_circuit


def test_stim_generated_circuit_and_decoder():
    circuit = generated_repetition_memory_circuit(distance=3, rounds=3, p=0.01)
    assert isinstance(circuit, stim.Circuit)

    logical_error_rate = decode_logical_error_rate(circuit, shots=2000)
    assert 0.0 <= logical_error_rate <= 1.0
