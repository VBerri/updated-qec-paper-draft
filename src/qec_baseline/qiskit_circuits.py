from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister


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


def build_repetition_syndrome_memory_circuit(
    rounds: int,
    delay_dt: int,
    logical_bit: int = 0,
) -> QuantumCircuit:
    """Three-data/two-ancilla repetition memory with repeated syndrome extraction."""
    if rounds <= 0:
        raise ValueError("rounds must be positive")
    if delay_dt < 0:
        raise ValueError("delay_dt must be non-negative")
    if logical_bit not in {0, 1}:
        raise ValueError("logical_bit must be 0 or 1")

    data = QuantumRegister(3, "data")
    anc = QuantumRegister(2, "anc")
    # One flat memory register: [syndrome bits by round][final data bits].
    memory = ClassicalRegister(2 * rounds + 3, "m")
    qc = QuantumCircuit(data, anc, memory)

    if logical_bit == 1:
        qc.x(data)

    for r in range(rounds):
        if delay_dt > 0:
            for q in data:
                qc.delay(delay_dt, q, unit="dt")

        qc.cx(data[0], anc[0])
        qc.cx(data[1], anc[0])
        qc.cx(data[1], anc[1])
        qc.cx(data[2], anc[1])

        qc.measure(anc[0], memory[2 * r])
        qc.measure(anc[1], memory[2 * r + 1])
        qc.reset(anc)

    qc.measure(data[0], memory[2 * rounds + 0])
    qc.measure(data[1], memory[2 * rounds + 1])
    qc.measure(data[2], memory[2 * rounds + 2])
    return qc


def build_unencoded_memory_control_circuit(
    rounds: int,
    delay_dt: int,
    logical_bit: int = 0,
    total_delay_dt: int | None = None,
) -> QuantumCircuit:
    """Single-qubit duration-matched memory control circuit.

    The default behavior preserves the legacy API: a delay of ``delay_dt`` is inserted
    once per round. When ``total_delay_dt`` is specified, the control uses the exact
    elapsed memory duration implied by the encoded circuit comparison interval rather
    than only the nominal per-round multiplication.
    """
    if rounds <= 0:
        raise ValueError("rounds must be positive")
    if delay_dt < 0:
        raise ValueError("delay_dt must be non-negative")
    if logical_bit not in {0, 1}:
        raise ValueError("logical_bit must be 0 or 1")

    data = QuantumRegister(1, "data")
    memory = ClassicalRegister(1, "m")
    qc = QuantumCircuit(data, memory)

    if logical_bit == 1:
        qc.x(data[0])

    if total_delay_dt is None:
        for _ in range(rounds):
            if delay_dt > 0:
                qc.delay(delay_dt, data[0], unit="dt")
    else:
        if total_delay_dt < 0:
            raise ValueError("total_delay_dt must be non-negative")
        if total_delay_dt > 0:
            qc.delay(total_delay_dt, data[0], unit="dt")

    qc.measure(data[0], memory[0])
    return qc
