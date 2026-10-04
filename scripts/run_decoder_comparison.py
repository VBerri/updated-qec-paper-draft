from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_stim.decoder_comparison import run_decoder_comparison
from qec_stim.plots import plot_decoder_comparison


def mode_params(mode: str):
    if mode == "quick":
        return 5000, [0.001, 0.005, 0.01, 0.02], [3, 5, 7]
    if mode == "full-local":
        return 25000, [0.001, 0.002, 0.005, 0.01, 0.02, 0.05], [3, 5, 7, 9, 11]
    raise ValueError("mode must be quick or full-local")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run decoder comparison experiments.")
    parser.add_argument("--mode", choices=["quick", "full-local"], default="quick")
    parser.add_argument("--include-neural", action="store_true")
    parser.add_argument("--seed", type=int, default=12345)
    args = parser.parse_args()

    shots, p_values, distances = mode_params(args.mode)
    run_decoder_comparison(
        shots=shots,
        distances=distances,
        p_values=p_values,
        include_neural=args.include_neural,
        seed=args.seed,
        out_csv=ROOT / "results" / "decoder_comparison_results.csv",
    )
    plot_decoder_comparison(
        csv_path=ROOT / "results" / "decoder_comparison_results.csv",
        fig_path=ROOT / "figures" / "decoder_comparison.png",
    )
    print("Decoder comparison complete.")


if __name__ == "__main__":
    main()
