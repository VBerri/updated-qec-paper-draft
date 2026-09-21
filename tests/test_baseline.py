from pathlib import Path

from qec_baseline.baseline_experiments import run_baseline_experiments
from qec_baseline.theory import effective_error_over_idle_steps, repetition_success_probability


def test_baseline_theory_basic():
    assert repetition_success_probability(3, 0.0, idle_steps=4) == 1.0
    p_eff = effective_error_over_idle_steps(0.01, idle_steps=4)
    assert 0.0 < p_eff < 0.5


def test_qiskit_baseline_small_run(tmp_path: Path):
    out_csv = tmp_path / "baseline.csv"
    df = run_baseline_experiments(
        shots=1500,
        idle_steps=4,
        seed=12345,
        p_values=[0.10],
        code_sizes=(1, 3, 5),
        out_csv=out_csv,
    )
    assert out_csv.exists()

    sub = df[(df["experiment"] == "bit_flip") & (df["p"] == 0.10)].sort_values("code_size")
    vals = sub["logical_success_probability"].tolist()
    assert len(vals) == 3
    assert vals[2] > vals[1] > vals[0]
