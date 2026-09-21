from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_stim.plots import plot_stim_logical_error
from qec_stim.stim_experiments import run_stim_mwpm_experiments


def mode_params(mode: str) -> tuple[int, list[float]]:
    if mode == "quick":
        return 5000, [0.001, 0.005, 0.01, 0.02]
    if mode == "full-local":
        return 100000, [0.001, 0.002, 0.005, 0.01, 0.02, 0.05]
    raise ValueError("mode must be quick or full-local")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stim + PyMatching MWPM sweeps.")
    parser.add_argument("--mode", choices=["quick", "full-local"], default="quick")
    args = parser.parse_args()

    shots, p_values = mode_params(args.mode)
    run_stim_mwpm_experiments(
        shots=shots,
        distances=(3, 5, 7, 9, 11),
        p_values=p_values,
        out_csv=ROOT / "results" / "stim_mwpm_results.csv",
    )
    plot_stim_logical_error(
        csv_path=ROOT / "results" / "stim_mwpm_results.csv",
        fig_path=ROOT / "figures" / "stim_logical_error_vs_p.png",
    )
    print("Layer 2 Stim MWPM sweep complete.")


if __name__ == "__main__":
    main()
