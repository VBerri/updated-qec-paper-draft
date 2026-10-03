from pathlib import Path

from qec_stim.decoder_comparison import run_decoder_comparison


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
    assert methods == {"detector_count_heuristic", "unweighted_mwpm", "mwpm"}

    pivot = df.pivot_table(index=["distance", "p"], columns="method", values="logical_error_rate")
    row = pivot.loc[(5, 0.05)]
    assert row["mwpm"] <= row["unweighted_mwpm"] <= row["detector_count_heuristic"]
