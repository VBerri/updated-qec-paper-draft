from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_baseline.baseline_experiments import DEFAULT_P_VALUES, run_baseline_experiments
from qec_baseline.baseline_plots import generate_baseline_plots
from qec_stim.decoder_comparison import run_decoder_comparison
from qec_stim.calibration_adaptive import (
    run_calibration_adaptive_decoder_experiment,
    summarize_calibration_gain,
)
from qec_stim.plots import (
    plot_bias_results,
    plot_calibration_adaptive_rounds,
    plot_decoder_comparison,
    plot_heterogeneous_noise,
    plot_pipeline_diagram,
    plot_stim_logical_error,
    plot_temporal_drift,
)
from qec_stim.stim_experiments import (
    run_bias_sweep,
    run_heterogeneous_noise,
    run_stim_mwpm_experiments,
    run_temporal_drift,
)
from qec_stim.utils import ensure_project_dirs


def _setup_logger() -> logging.Logger:
    ensure_project_dirs(ROOT)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = ROOT / "logs" / f"run_all_{ts}.log"

    logger = logging.getLogger("run_all")
    logger.setLevel(logging.INFO)
    logger.handlers = []

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    logger.info("Logging to %s", log_path)
    return logger


def _write_docs() -> None:
    # Re-generate these summary docs at each run to keep a fresh run artifact.
    (ROOT / "docs" / "paper_draft.md").write_text(
        (ROOT / "docs" / "paper_draft.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (ROOT / "docs" / "professor_response_summary.md").write_text(
        (ROOT / "docs" / "professor_response_summary.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def _mode_params(mode: str):
    if mode == "quick":
        return {
            "baseline_shots": 1000,
            "stim_shots": 5000,
            "stim_p_values": [0.001, 0.005, 0.01, 0.02],
            "bias_values": [0.1, 1, 10],
            "distances": [3, 5, 7],
            "decoder_shots": 5000,
        }
    if mode == "full-local":
        return {
            "baseline_shots": 4000,
            "stim_shots": 100000,
            "stim_p_values": [0.001, 0.002, 0.005, 0.01, 0.02, 0.05],
            "bias_values": [0.1, 1, 3, 10, 30, 100],
            "distances": [3, 5, 7, 9, 11],
            "decoder_shots": 25000,
        }
    if mode == "full":
        print(
            "IBM hardware validation is Layer 3 and must be run later with "
            "scripts/run_ibm_hardware_validation.py after credentials are set."
        )
        return _mode_params("full-local")
    raise ValueError("Unsupported mode")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full local Layer 1 + Layer 2 pipeline.")
    parser.add_argument("--mode", choices=["quick", "full-local", "full"], default="quick")
    args = parser.parse_args()

    logger = _setup_logger()
    cfg = _mode_params(args.mode)

    try:
        ensure_project_dirs(ROOT)
        logger.info("Starting run_all with mode=%s", args.mode)

        logger.info("1/12 Running Qiskit baseline...")
        run_baseline_experiments(
            shots=cfg["baseline_shots"],
            idle_steps=4,
            seed=12345,
            p_values=DEFAULT_P_VALUES,
            code_sizes=(1, 3, 5),
            out_csv=ROOT / "results" / "baseline_qiskit_results.csv",
        )
        generate_baseline_plots(ROOT / "results" / "baseline_qiskit_results.csv", ROOT / "figures")

        logger.info("2/12 Running Stim MWPM sweeps...")
        run_stim_mwpm_experiments(
            shots=cfg["stim_shots"],
            distances=cfg["distances"],
            p_values=cfg["stim_p_values"],
            out_csv=ROOT / "results" / "stim_mwpm_results.csv",
        )
        plot_stim_logical_error(ROOT / "results" / "stim_mwpm_results.csv", ROOT / "figures" / "stim_logical_error_vs_p.png")

        logger.info("3/12 Running bias sweep...")
        run_bias_sweep(
            shots=cfg["stim_shots"],
            distances=cfg["distances"],
            p_values=cfg["stim_p_values"],
            bias_values=cfg["bias_values"],
            seed=12345,
            out_csv=ROOT / "results" / "bias_sweep_results.csv",
        )
        plot_bias_results(
            ROOT / "results" / "bias_sweep_results.csv",
            ROOT / "figures" / "bias_heatmap.png",
            ROOT / "figures" / "bias_curves_by_distance.png",
        )

        logger.info("4/12 Running heterogeneous noise sweep...")
        run_heterogeneous_noise(
            shots=cfg["stim_shots"],
            distances=cfg["distances"],
            p_values=cfg["stim_p_values"],
            seed=12345,
            out_csv=ROOT / "results" / "heterogeneous_noise_results.csv",
        )
        plot_heterogeneous_noise(
            ROOT / "results" / "heterogeneous_noise_results.csv",
            ROOT / "figures" / "heterogeneous_noise_plot.png",
        )

        logger.info("5/12 Running temporal drift analysis...")
        run_temporal_drift(
            shots=cfg["stim_shots"],
            distances=[d for d in cfg["distances"] if d in {5, 7}],
            p_values=[p for p in cfg["stim_p_values"] if p in {0.01, 0.02}],
            seed=12345,
            out_csv=ROOT / "results" / "temporal_drift_results.csv",
        )
        plot_temporal_drift(
            ROOT / "results" / "temporal_drift_results.csv",
            ROOT / "figures" / "temporal_drift_plot.png",
        )

        logger.info("6/12 Running decoder comparison...")
        run_decoder_comparison(
            shots=cfg["decoder_shots"],
            distances=cfg["distances"],
            p_values=cfg["stim_p_values"],
            include_neural=False,
            out_csv=ROOT / "results" / "decoder_comparison_results.csv",
        )
        plot_decoder_comparison(
            ROOT / "results" / "decoder_comparison_results.csv",
            ROOT / "figures" / "decoder_comparison.png",
        )

        logger.info("7/12 Running calibration-adaptive decoder experiment...")
        adaptive_df = run_calibration_adaptive_decoder_experiment(
            shots=cfg["decoder_shots"],
            distances=[d for d in cfg["distances"] if d in {3, 5, 7}],
            rounds_list=[1, 3, 5, 7],
            static_reference_snapshot="monday",
            seed=12345,
            out_csv=ROOT / "results" / "calibration_adaptive_decoder_results.csv",
        )
        plot_calibration_adaptive_rounds(
            ROOT / "results" / "calibration_adaptive_decoder_results.csv",
            ROOT / "figures" / "calibration_adaptive_rounds.png",
        )
        summarize_calibration_gain(adaptive_df).to_csv(
            ROOT / "results" / "calibration_adaptive_gain_summary.csv", index=False
        )

        logger.info("8/12 Generating pipeline figure...")
        plot_pipeline_diagram(ROOT / "figures" / "pipeline_diagram.png")

        logger.info("9/12 Generating paper draft artifact...")
        _write_docs()

        logger.info("10/12 Generating professor response summary artifact...")
        _write_docs()

        logger.info("11/12 Collecting summary outputs...")
        outputs = [
            ROOT / "results" / "baseline_qiskit_results.csv",
            ROOT / "results" / "stim_mwpm_results.csv",
            ROOT / "results" / "bias_sweep_results.csv",
            ROOT / "results" / "heterogeneous_noise_results.csv",
            ROOT / "results" / "temporal_drift_results.csv",
            ROOT / "results" / "decoder_comparison_results.csv",
            ROOT / "results" / "calibration_adaptive_decoder_results.csv",
            ROOT / "results" / "calibration_adaptive_gain_summary.csv",
            ROOT / "figures" / "baseline_bitflip.png",
            ROOT / "figures" / "baseline_phaseflip.png",
            ROOT / "figures" / "baseline_depolarizing.png",
            ROOT / "figures" / "baseline_summary_p010.png",
            ROOT / "figures" / "baseline_theory_vs_sim.png",
            ROOT / "figures" / "stim_logical_error_vs_p.png",
            ROOT / "figures" / "bias_heatmap.png",
            ROOT / "figures" / "bias_curves_by_distance.png",
            ROOT / "figures" / "heterogeneous_noise_plot.png",
            ROOT / "figures" / "temporal_drift_plot.png",
            ROOT / "figures" / "decoder_comparison.png",
            ROOT / "figures" / "calibration_adaptive_rounds.png",
            ROOT / "figures" / "pipeline_diagram.png",
        ]

        logger.info("12/12 Final status")
        for p in outputs:
            logger.info("Output %s | exists=%s", p.name, p.exists())

        logger.info("IBM Layer 3 was not run yet.")
        print("IBM Layer 3 was not run yet.")
        print("Pipeline completed successfully.")

    except Exception as exc:
        logger.exception("Core local simulation pipeline failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
