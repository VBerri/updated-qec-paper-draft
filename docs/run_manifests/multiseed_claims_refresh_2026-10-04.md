# Run Manifest: Multi-Seed Broad-Claim Refresh

Date: 2026-10-04

## Purpose

Provide broader-claim simulation evidence beyond the previous single-seed non-hardware refresh by running three seeded trials and pooled summaries across decoder, bias, heterogeneous, temporal-drift, and calibration families.

## Seeds

- 101
- 202
- 303

## Grids and Shot Budgets

- Decoder comparison:
  - distances: (3, 5, 7, 9, 11)
  - rounds: r = d
  - p: (0.001, 0.002, 0.005, 0.01, 0.02, 0.05)
  - shots per seed per point: 25,000
- Bias sweep:
  - distances: (3, 5, 7)
  - rounds: r = d
  - p_total: (0.01, 0.02)
  - bias_z: (0.1, 1.0, 10.0, 100.0)
  - shots per seed per point: 25,000
- Heterogeneous same-mean sweep:
  - distances: (5, 7)
  - p_mean: (0.01, 0.02)
  - scenarios: uniform_control, local_defect_edge, local_defect_center
  - shots per seed per point: 25,000
- Temporal-drift sweep:
  - distances: (5, 7)
  - p_mean: (0.01, 0.02)
  - scenarios: constant_data_schedule, front_half_low_back_half_high, measurement_only_worse
  - shots per seed per point: 25,000
- Calibration adaptive sweep:
  - distances: (3, 5)
  - rounds: (1, 3, 5, 7)
  - snapshots: monday, wednesday, friday
  - shots per seed per point: 15,000

## Generated Artifacts

All artifacts are under results/multiseed_claims:

- Seed-level CSVs:
  - bias_sweep_seed101.csv, bias_sweep_seed202.csv, bias_sweep_seed303.csv
  - heterogeneous_noise_seed101.csv, heterogeneous_noise_seed202.csv, heterogeneous_noise_seed303.csv
  - temporal_drift_seed101.csv, temporal_drift_seed202.csv, temporal_drift_seed303.csv
  - calibration_adaptive_seed101.csv, calibration_adaptive_seed202.csv, calibration_adaptive_seed303.csv
  - decoder_comparison_seed101.csv, decoder_comparison_seed202.csv, decoder_comparison_seed303.csv
- Seed-level pairwise CSVs (where applicable):
  - decoder_comparison_seed*_pairwise.csv
  - heterogeneous_noise_seed*_pairwise.csv
  - temporal_drift_seed*_pairwise.csv
- Pooled summaries:
  - bias_sweep_multiseed_summary.csv
  - heterogeneous_noise_multiseed_summary.csv
  - temporal_drift_multiseed_summary.csv
  - calibration_adaptive_multiseed_summary.csv
  - decoder_comparison_multiseed_summary.csv
- Combined tables:
  - bias_sweep_multiseed_all.csv
  - heterogeneous_noise_multiseed_all.csv
  - temporal_drift_multiseed_all.csv
  - calibration_adaptive_multiseed_all.csv
  - decoder_comparison_multiseed_all.csv
- Config record:
  - multiseed_run_config.csv

## Interpretation Scope

- These pooled summaries support broader simulation-level claims relative to the previous single-seed refresh.
- They remain simulation evidence and should be reported with uncertainty language appropriate to finite-shot Monte Carlo data.
