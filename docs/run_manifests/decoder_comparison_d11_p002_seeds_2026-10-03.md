# Run Manifest: Decoder Comparison Corrected Slice

Date: 2026-10-03

## Purpose

First corrected evidence-grade decoder-comparison slice after Workstream A refactor, using identical sampled shots for all decoders and a true final-data majority baseline.

## Code Provenance

- Repository: `VBerri/updated-qec-paper-draft`
- Commit used for run: `33554aa`
- Entry point: `qec_stim.decoder_comparison.run_decoder_comparison`

## Environment

- Python: 3.13.5
- stim: 1.16.0
- pymatching: 2.4.0
- numpy: 2.1.3
- pandas: 2.2.3

## Command Pattern

Executed from project root with `PYTHONPATH=src`, looping over seeds:

- shots: 100000
- distances: (11,)
- p_values: (0.02,)
- include_neural: False
- seeds: 101, 202, 303
- output CSV per seed:
  - `results/corrected_runs/decoder_comparison_d11_p002_seed101.csv`
  - `results/corrected_runs/decoder_comparison_d11_p002_seed202.csv`
  - `results/corrected_runs/decoder_comparison_d11_p002_seed303.csv`
- summary CSV:
  - `results/corrected_runs/decoder_comparison_d11_p002_summary.csv`

## Integer Failure Counts (per 100,000 shots)

Seed 101:
- final_data_majority: 22857 failures
- detector_count_heuristic: 23037 failures
- unweighted_mwpm: 168 failures
- mwpm: 98 failures

Seed 202:
- final_data_majority: 23027 failures
- detector_count_heuristic: 22956 failures
- unweighted_mwpm: 148 failures
- mwpm: 82 failures

Seed 303:
- final_data_majority: 23001 failures
- detector_count_heuristic: 23123 failures
- unweighted_mwpm: 152 failures
- mwpm: 76 failures

## Notes

- Decoder results are produced from the same sampled measurement records for each (distance, p, seed) point.
- Detector events and observable flips are derived via Stim measurement-to-detector conversion from those same records.
- Pairwise method overlap files are generated automatically alongside each per-seed CSV with suffix `_pairwise.csv`.
