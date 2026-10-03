from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd
import stim

from .mwpm_decode import decode_syndrome_batch
from .stim_circuits import generated_repetition_memory_circuit


def _detector_count_heuristic(syndrome: np.ndarray) -> np.ndarray:
    pred = (np.sum(syndrome, axis=1) > (syndrome.shape[1] / 2.0)).astype(np.uint8)
    return pred.reshape(-1, 1)


def _final_data_measurement_columns(circuit: stim.Circuit) -> list[int]:
    """Return measurement record columns belonging to the final data readout."""
    flat = circuit.flattened()
    measurement_col = 0
    final_cols: list[int] = []

    for name, targets, _ in flat.flattened_operations():
        if name in {"M", "MX", "MY", "MZ", "MR", "MRX", "MRY", "MRZ"}:
            cols = list(range(measurement_col, measurement_col + len(targets)))
            measurement_col += len(targets)
            if name in {"M", "MX", "MY", "MZ"}:
                final_cols = cols

    if not final_cols:
        raise RuntimeError("Unable to identify final data measurement columns from circuit")
    return final_cols


def _sample_consistent_records(circuit: stim.Circuit, shots: int):
    """Sample measurements once and derive detectors/observables from the same records."""
    measurements = circuit.compile_sampler().sample(shots)
    converter = circuit.compile_m2d_converter()
    syndrome, actual_observables = converter.convert(measurements=measurements, separate_observables=True)
    return measurements, syndrome, actual_observables


def _sample_consistent_records_seeded(circuit: stim.Circuit, shots: int, seed: int | None):
    """Seeded variant used for reproducible experimental runs."""
    if seed is None:
        return _sample_consistent_records(circuit=circuit, shots=shots)
    measurements = circuit.compile_sampler(seed=seed).sample(shots)
    converter = circuit.compile_m2d_converter()
    syndrome, actual_observables = converter.convert(measurements=measurements, separate_observables=True)
    return measurements, syndrome, actual_observables


def _final_data_majority_from_measurements(
    measurements: np.ndarray,
    final_data_cols: list[int],
    prepared_logical_bit: int = 0,
) -> np.ndarray:
    final_data = measurements[:, final_data_cols].astype(np.uint8)
    logical_bit = (np.sum(final_data, axis=1) > (final_data.shape[1] / 2.0)).astype(np.uint8)
    predicted_observable_flip = (logical_bit != prepared_logical_bit).astype(np.uint8)
    return predicted_observable_flip.reshape(-1, 1)


def evaluate_decoders_on_shared_samples(
    *,
    sampling_circuit: stim.Circuit,
    decoder_circuits: Mapping[str, stim.Circuit],
    shots: int,
    seed: int | None,
    include_final_data_majority: bool = True,
    include_detector_count_heuristic: bool = True,
    prepared_logical_bit: int = 0,
) -> tuple[list[dict], list[dict]]:
    """Evaluate decoder methods on identical sampled shots and return metric rows plus pairwise rows."""
    final_data_cols = _final_data_measurement_columns(sampling_circuit)
    measurements, syndrome, actual = _sample_consistent_records_seeded(
        sampling_circuit,
        shots=shots,
        seed=seed,
    )

    method_predictions: list[tuple[str, np.ndarray]] = []
    if include_final_data_majority:
        method_predictions.append(
            (
                "final_data_majority",
                _final_data_majority_from_measurements(
                    measurements,
                    final_data_cols=final_data_cols,
                    prepared_logical_bit=prepared_logical_bit,
                ),
            )
        )
    if include_detector_count_heuristic:
        method_predictions.append(("detector_count_heuristic", _detector_count_heuristic(syndrome)))

    for method, circuit in decoder_circuits.items():
        weight_mode = "detector_model" if "unweighted" not in method else "uniform"
        method_predictions.append((method, decode_syndrome_batch(circuit, syndrome, weight_mode=weight_mode)))

    method_rows = []
    pairwise_rows = []
    failure_masks = {}
    for method, pred in method_predictions:
        fail_mask = (pred != actual).reshape(-1)
        failure_masks[method] = fail_mask
        failures = int(np.sum(fail_mask))
        method_rows.append(
            {
                "method": method,
                "shots": shots,
                "seed": seed,
                "failures": failures,
                "logical_error_rate": float(failures / shots),
            }
        )

    for i, (left_name, _) in enumerate(method_predictions):
        left_mask = failure_masks[left_name]
        for j, (right_name, _) in enumerate(method_predictions):
            if i >= j:
                continue
            right_mask = failure_masks[right_name]
            pairwise_rows.append(
                {
                    "left_method": left_name,
                    "right_method": right_name,
                    "left_only_failures": int(np.sum(left_mask & ~right_mask)),
                    "right_only_failures": int(np.sum(right_mask & ~left_mask)),
                    "both_failures": int(np.sum(left_mask & right_mask)),
                    "both_success": int(np.sum(~left_mask & ~right_mask)),
                }
            )

    return method_rows, pairwise_rows


def run_decoder_comparison(
    shots: int,
    distances: Iterable[int],
    p_values: Iterable[float],
    include_neural: bool = True,
    seed: int | None = None,
    out_csv: str | Path = "results/decoder_comparison_results.csv",
) -> pd.DataFrame:
    rows = []
    pairwise_rows = []

    for d in distances:
        rounds = d
        for p in p_values:
            circuit = generated_repetition_memory_circuit(distance=d, rounds=rounds, p=p)

            method_rows, pairwise = evaluate_decoders_on_shared_samples(
                sampling_circuit=circuit,
                decoder_circuits={
                    "unweighted_mwpm": circuit,
                    "mwpm": circuit,
                },
                shots=shots,
                seed=seed,
                include_final_data_majority=True,
                include_detector_count_heuristic=True,
                prepared_logical_bit=0,
            )

            for m in method_rows:
                rows.append(
                    {
                        "layer": "layer2",
                        "experiment": "decoder_comparison",
                        "distance": d,
                        "rounds": rounds,
                        "p": p,
                        **m,
                    }
                )

            for pw in pairwise:
                pairwise_rows.append(
                    {
                        "layer": "layer2",
                        "experiment": "decoder_comparison_pairwise",
                        "distance": d,
                        "rounds": rounds,
                        "p": p,
                        "shots": shots,
                        "seed": seed,
                        **pw,
                    }
                )

            if include_neural:
                from .neural_decoder import train_and_predict_toy_film_decoder

                measurements, syndrome, actual = _sample_consistent_records_seeded(circuit, shots=shots, seed=seed)
                subsample = min(5000, syndrome.shape[0])
                syn_train = syndrome[:subsample]
                y_train = actual[:subsample].reshape(-1)
                calibration = np.linspace(0.9, 1.1, syn_train.shape[1], dtype=np.float32)
                neural_pred = train_and_predict_toy_film_decoder(
                    syndrome=syn_train,
                    labels=y_train,
                    calibration_vector=calibration,
                    epochs=4,
                    batch_size=256,
                    seed=12345,
                )
                neural_error = float(np.mean(neural_pred != actual[:subsample]))
                rows.append(
                    {
                        "layer": "layer2",
                        "experiment": "decoder_comparison",
                        "distance": d,
                        "rounds": rounds,
                        "p": p,
                        "method": "toy_film_neural",
                        "shots": subsample,
                        "failures": int(np.sum(neural_pred != actual[:subsample])),
                        "logical_error_rate": neural_error,
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
