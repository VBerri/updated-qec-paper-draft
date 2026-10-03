from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_stim.plots import plot_heterogeneous_noise
from qec_stim.stim_experiments import run_heterogeneous_noise


def mode_params(mode: str):
    if mode == "quick":
        return 5000, [0.001, 0.005, 0.01, 0.02], [3, 5, 7]
    if mode == "full-local":
        return 100000, [0.001, 0.002, 0.005, 0.01, 0.02, 0.05], [3, 5, 7, 9, 11]
    raise ValueError("mode must be quick or full-local")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run heterogeneous per-qubit noise sweeps.")
    parser.add_argument("--mode", choices=["quick", "full-local"], default="quick")
    args = parser.parse_args()

    shots, p_values, distances = mode_params(args.mode)
    run_heterogeneous_noise(
        shots=shots,
        distances=distances,
        p_values=p_values,
        spreads=(0.0, 0.25, 0.5, 1.0),
        out_csv=ROOT / "results" / "heterogeneous_noise_results.csv",
    )
    plot_heterogeneous_noise(
        csv_path=ROOT / "results" / "heterogeneous_noise_results.csv",
        fig_path=ROOT / "figures" / "heterogeneous_noise_plot.png",
    )
    print("Heterogeneous noise sweep complete.")


if __name__ == "__main__":
    main()
