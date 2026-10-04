# Run Manifest: Non-Hardware Evidence Refresh

Date: 2026-10-04

## Purpose

Refresh all non-hardware artifacts affected by corrected reset/gate handling and decoder-label corrections, and align manuscript numeric claims with corrected evidence files.

## Code Provenance

- Repository: VBerri/updated-qec-paper-draft
- Base revision used for this regeneration: 2c3cc67
- Key updated modules:
  - src/qec_stim/stim_experiments.py
  - src/qec_stim/calibration_adaptive.py
  - src/qec_stim/mwpm_decode.py

## Environment

- Python: 3.13.5
- stim: 1.16.0
- pymatching: 2.4.0
- numpy: 2.1.3
- pandas: 2.2.3

## Commands

Executed from project root with PYTHONPATH=src:

1. C:/Users/sansu/anaconda3/python.exe scripts/run_bias_sweep.py --mode full-local --seed 12345
2. C:/Users/sansu/anaconda3/python.exe scripts/run_heterogeneous_noise.py --mode full-local --seed 12345
3. C:/Users/sansu/anaconda3/python.exe scripts/run_temporal_drift.py --mode full-local --seed 12345
4. C:/Users/sansu/anaconda3/python.exe scripts/run_calibration_adaptive_decoder.py --mode full-local --seed 12345

## Regenerated Result Artifacts

- results/bias_sweep_results.csv
- results/heterogeneous_noise_results.csv
- results/heterogeneous_noise_results_pairwise.csv
- results/temporal_drift_results.csv
- results/temporal_drift_results_pairwise.csv
- results/calibration_adaptive_decoder_results.csv
- results/calibration_adaptive_gain_summary.csv

## Regenerated Figures

- figures/bias_heatmap.png
- figures/bias_curves_by_distance.png
- figures/heterogeneous_noise_plot.png
- figures/temporal_drift_plot.png
- figures/calibration_adaptive_rounds.png

## Reproducibility Metadata

- Bias and calibration outputs now include seed and integer failure counts.
- Heterogeneity and temporal outputs include seed, integer failures, and pairwise comparison CSVs.
- Corrected three-seed decoder comparison evidence remains at:
  - results/corrected_runs/decoder_comparison_d11_p002_summary.csv
  - results/corrected_runs/decoder_comparison_d11_p002_seed101.csv
  - results/corrected_runs/decoder_comparison_d11_p002_seed202.csv
  - results/corrected_runs/decoder_comparison_d11_p002_seed303.csv

## Manuscript Alignment Note

- docs/paper_draft.md Stage 2 slice now cites corrected pooled rates from the designated three-seed summary:
  - final_data_majority: 0.054423
  - mwpm: 0.000853
- The broad distance/noise superiority claim is explicitly deferred pending expanded multi-seed uncertainty reporting.
