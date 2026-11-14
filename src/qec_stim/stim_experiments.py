from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .decoder_comparison import evaluate_decoders_on_shared_samples
from .mwpm_decode import decode_logical_error_rate, decode_logical_stats
from .noise_models import (
    biased_pauli_rates,
    make_heterogeneous_rates,
    make_temporal_drift_schedule,
)
from .stim_circuits import (
    biased_noise_repetition_approximation,
    explicit_repetition_memory_circuit,
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
    seed: int | None = None,
    out_csv: str | Path = "results/bias_sweep_results.csv",
) -> pd.DataFrame:
    rows = []
    for d in distances:
        rounds = d
        for p_total in p_values:
            for bias_z in bias_values:
                px, py, pz = biased_pauli_rates(p_total=p_total, bias_z=bias_z)
                p_meas = 1e-3
                p_reset = 1e-3
                p_two_qubit = 1e-3
                circuit = biased_noise_repetition_approximation(
                    distance=d,
                    rounds=rounds,
                    px=px,
                    py=py,
                    pz=pz,
                    measurement_flip_probability=p_meas,
                    p_reset_flip=p_reset,
                    p_two_qubit=p_two_qubit,
                )
                stats = decode_logical_stats(circuit, shots=shots, seed=seed)
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
                        "seed": seed,
                        "failures": int(stats["failures"]),
                        "logical_error_rate": float(stats["logical_error_rate"]),
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
    for d in distances:
        rounds = d
        for p_mean in p_values:
            for spread in spreads:
                data_rates = make_heterogeneous_rates(distance=d, p_mean=p_mean, spread=spread, seed=seed + d)
                round_rates = [[(float(rx), 0.0, 0.0) for rx in data_rates] for _ in range(rounds)]
                measurement_schedule = [0.001 for _ in range(rounds)]

                heterogeneous_circuit = explicit_repetition_memory_circuit(
                    distance=d,
                    rounds=rounds,
                    data_pauli_by_round=round_rates,
                    measurement_flip_by_round=measurement_schedule,
                    p_two_qubit=0.001,
                    p_reset_flip=0.001,
                    final_measure_flip=0.001,
                )

                method_rows, _ = evaluate_decoders_on_shared_samples(
                    sampling_circuit=heterogeneous_circuit,
                    decoder_circuits={
                        "mwpm": heterogeneous_circuit,
                    },
                    shots=shots,
                    seed=seed,
                    include_final_data_majority=True,
                    include_detector_count_heuristic=False,
                    prepared_logical_bit=0,
                )

                for m in method_rows:
                    rows.append(
                        {
                            "layer": "layer2",
                            "experiment": "heterogeneous_noise",
                            "distance": d,
                            "rounds": rounds,
                            "p_mean": p_mean,
                            "spread": float(spread),
                            "effective_p_mean": float(np.mean(data_rates)),
                            "effective_p_std": float(np.std(data_rates)),
                            "max_qubit_rate": float(np.max(data_rates)),
                            "min_qubit_rate": float(np.min(data_rates)),
                            "shots": shots,
                            "seed": seed,
                            **m,
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
    rows = []
    for d in distances:
        rounds = d
        for p_mean in p_values:
            snapshot_schedules = {
                "snapshot_0": {
                    "data": make_temporal_drift_schedule(rounds, p_mean, drift_strength=0.0, seed=seed),
                    "meas": np.full(rounds, 0.001, dtype=float),
                },
                "snapshot_1": {
                    "data": make_temporal_drift_schedule(rounds, p_mean, drift_strength=0.05, seed=seed + 1),
                    "meas": np.full(rounds, 0.002, dtype=float),
                },
                "snapshot_2": {
                    "data": make_temporal_drift_schedule(rounds, p_mean, drift_strength=0.08, seed=seed + 2),
                    "meas": np.full(rounds, 0.001, dtype=float),
                },
                "snapshot_3": {
                    "data": make_temporal_drift_schedule(rounds, p_mean, drift_strength=0.18, seed=seed + 3),
                    "meas": np.full(rounds, 0.0025, dtype=float),
                },
                "snapshot_4": {
                    "data": make_temporal_drift_schedule(rounds, p_mean, drift_strength=0.03, seed=seed + 4),
                    "meas": np.full(rounds, 0.0012, dtype=float),
                },
            }

            snapshot_schedules["snapshot_2"]["data"][d // 2] = min(0.49, p_mean * 2.5)

            for scenario_name, payload in snapshot_schedules.items():
                data_schedule = np.clip(payload["data"], 0.0, 0.49)
                measurement_schedule = np.clip(payload["meas"], 0.0, 0.49)
                true_schedule_circuit = explicit_repetition_memory_circuit(
                    distance=d,
                    rounds=rounds,
                    data_pauli_by_round=[(float(p_data), 0.0, 0.0) for p_data in data_schedule],
                    measurement_flip_by_round=[float(x) for x in measurement_schedule],
                    p_two_qubit=0.001,
                    p_reset_flip=0.001,
                    final_measure_flip=float(measurement_schedule[-1]),
                )

                nominal_constant_circuit = explicit_repetition_memory_circuit(
                    distance=d,
                    rounds=rounds,
                    data_pauli_by_round=[(float(np.mean(data_schedule)), 0.0, 0.0) for _ in range(rounds)],
                    measurement_flip_by_round=[float(np.mean(measurement_schedule)) for _ in range(rounds)],
                    p_two_qubit=0.001,
                    p_reset_flip=0.001,
                    final_measure_flip=float(np.mean(measurement_schedule)),
                )

                method_rows, _ = evaluate_decoders_on_shared_samples(
                    sampling_circuit=true_schedule_circuit,
                    decoder_circuits={
                        "mwpm": nominal_constant_circuit,
                        "weighted_calibration_informed_mwpm": true_schedule_circuit,
                    },
                    shots=shots,
                    seed=seed,
                    include_final_data_majority=True,
                    include_detector_count_heuristic=False,
                    prepared_logical_bit=0,
                )

                for m in method_rows:
                    rows.append(
                        {
                            "layer": "layer2",
                            "experiment": "temporal_drift_schedule",
                            "distance": d,
                            "rounds": rounds,
                            "p_mean": p_mean,
                            "snapshot": scenario_name,
                            "schedule_data_mean": float(np.mean(data_schedule)),
                            "schedule_data_std": float(np.std(data_schedule)),
                            "schedule_meas_mean": float(np.mean(measurement_schedule)),
                            "schedule_meas_std": float(np.std(measurement_schedule)),
                            "shots": shots,
                            "seed": seed,
                            **m,
                        }
                    )

    df = pd.DataFrame(rows)
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df
