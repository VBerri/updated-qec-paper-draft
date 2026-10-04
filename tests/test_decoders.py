from pathlib import Path

import numpy as np

from qec_stim.decoder_comparison import _final_data_majority_from_measurements, run_decoder_comparison


def test_decoder_comparison_outputs(tmp_path: Path):
    out_csv = tmp_path / "decoder_comparison.csv"
    df = run_decoder_comparison(
        shots=4000,
        distances=(5,),
        p_values=(0.05,),
        include_neural=False,
        out_csv=out_csv,
    )
    assert out_csv.exists()
    methods = set(df["method"].tolist())
    assert methods == {"final_data_majority", "detector_count_heuristic", "unweighted_mwpm", "mwpm"}

    assert "failures" in df.columns
    assert int(df["failures"].min()) >= 0
    assert int(df["failures"].max()) <= 4000

    pivot = df.pivot_table(index=["distance", "p"], columns="method", values="logical_error_rate")
    row = pivot.loc[(5, 0.05)]
    assert row["mwpm"] <= row["unweighted_mwpm"]


def test_final_data_majority_returns_decoded_bit_not_failure_mask():
    measurements = np.array(
        [[0, 0, 1],
         [1, 1, 1]],
        dtype=np.uint8,
    )
    pred = _final_data_majority_from_measurements(
        measurements,
        final_data_cols=[0, 1, 2],
        prepared_logical_bit=1,
    )
    assert pred.reshape(-1).tolist() == [0, 1]
