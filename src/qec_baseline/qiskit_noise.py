from qiskit_aer.noise import NoiseModel, depolarizing_error, pauli_error


def build_idle_noise_model(noise_type: str, p: float) -> NoiseModel:
    """Attach a single-qubit noise channel to idle gates."""
    if p < 0 or p > 1:
        raise ValueError("p must be in [0, 1]")

    noise_model = NoiseModel()
    if noise_type == "bit_flip":
        channel = pauli_error([("X", p), ("I", 1 - p)])
    elif noise_type == "phase_flip":
        channel = pauli_error([("Z", p), ("I", 1 - p)])
    elif noise_type == "depolarizing":
        channel = depolarizing_error(p, 1)
    else:
        raise ValueError(f"Unsupported noise type: {noise_type}")

    noise_model.add_all_qubit_quantum_error(channel, "id")
    return noise_model
