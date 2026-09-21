from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_baseline.baseline_experiments import DEFAULT_P_VALUES, run_baseline_experiments
from qec_baseline.baseline_plots import generate_baseline_plots


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Layer 1 Qiskit Aer baseline experiments.")
    parser.add_argument("--shots", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=12345)
    args = parser.parse_args()

    run_baseline_experiments(
        shots=args.shots,
        idle_steps=4,
        seed=args.seed,
        p_values=DEFAULT_P_VALUES,
        code_sizes=(1, 3, 5),
        out_csv=ROOT / "results" / "baseline_qiskit_results.csv",
    )
    generate_baseline_plots(
        csv_path=ROOT / "results" / "baseline_qiskit_results.csv",
        figure_dir=ROOT / "figures",
    )
    print("Layer 1 baseline complete.")


if __name__ == "__main__":
    main()
