from pathlib import Path

import pandas as pd

from qec_stim.stim_experiments import run_bias_sweep, run_heterogeneous_noise, run_temporal_drift


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
    assert set(df["scenario"]) == {"uniform_control", "local_defect_edge", "local_defect_center"}
    assert {"final_data_majority", "unweighted_mwpm", "mwpm_nominal_uniform_model", "mwpm_oracle_heterogeneous_model"}.issubset(set(df["method"]))

    # Same-mean design should preserve mean data rate for each scenario.
    means = df.groupby("scenario")["effective_p_mean"].mean().to_dict()
    assert abs(means["uniform_control"] - means["local_defect_edge"]) < 1e-12
    assert abs(means["uniform_control"] - means["local_defect_center"]) < 1e-12


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
        "constant_data_schedule",
        "front_half_low_back_half_high",
        "measurement_only_worse",
    }
    assert {"final_data_majority", "unweighted_mwpm", "mwpm_nominal_static_model", "mwpm_oracle_true_schedule_model"}.issubset(set(df["method"]))

    # Constant and drift schedule share the same mean data rate.
    pivot = (
        df.groupby("snapshot", as_index=False)["schedule_data_mean"]
        .mean()
        .set_index("snapshot")["schedule_data_mean"]
    )
    assert abs(float(pivot["constant_data_schedule"]) - float(pivot["front_half_low_back_half_high"])) < 1e-12
