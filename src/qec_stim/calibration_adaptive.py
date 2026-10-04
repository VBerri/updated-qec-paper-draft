from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .mwpm_decode import decode_syndrome_batch
from .noise_models import biased_pauli_rates
from .stim_circuits import biased_noise_repetition_approximation


def _majority_from_syndrome(syndrome: np.ndarray) -> np.ndarray:
    pred = (np.sum(syndrome, axis=1) > (syndrome.shape[1] / 2.0)).astype(np.uint8)
    return pred.reshape(-1, 1)


def _wilson_interval(num_errors: int, shots: int, z: float = 1.96) -> tuple[float, float]:
    if shots <= 0:
        raise ValueError("shots must be positive")
    p_hat = num_errors / shots
    denom = 1.0 + (z**2 / shots)
    center = (p_hat + (z**2 / (2.0 * shots))) / denom
    radius = z * np.sqrt((p_hat * (1.0 - p_hat) / shots) + (z**2 / (4.0 * shots**2))) / denom
    lo = max(0.0, center - radius)
    hi = min(1.0, center + radius)
    return float(lo), float(hi)


def _default_snapshots() -> list[dict[str, float | str]]:
    return [
        {"snapshot": "monday", "p_total": 0.012, "bias_z": 8.0, "meas_factor": 1.0},
        {"snapshot": "wednesday", "p_total": 0.016, "bias_z": 5.0, "meas_factor": 1.15},
        {"snapshot": "friday", "p_total": 0.020, "bias_z": 2.5, "meas_factor": 1.25},
    ]


def _build_snapshot_circuit(distance: int, rounds: int, p_total: float, bias_z: float, meas_factor: float):
    px, py, pz = biased_pauli_rates(p_total=p_total, bias_z=bias_z)
    return biased_noise_repetition_approximation(
        distance=distance,
        rounds=rounds,
        px=px,
        py=py,
        pz=pz,
        measurement_flip_probability=min(max(p_total * meas_factor, 0.0), 0.49),
    )


def run_calibration_adaptive_decoder_experiment(
    shots: int,
    distances: Iterable[int] = (3, 5),
    rounds_list: Iterable[int] = (1, 3, 5, 7),
    snapshots: Iterable[dict[str, float | str]] | None = None,
    static_reference_snapshot: str = "monday",
    seed: int | None = None,
    out_csv: str | Path = "results/calibration_adaptive_decoder_results.csv",
) -> pd.DataFrame:
    if shots <= 0:
        raise ValueError("shots must be positive")

    snapshot_cfg = list(snapshots) if snapshots is not None else _default_snapshots()
    snapshot_map = {str(s["snapshot"]): s for s in snapshot_cfg}
    if static_reference_snapshot not in snapshot_map:
        raise ValueError("static_reference_snapshot must match one of the snapshot labels")

    rows: list[dict[str, float | int | str]] = []

    for d in distances:
        for rounds in rounds_list:
            static_cfg = snapshot_map[static_reference_snapshot]
            static_circuit = _build_snapshot_circuit(
                distance=d,
                rounds=rounds,
                p_total=float(static_cfg["p_total"]),
                bias_z=float(static_cfg["bias_z"]),
                meas_factor=float(static_cfg["meas_factor"]),
            )

            for snapshot in snapshot_cfg:
                snapshot_name = str(snapshot["snapshot"])
                sample_circuit = _build_snapshot_circuit(
                    distance=d,
                    rounds=rounds,
                    p_total=float(snapshot["p_total"]),
                    bias_z=float(snapshot["bias_z"]),
                    meas_factor=float(snapshot["meas_factor"]),
                )

                sampler = sample_circuit.compile_detector_sampler(seed=seed) if seed is not None else sample_circuit.compile_detector_sampler()
                syndrome, actual = sampler.sample(shots, separate_observables=True)

                predictions = {
                    "detector_event_majority": _majority_from_syndrome(syndrome),
                    "uniform_mwpm": decode_syndrome_batch(sample_circuit, syndrome, weight_mode="uniform"),
                    "static_weighted_mwpm": decode_syndrome_batch(static_circuit, syndrome, weight_mode="detector_model"),
                    "oracle_informed_mwpm": decode_syndrome_batch(sample_circuit, syndrome, weight_mode="detector_model"),
                }

                shared_group = f"{snapshot_name}_d{d}_r{rounds}"

                for method, pred in predictions.items():
                    num_errors = int(np.sum(pred != actual))
                    logical_error = float(num_errors / shots)
                    ci_low, ci_high = _wilson_interval(num_errors=num_errors, shots=shots)
                    rows.append(
                        {
                            "layer": "layer2",
                            "experiment": "calibration_adaptive_decoder",
                            "snapshot": snapshot_name,
                            "distance": d,
                            "rounds": rounds,
                            "shots": shots,
                            "method": method,
                            "seed": seed,
                            "failures": num_errors,
                            "logical_error_rate": logical_error,
                            "ci95_low": ci_low,
                            "ci95_high": ci_high,
                            "snapshot_p_total": float(snapshot["p_total"]),
                            "snapshot_bias_z": float(snapshot["bias_z"]),
                            "snapshot_meas_factor": float(snapshot["meas_factor"]),
                            "static_reference_snapshot": static_reference_snapshot,
                            "same_syndrome_group": shared_group,
                        }
                    )

    df = pd.DataFrame(rows)
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df


def summarize_calibration_gain(df: pd.DataFrame) -> pd.DataFrame:
    pivot = df.pivot_table(
        index=["snapshot", "distance", "rounds"],
        columns="method",
        values="logical_error_rate",
        aggfunc="mean",
    ).reset_index()

    if "static_weighted_mwpm" not in pivot or "oracle_informed_mwpm" not in pivot:
        raise ValueError("Data frame must include both static_weighted_mwpm and oracle_informed_mwpm")

    pivot["adaptive_minus_static"] = pivot["oracle_informed_mwpm"] - pivot["static_weighted_mwpm"]
    pivot["relative_improvement_vs_static"] = (
        (pivot["static_weighted_mwpm"] - pivot["oracle_informed_mwpm"])
        / np.clip(pivot["static_weighted_mwpm"], 1e-12, None)
    )
    return pivot