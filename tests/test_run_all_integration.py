from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

import scripts.run_all as run_all


def _touch_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"PNG")


def _touch_csv(path: Path, data: dict[str, list[object]] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = data if data is not None else {"ok": [1]}
    pd.DataFrame(payload).to_csv(path, index=False)


def test_run_all_quick_is_compatible_and_does_not_overwrite_authored_docs(tmp_path: Path, monkeypatch):
    authored_paper = "AUTHORED_PAPER_SENTINEL\n"
    authored_summary = "AUTHORED_SUMMARY_SENTINEL\n"

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    paper_path = docs_dir / "paper_draft.md"
    summary_path = docs_dir / "professor_response_summary.md"
    paper_path.write_text(authored_paper, encoding="utf-8")
    summary_path.write_text(authored_summary, encoding="utf-8")

    monkeypatch.setattr(run_all, "ROOT", tmp_path)

    logger = logging.getLogger("run_all_test")
    logger.handlers = []
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.NullHandler())
    monkeypatch.setattr(run_all, "_setup_logger", lambda: logger)

    monkeypatch.setattr(run_all, "ensure_project_dirs", lambda root: [
        (Path(root) / "results").mkdir(parents=True, exist_ok=True),
        (Path(root) / "figures").mkdir(parents=True, exist_ok=True),
        (Path(root) / "logs").mkdir(parents=True, exist_ok=True),
        (Path(root) / "docs").mkdir(parents=True, exist_ok=True),
    ])

    def fake_run_baseline_experiments(**kwargs):
        _touch_csv(Path(kwargs["out_csv"]), {"experiment": ["bit_flip"], "p": [0.1], "logical_success_probability": [0.9]})

    def fake_generate_baseline_plots(_csv_path, figure_dir):
        base = Path(figure_dir)
        for name in [
            "baseline_bitflip.png",
            "baseline_phaseflip.png",
            "baseline_depolarizing.png",
            "baseline_summary_p010.png",
            "baseline_theory_vs_sim.png",
        ]:
            _touch_png(base / name)

    def fake_run_stim_mwpm_experiments(**kwargs):
        _touch_csv(Path(kwargs["out_csv"]), {"distance": [3], "p": [0.01], "logical_error_rate": [0.01]})

    def fake_plot_stim_logical_error(_csv, fig):
        _touch_png(Path(fig))

    def fake_run_bias_sweep(**kwargs):
        _touch_csv(Path(kwargs["out_csv"]), {"distance": [3], "bias_z": [1.0], "logical_error_rate": [0.02]})

    def fake_plot_bias_results(_csv, heatmap, curves):
        _touch_png(Path(heatmap))
        _touch_png(Path(curves))

    heterogeneous_call = {"called": False}

    def fake_run_heterogeneous_noise(**kwargs):
        heterogeneous_call["called"] = True
        assert "spreads" not in kwargs
        _touch_csv(Path(kwargs["out_csv"]), {"scenario": ["uniform_control"], "logical_error_rate": [0.03]})

    def fake_plot_heterogeneous_noise(_csv, fig):
        _touch_png(Path(fig))

    def fake_run_temporal_drift(**kwargs):
        _touch_csv(Path(kwargs["out_csv"]), {"snapshot": ["constant_data_schedule"], "logical_error_rate": [0.04]})

    def fake_plot_temporal_drift(_csv, fig):
        _touch_png(Path(fig))

    def fake_run_decoder_comparison(**kwargs):
        _touch_csv(Path(kwargs["out_csv"]), {"method": ["mwpm"], "logical_error_rate": [0.01]})

    def fake_plot_decoder_comparison(_csv, fig):
        _touch_png(Path(fig))

    def fake_run_calibration_adaptive_decoder_experiment(**kwargs):
        out_csv = Path(kwargs["out_csv"])
        df = pd.DataFrame(
            {
                "snapshot": ["monday"],
                "distance": [3],
                "rounds": [1],
                "method": ["static_weighted_mwpm"],
                "logical_error_rate": [0.02],
            }
        )
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_csv, index=False)
        return df

    def fake_plot_calibration_adaptive_rounds(_csv, fig):
        _touch_png(Path(fig))

    def fake_summarize_calibration_gain(_df):
        return pd.DataFrame(
            {
                "snapshot": ["monday"],
                "distance": [3],
                "rounds": [1],
                "adaptive_minus_static": [0.0],
                "relative_improvement_vs_static": [0.0],
            }
        )

    def fake_plot_pipeline_diagram(fig):
        _touch_png(Path(fig))

    monkeypatch.setattr(run_all, "run_baseline_experiments", fake_run_baseline_experiments)
    monkeypatch.setattr(run_all, "generate_baseline_plots", fake_generate_baseline_plots)
    monkeypatch.setattr(run_all, "run_stim_mwpm_experiments", fake_run_stim_mwpm_experiments)
    monkeypatch.setattr(run_all, "plot_stim_logical_error", fake_plot_stim_logical_error)
    monkeypatch.setattr(run_all, "run_bias_sweep", fake_run_bias_sweep)
    monkeypatch.setattr(run_all, "plot_bias_results", fake_plot_bias_results)
    monkeypatch.setattr(run_all, "run_heterogeneous_noise", fake_run_heterogeneous_noise)
    monkeypatch.setattr(run_all, "plot_heterogeneous_noise", fake_plot_heterogeneous_noise)
    monkeypatch.setattr(run_all, "run_temporal_drift", fake_run_temporal_drift)
    monkeypatch.setattr(run_all, "plot_temporal_drift", fake_plot_temporal_drift)
    monkeypatch.setattr(run_all, "run_decoder_comparison", fake_run_decoder_comparison)
    monkeypatch.setattr(run_all, "plot_decoder_comparison", fake_plot_decoder_comparison)
    monkeypatch.setattr(run_all, "run_calibration_adaptive_decoder_experiment", fake_run_calibration_adaptive_decoder_experiment)
    monkeypatch.setattr(run_all, "plot_calibration_adaptive_rounds", fake_plot_calibration_adaptive_rounds)
    monkeypatch.setattr(run_all, "summarize_calibration_gain", fake_summarize_calibration_gain)
    monkeypatch.setattr(run_all, "plot_pipeline_diagram", fake_plot_pipeline_diagram)

    old_argv = sys.argv[:]
    sys.argv = ["run_all.py", "--mode", "quick"]
    try:
        run_all.main()
    finally:
        sys.argv = old_argv

    assert heterogeneous_call["called"]
    assert paper_path.read_text(encoding="utf-8") == authored_paper
    assert summary_path.read_text(encoding="utf-8") == authored_summary
