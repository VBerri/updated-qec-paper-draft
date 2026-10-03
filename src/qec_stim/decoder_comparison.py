from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .mwpm_decode import decode_syndrome_batch, decode_with_weight_mode
from .stim_circuits import generated_repetition_memory_circuit


def _detector_count_heuristic(syndrome: np.ndarray) -> np.ndarray:
    pred = (np.sum(syndrome, axis=1) > (syndrome.shape[1] / 2.0)).astype(np.uint8)
    return pred.reshape(-1, 1)


def run_decoder_comparison(
    shots: int,
    distances: Iterable[int],
    p_values: Iterable[float],
    include_neural: bool = True,
    out_csv: str | Path = "results/decoder_comparison_results.csv",
) -> pd.DataFrame:
    rows = []

    for d in distances:
        rounds = d
        for p in p_values:
            circuit = generated_repetition_memory_circuit(distance=d, rounds=rounds, p=p)

            syndrome, actual, mwpm_pred = decode_with_weight_mode(circuit, shots=shots, weight_mode="detector_model")
            unweighted_pred = decode_syndrome_batch(circuit, syndrome, weight_mode="uniform")
            detector_heuristic_pred = _detector_count_heuristic(syndrome)

            for method, pred in [
                ("detector_count_heuristic", detector_heuristic_pred),
                ("unweighted_mwpm", unweighted_pred),
                ("mwpm", mwpm_pred),
            ]:
                logical_error = float(np.mean(pred != actual))
                rows.append(
                    {
                        "layer": "layer2",
                        "experiment": "decoder_comparison",
                        "distance": d,
                        "rounds": rounds,
                        "p": p,
                        "method": method,
                        "shots": shots,
                        "logical_error_rate": logical_error,
                    }
                )

            if include_neural:
                from .neural_decoder import train_and_predict_toy_film_decoder

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
                        "logical_error_rate": neural_error,
                    }
                )

    df = pd.DataFrame(rows)
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df
