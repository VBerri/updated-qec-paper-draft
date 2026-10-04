# Run Manifest: Non-Hardware Evidence Refresh

Date: 2026-10-04

## Purpose

Refresh all non-hardware artifacts affected by corrected reset/gate handling and decoder-label corrections, and align manuscript numeric claims with corrected evidence files.

## Code Provenance

- Repository: VBerri/updated-qec-paper-draft
- Base revision before refresh work: 2c3cc67
- Refresh implementation and regenerated outputs were produced from the modified working tree and committed as d183967.
- Reproducing this exact refresh requires commit d183967 (or later), because seed-enabled command paths were introduced in that revision.
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

Tracked submission copies (for publication materials):

- docs/submission_materials/figures/bias_heatmap.png
- docs/submission_materials/figures/bias_curves_by_distance.png
- docs/submission_materials/figures/heterogeneous_noise_plot.png
- docs/submission_materials/figures/temporal_drift_plot.png
- docs/submission_materials/figures/calibration_adaptive_rounds.png
- docs/submission_materials/figures/decoder_comparison.png
- docs/submission_materials/figures/stim_logical_error_vs_p.png

## Reproducibility Metadata

- Bias and calibration outputs now include seed and integer failure counts.
- Heterogeneity and temporal outputs include seed, integer failures, and pairwise comparison CSVs.
- Corrected three-seed decoder comparison evidence remains at:
  - results/corrected_runs/decoder_comparison_d11_p002_summary.csv
  - results/corrected_runs/decoder_comparison_d11_p002_seed101.csv
  - results/corrected_runs/decoder_comparison_d11_p002_seed202.csv
  - results/corrected_runs/decoder_comparison_d11_p002_seed303.csv

Stim and detector-error-model exports included in tracked submission materials:

- docs/submission_materials/reproducibility/stim_dem/decoder_comparison_d11_r11_p0p02.stim
- docs/submission_materials/reproducibility/stim_dem/decoder_comparison_d11_r11_p0p02.dem
- docs/submission_materials/reproducibility/stim_dem/bias_sweep_d7_r7_ptotal0p02_bias10.stim
- docs/submission_materials/reproducibility/stim_dem/bias_sweep_d7_r7_ptotal0p02_bias10.dem
- docs/submission_materials/reproducibility/stim_dem/heterogeneous_center_defect_d7_r7_pmean0p02.stim
- docs/submission_materials/reproducibility/stim_dem/heterogeneous_center_defect_d7_r7_pmean0p02.dem
- docs/submission_materials/reproducibility/stim_dem/temporal_fronthalf_low_backhalf_high_d7_r10_pmean0p02.stim
- docs/submission_materials/reproducibility/stim_dem/temporal_fronthalf_low_backhalf_high_d7_r10_pmean0p02.dem
- docs/submission_materials/reproducibility/stim_dem/calibration_friday_d5_r7_ptotal0p02_bias2p5.stim
- docs/submission_materials/reproducibility/stim_dem/calibration_friday_d5_r7_ptotal0p02_bias2p5.dem

## Manuscript Alignment Note

- docs/paper_draft.md Stage 2 slice now cites corrected pooled rates from the designated three-seed summary:
  - final_data_majority: 0.054423
  - mwpm: 0.000853
- The broad distance/noise superiority claim is explicitly deferred pending expanded multi-seed uncertainty reporting.
- The refreshed bias, heterogeneity, temporal-drift, and calibration sweeps are currently single-seed (12345) evidence for the reported simulated conditions, not multi-seed superiority proof.
