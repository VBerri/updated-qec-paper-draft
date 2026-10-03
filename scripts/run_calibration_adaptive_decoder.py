from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_stim.calibration_adaptive import (  # noqa: E402
    run_calibration_adaptive_decoder_experiment,
    summarize_calibration_gain,
)
from qec_stim.plots import plot_calibration_adaptive_rounds  # noqa: E402


def mode_params(mode: str):
    if mode == "quick":
        return 5000, [3, 5], [1, 3, 5, 7]
    if mode == "full-local":
        return 25000, [3, 5, 7], [1, 3, 5, 7, 9]
    raise ValueError("mode must be quick or full-local")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run calibration-aware vs static decoder experiment on same syndrome data.")
    parser.add_argument("--mode", choices=["quick", "full-local"], default="quick")
    args = parser.parse_args()

    shots, distances, rounds_list = mode_params(args.mode)
    out_csv = ROOT / "results" / "calibration_adaptive_decoder_results.csv"

    df = run_calibration_adaptive_decoder_experiment(
        shots=shots,
        distances=distances,
        rounds_list=rounds_list,
        static_reference_snapshot="monday",
        out_csv=out_csv,
    )

    plot_calibration_adaptive_rounds(
        csv_path=out_csv,
        fig_path=ROOT / "figures" / "calibration_adaptive_rounds.png",
    )

    summary = summarize_calibration_gain(df)
    summary_path = ROOT / "results" / "calibration_adaptive_gain_summary.csv"
    summary.to_csv(summary_path, index=False)

    wins = int((summary["adaptive_minus_static"] < 0.0).sum())
    total = int(summary.shape[0])
    print(f"Calibration-adaptive experiment complete. Adaptive better in {wins}/{total} settings.")
    print(f"Results: {out_csv}")
    print(f"Gain summary: {summary_path}")


if __name__ == "__main__":
    main()