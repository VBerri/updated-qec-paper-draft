from pathlib import Path

import pandas as pd

from qec_stim.stim_experiments import (
    run_bias_sweep,
    run_heterogeneous_noise,
    run_stim_mwpm_experiments,
    run_temporal_drift,
)


def test_bias_sweep_outputs_seed_and_failures(tmp_path: Path):
    out_csv = tmp_path / "bias_corrected.csv"
    df = run_bias_sweep(
        shots=2000,
        distances=(3,),
        p_values=(0.01,),
        bias_values=(0.1, 1.0),
        seed=123,
        out_csv=out_csv,
    )

    assert out_csv.exists()
    assert "seed" in df.columns
    assert "failures" in df.columns
    assert int(df["failures"].min()) >= 0
    assert int(df["failures"].max()) <= 2000
    assert set(df["seed"].unique()) == {123}


def test_run_stim_mwpm_experiments_executes_and_writes_csv(tmp_path: Path):
    out_csv = tmp_path / "stim_mwpm.csv"
    df = run_stim_mwpm_experiments(
        shots=2000,
        distances=(3,),
        p_values=(0.01,),
        out_csv=out_csv,
    )

    assert out_csv.exists()
    assert df.shape[0] == 1
    row = df.iloc[0]
    assert int(row["distance"]) == 3
    assert float(row["p"]) == 0.01
    assert 0.0 <= float(row["logical_error_rate"]) <= 1.0


def test_heterogeneous_noise_same_mean_outputs(tmp_path: Path):
    out_csv = tmp_path / "heterogeneous_corrected.csv"
    df = run_heterogeneous_noise(
        shots=2000,
        distances=(5,),
        p_values=(0.01,),
        seed=123,
        out_csv=out_csv,
    )

    assert out_csv.exists()
    assert set(df["spread"]) == {0.0, 0.25, 0.5, 1.0}
    assert {"final_data_majority", "mwpm"}.issubset(set(df["method"]))

    # With spread=0, rates remain exactly homogeneous.
    spread0 = df[df["spread"] == 0.0]
    assert float(spread0["effective_p_std"].max()) == 0.0


def test_temporal_drift_schedule_outputs(tmp_path: Path):
    out_csv = tmp_path / "temporal_corrected.csv"
    df = run_temporal_drift(
        shots=2000,
        distances=(5,),
        p_values=(0.01,),
        seed=123,
        out_csv=out_csv,
    )

    assert out_csv.exists()
    assert set(df["snapshot"]) == {
        "snapshot_0",
        "snapshot_1",
        "snapshot_2",
        "snapshot_3",
        "snapshot_4",
    }
    assert {"final_data_majority", "mwpm", "weighted_calibration_informed_mwpm"}.issubset(set(df["method"]))
    assert (df["schedule_data_std"] >= 0).all()
