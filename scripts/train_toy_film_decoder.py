from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_stim.decoder_comparison import run_decoder_comparison
from qec_stim.plots import plot_decoder_comparison


def main() -> None:
    run_decoder_comparison(
        shots=8000,
        distances=(3, 5),
        p_values=(0.005, 0.01),
        include_neural=True,
        out_csv=ROOT / "results" / "decoder_comparison_results.csv",
    )
    plot_decoder_comparison(
        csv_path=ROOT / "results" / "decoder_comparison_results.csv",
        fig_path=ROOT / "figures" / "decoder_comparison.png",
    )
    print("Toy FiLM decoder training/evaluation complete.")


if __name__ == "__main__":
    main()
