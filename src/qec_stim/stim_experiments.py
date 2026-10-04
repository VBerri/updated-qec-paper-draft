from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .decoder_comparison import evaluate_decoders_on_shared_samples
from .mwpm_decode import decode_logical_stats
from .noise_models import (
    biased_pauli_rates,
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
    seed: int = 12345,
    out_csv: str | Path = "results/heterogeneous_noise_results.csv",
) -> pd.DataFrame:
    rows = []
    pairwise_rows = []

    def _same_mean_local_defect_rates(distance: int, p_mean: float, defect_index: int, defect_factor: float = 2.5):
        if distance <= 1:
            raise ValueError("distance must be > 1 for local-defect design")
        others = p_mean * (distance - defect_factor) / (distance - 1)
        base = np.full(distance, others, dtype=float)
        base[defect_index] = defect_factor * p_mean
        return np.clip(base, 0.0, 0.49)

    for d in distances:
        rounds = d
        center_idx = d // 2
        edge_idx = 0
        for p_mean in p_values:
            scenarios = [
                ("uniform_control", np.full(d, p_mean, dtype=float)),
                ("local_defect_edge", _same_mean_local_defect_rates(d, p_mean, edge_idx)),
                ("local_defect_center", _same_mean_local_defect_rates(d, p_mean, center_idx)),
            ]

            for scenario_name, data_rates in scenarios:
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

                nominal_uniform_circuit = explicit_repetition_memory_circuit(
                    distance=d,
                    rounds=rounds,
                    data_pauli_by_round=[(float(p_mean), 0.0, 0.0) for _ in range(rounds)],
                    measurement_flip_by_round=measurement_schedule,
                    p_two_qubit=0.001,
                    p_reset_flip=0.001,
                    final_measure_flip=0.001,
                )

                method_rows, pairwise = evaluate_decoders_on_shared_samples(
                    sampling_circuit=heterogeneous_circuit,
                    decoder_circuits={
                        "unweighted_mwpm": heterogeneous_circuit,
                        "mwpm_nominal_uniform_model": nominal_uniform_circuit,
                        "mwpm_oracle_heterogeneous_model": heterogeneous_circuit,
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
                            "experiment": "heterogeneous_noise_same_mean",
                            "distance": d,
                            "rounds": rounds,
                            "p_mean": p_mean,
                            "scenario": scenario_name,
                            "effective_p_mean": float(np.mean(data_rates)),
                            "effective_p_std": float(np.std(data_rates)),
                            "defect_index": int(np.argmax(data_rates)),
                            "shots": shots,
                            "seed": seed,
                            **m,
                        }
                    )
                for pw in pairwise:
                    pairwise_rows.append(
                        {
                            "layer": "layer2",
                            "experiment": "heterogeneous_noise_same_mean_pairwise",
                            "distance": d,
                            "rounds": rounds,
                            "p_mean": p_mean,
                            "scenario": scenario_name,
                            "effective_p_mean": float(np.mean(data_rates)),
                            "effective_p_std": float(np.std(data_rates)),
                            "defect_index": int(np.argmax(data_rates)),
                            "shots": shots,
                            "seed": seed,
                            **pw,
                        }
                    )

    df = pd.DataFrame(rows)
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    pairwise_df = pd.DataFrame(pairwise_rows)
    if not pairwise_df.empty:
        pairwise_out = out_path.with_name(f"{out_path.stem}_pairwise{out_path.suffix}")
        pairwise_df.to_csv(pairwise_out, index=False)
    return df


def run_temporal_drift(
    shots: int,
    distances: Iterable[int],
    p_values: Iterable[float],
    seed: int = 12345,
    out_csv: str | Path = "results/temporal_drift_results.csv",
) -> pd.DataFrame:
    rows = []
    pairwise_rows = []
    for d in distances:
        rounds = 10
        for p_mean in p_values:
            constant_schedule = [p_mean for _ in range(rounds)]
            drift_schedule = [0.5 * p_mean for _ in range(rounds // 2)] + [1.5 * p_mean for _ in range(rounds - rounds // 2)]

            scenarios = [
                ("constant_data_schedule", constant_schedule, [0.001 for _ in range(rounds)]),
                ("front_half_low_back_half_high", drift_schedule, [0.001 for _ in range(rounds)]),
                ("measurement_only_worse", constant_schedule, [0.001 for _ in range(rounds // 2)] + [0.003 for _ in range(rounds - rounds // 2)]),
            ]

            nominal_constant_circuit = explicit_repetition_memory_circuit(
                distance=d,
                rounds=rounds,
                data_pauli_by_round=[(float(p_mean), 0.0, 0.0) for _ in range(rounds)],
                measurement_flip_by_round=[0.001 for _ in range(rounds)],
                p_two_qubit=0.001,
                p_reset_flip=0.001,
                final_measure_flip=0.001,
            )

            for scenario_name, data_schedule, measurement_schedule in scenarios:
                true_schedule_circuit = explicit_repetition_memory_circuit(
                    distance=d,
                    rounds=rounds,
                    data_pauli_by_round=[(float(p_data), 0.0, 0.0) for p_data in data_schedule],
                    measurement_flip_by_round=[float(x) for x in measurement_schedule],
                    p_two_qubit=0.001,
                    p_reset_flip=0.001,
                    final_measure_flip=float(measurement_schedule[-1]),
                )

                method_rows, pairwise = evaluate_decoders_on_shared_samples(
                    sampling_circuit=true_schedule_circuit,
                    decoder_circuits={
                        "unweighted_mwpm": true_schedule_circuit,
                        "mwpm_nominal_static_model": nominal_constant_circuit,
                        "mwpm_oracle_true_schedule_model": true_schedule_circuit,
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
                for pw in pairwise:
                    pairwise_rows.append(
                        {
                            "layer": "layer2",
                            "experiment": "temporal_drift_schedule_pairwise",
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
                            **pw,
                        }
                    )

    df = pd.DataFrame(rows)
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    pairwise_df = pd.DataFrame(pairwise_rows)
    if not pairwise_df.empty:
        pairwise_out = out_path.with_name(f"{out_path.stem}_pairwise{out_path.suffix}")
        pairwise_df.to_csv(pairwise_out, index=False)
    return df
