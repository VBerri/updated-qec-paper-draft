from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_stim.plots import plot_bias_results
from qec_stim.stim_experiments import run_bias_sweep


def mode_params(mode: str):
    if mode == "quick":
        return 5000, [0.001, 0.005, 0.01, 0.02], [0.1, 1, 10], [3, 5, 7]
    if mode == "full-local":
        return 100000, [0.001, 0.002, 0.005, 0.01, 0.02, 0.05], [0.1, 1, 3, 10, 30, 100], [3, 5, 7, 9, 11]
    raise ValueError("mode must be quick or full-local")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run biased-noise sweeps in Stim.")
    parser.add_argument("--mode", choices=["quick", "full-local"], default="quick")
    parser.add_argument("--seed", type=int, default=12345)
    args = parser.parse_args()

    shots, p_values, bias_values, distances = mode_params(args.mode)
    run_bias_sweep(
        shots=shots,
        distances=distances,
        p_values=p_values,
        bias_values=bias_values,
        seed=args.seed,
        out_csv=ROOT / "results" / "bias_sweep_results.csv",
    )
    plot_bias_results(
        csv_path=ROOT / "results" / "bias_sweep_results.csv",
        heatmap_path=ROOT / "figures" / "bias_heatmap.png",
        curves_path=ROOT / "figures" / "bias_curves_by_distance.png",
    )
    print("Bias sweep complete.")


if __name__ == "__main__":
    main()
