from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .mwpm_decode import decode_logical_error_rate
from .noise_models import (
    biased_pauli_rates,
    make_heterogeneous_rates,
    make_temporal_drift_schedule,
)
from .stim_circuits import (
    biased_noise_repetition_approximation,
    generated_repetition_memory_circuit,
)


def run_stim_mwpm_experiments(
    shots: int,
    distances: Iterable[int] = (3, 5, 7, 9, 11),
    p_values: Iterable[float] = (0.001, 0.005, 0.01, 0.02),
    out_csv: str | Path = "results/stim_mwpm_results.csv",
) -> pd.DataFrame:
    rows = []
    for d in distances:
        rounds = d
        for p in p_values:
            circuit = generated_repetition_memory_circuit(distance=d, rounds=rounds, p=p)
            logical_error = decode_logical_error_rate(circuit, shots=shots)
            rows.append(
                {
                    "layer": "layer2",
                    "experiment": "stim_mwpm",
                    "distance": d,
                    "rounds": rounds,
                    "p": p,
                    "shots": shots,
                    "logical_error_rate": logical_error,
                }
            )

    df = pd.DataFrame(rows)
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df


def run_bias_sweep(
    shots: int,
    distances: Iterable[int],
    p_values: Iterable[float],
    bias_values: Iterable[float],
    out_csv: str | Path = "results/bias_sweep_results.csv",
) -> pd.DataFrame:
    rows = []
    for d in distances:
        rounds = d
        for p_total in p_values:
            for bias_z in bias_values:
                px, py, pz = biased_pauli_rates(p_total=p_total, bias_z=bias_z)
                p_meas = min(p_total, 0.49)
                circuit = biased_noise_repetition_approximation(
                    distance=d,
                    rounds=rounds,
                    px=px,
                    py=py,
                    pz=pz,
                    measurement_flip_probability=p_meas,
                )
                logical_error = decode_logical_error_rate(circuit, shots=shots)
                rows.append(
                    {
                        "layer": "layer2",
                        "experiment": "bias_sweep",
                        "distance": d,
                        "rounds": rounds,
                        "p_total": p_total,
                        "bias_z": bias_z,
                        "px": px,
                        "py": py,
                        "pz": pz,
                        "shots": shots,
                        "logical_error_rate": logical_error,
                    }
                )

    df = pd.DataFrame(rows)
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df


def run_heterogeneous_noise(
    shots: int,
    distances: Iterable[int],
    p_values: Iterable[float],
    spreads: Iterable[float] = (0.0, 0.25, 0.5, 1.0),
    seed: int = 12345,
    out_csv: str | Path = "results/heterogeneous_noise_results.csv",
) -> pd.DataFrame:
    rows = []
    idx = 0
    for d in distances:
        rounds = d
        for p_mean in p_values:
            for spread in spreads:
                rates = make_heterogeneous_rates(distance=d, p_mean=p_mean, spread=spread, seed=seed + idx)
                idx += 1
                p_eff = float(np.mean(rates))
                p_std = float(np.std(rates))
                circuit = generated_repetition_memory_circuit(distance=d, rounds=rounds, p=min(p_eff, 0.49))
                logical_error = decode_logical_error_rate(circuit, shots=shots)
                rows.append(
                    {
                        "layer": "layer2",
                        "experiment": "heterogeneous_noise",
                        "distance": d,
                        "rounds": rounds,
                        "p_mean": p_mean,
                        "spread": spread,
                        "effective_p_mean": p_eff,
                        "effective_p_std": p_std,
                        "shots": shots,
                        "logical_error_rate": logical_error,
                    }
                )

    df = pd.DataFrame(rows)
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df


def run_temporal_drift(
    shots: int,
    distances: Iterable[int],
    p_values: Iterable[float],
    seed: int = 12345,
    out_csv: str | Path = "results/temporal_drift_results.csv",
) -> pd.DataFrame:
    snapshots = [
        {"snapshot": "snapshot_0_normal", "data_factor": 1.0, "meas_factor": 1.0, "bad_qubit_factor": 1.0},
        {"snapshot": "snapshot_1_meas_worse", "data_factor": 1.0, "meas_factor": 1.25, "bad_qubit_factor": 1.0},
        {"snapshot": "snapshot_2_one_bad_qubit", "data_factor": 1.0, "meas_factor": 1.0, "bad_qubit_factor": 2.5},
        {"snapshot": "snapshot_3_global_drift_up", "data_factor": 1.35, "meas_factor": 1.2, "bad_qubit_factor": 1.0},
        {"snapshot": "snapshot_4_recovery", "data_factor": 1.05, "meas_factor": 1.0, "bad_qubit_factor": 1.0},
    ]

    rows = []
    ctr = 0
    for d in distances:
        rounds = d
        for p_mean in p_values:
            drift_schedule = make_temporal_drift_schedule(
                rounds=rounds,
                p_mean=p_mean,
                drift_strength=0.35,
                seed=seed + ctr,
            )
            ctr += 1
            base_data = float(np.mean(drift_schedule))

            for s in snapshots:
                one_bad_qubit_boost = (s["bad_qubit_factor"] - 1.0) * (p_mean / max(d, 1))
                p_data = min(max(base_data * s["data_factor"] + one_bad_qubit_boost, 0.0), 0.49)
                p_meas = min(max(p_mean * s["meas_factor"], 0.0), 0.49)
                circuit = generated_repetition_memory_circuit(distance=d, rounds=rounds, p=p_data)
                logical_error = decode_logical_error_rate(circuit, shots=shots)
                rows.append(
                    {
                        "layer": "layer2",
                        "experiment": "temporal_drift",
                        "distance": d,
                        "rounds": rounds,
                        "p_mean": p_mean,
                        "snapshot": s["snapshot"],
                        "p_data_effective": p_data,
                        "p_meas_effective": p_meas,
                        "shots": shots,
                        "logical_error_rate": logical_error,
                    }
                )

    df = pd.DataFrame(rows)
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df
