from qiskit import QuantumCircuit


def build_repetition_memory_circuit(code_size: int, idle_steps: int, basis: str) -> QuantumCircuit:
    """Build a simple repetition memory circuit in either Z or X protected basis."""
    if basis not in {"Z", "X"}:
        raise ValueError("basis must be 'Z' or 'X'")

    qc = QuantumCircuit(code_size, code_size)

    if basis == "X":
        qc.h(range(code_size))

    for _ in range(idle_steps):
        qc.id(range(code_size))

    if basis == "X":
        qc.h(range(code_size))

    qc.measure(range(code_size), range(code_size))
    return qc
