from pathlib import Path
from typing import Iterable

import pandas as pd
from qiskit import transpile
from qiskit_aer import AerSimulator

from .majority_decode import logical_success_from_counts
from .qiskit_circuits import build_repetition_memory_circuit
from .qiskit_noise import build_idle_noise_model
from .theory import repetition_success_probability

DEFAULT_P_VALUES = [0.00, 0.01, 0.02, 0.04, 0.06, 0.08, 0.10, 0.11, 0.12, 0.13, 0.14, 0.15]


def run_baseline_experiments(
    shots: int,
    idle_steps: int = 4,
    seed: int = 12345,
    p_values: Iterable[float] | None = None,
    code_sizes: Iterable[int] = (1, 3, 5),
    out_csv: str | Path = "results/baseline_qiskit_results.csv",
) -> pd.DataFrame:
    p_values = list(DEFAULT_P_VALUES if p_values is None else p_values)
    rows = []

    experiments = [
        ("bit_flip", "Z"),
        ("phase_flip", "X"),
        ("depolarizing", "Z"),
    ]

    for noise_type, basis in experiments:
        for code_size in code_sizes:
            for p in p_values:
                circuit = build_repetition_memory_circuit(code_size=code_size, idle_steps=idle_steps, basis=basis)
                noise_model = build_idle_noise_model(noise_type=noise_type, p=p)
                simulator = AerSimulator(noise_model=noise_model, seed_simulator=seed)
                compiled = transpile(
                    circuit,
                    simulator,
                    basis_gates=noise_model.basis_gates,
                    optimization_level=0,
                    seed_transpiler=seed,
                )
                result = simulator.run(compiled, shots=shots).result()
                counts = result.get_counts()

                success = logical_success_from_counts(counts, expected_logical="0")
                logical_error = 1.0 - success

                theory_success = None
                if noise_type in {"bit_flip", "phase_flip"}:
                    theory_success = repetition_success_probability(code_size=code_size, p=p, idle_steps=idle_steps)

                rows.append(
                    {
                        "layer": "layer1",
                        "experiment": noise_type,
                        "basis": basis,
                        "code_size": code_size,
                        "p": p,
                        "idle_steps": idle_steps,
                        "shots": shots,
                        "logical_success_probability": success,
                        "logical_error_rate": logical_error,
                        "theory_success_probability": theory_success,
                    }
                )

    df = pd.DataFrame(rows)
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df
