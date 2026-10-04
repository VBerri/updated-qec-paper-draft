from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_stim.plots import plot_temporal_drift
from qec_stim.stim_experiments import run_temporal_drift


def mode_params(mode: str):
    if mode == "quick":
        return 5000, [0.01, 0.02], [5, 7]
    if mode == "full-local":
        return 100000, [0.01, 0.02], [5, 7]
    raise ValueError("mode must be quick or full-local")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run temporal drift snapshot analysis.")
    parser.add_argument("--mode", choices=["quick", "full-local"], default="quick")
    parser.add_argument("--seed", type=int, default=12345)
    args = parser.parse_args()

    shots, p_values, distances = mode_params(args.mode)
    run_temporal_drift(
        shots=shots,
        distances=distances,
        p_values=p_values,
        seed=args.seed,
        out_csv=ROOT / "results" / "temporal_drift_results.csv",
    )
    plot_temporal_drift(
        csv_path=ROOT / "results" / "temporal_drift_results.csv",
        fig_path=ROOT / "figures" / "temporal_drift_plot.png",
    )
    print("Temporal drift analysis complete.")


if __name__ == "__main__":
    main()
