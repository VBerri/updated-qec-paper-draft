from pathlib import Path

from qec_stim.calibration_adaptive import (
    run_calibration_adaptive_decoder_experiment,
    summarize_calibration_gain,
)


def test_calibration_adaptive_outputs_same_syndrome_metadata(tmp_path: Path):
    out_csv = tmp_path / "calibration_adaptive_decoder_results.csv"
    df = run_calibration_adaptive_decoder_experiment(
        shots=2000,
        distances=(3,),
        rounds_list=(1, 3),
        out_csv=out_csv,
    )

    assert out_csv.exists()
    assert set(df["method"]) == {
        "majority_vote",
        "uniform_mwpm",
        "static_weighted_mwpm",
        "calibration_aware_mwpm",
    }

    counts = df.groupby(["snapshot", "distance", "rounds"])["same_syndrome_group"].nunique()
    assert (counts == 1).all()


def test_calibration_summary_has_gain_columns(tmp_path: Path):
    out_csv = tmp_path / "calibration_adaptive_decoder_results.csv"
    df = run_calibration_adaptive_decoder_experiment(
        shots=2000,
        distances=(3, 5),
        rounds_list=(1, 3),
        out_csv=out_csv,
    )

    summary = summarize_calibration_gain(df)
    assert "adaptive_minus_static" in summary.columns
    assert "relative_improvement_vs_static" in summary.columns
    assert summary.shape[0] > 0