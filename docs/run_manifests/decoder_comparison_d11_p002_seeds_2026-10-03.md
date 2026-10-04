# Run Manifest: Decoder Comparison Corrected Slice (Superseded)

Status: superseded legacy record. The values in this file are not the final evidence used by the corrected analysis and should not be cited in the manuscript or downstream plots.

Date: 2026-10-03

## Purpose

This manifest records a stale earlier decoder-comparison slice produced before the majority-vote scoring correction was finalized. The corrected evidence now lives under `results/corrected_runs/decoder_comparison_d11_p002_summary.csv` and its per-seed files.

## Corrected Evidence Values

The final corrected summary (per 100,000 shots) is:

- Seed 101: final_data_majority = 5518, detector_count_heuristic = 23037, unweighted_mwpm = 168, mwpm = 98
- Seed 202: final_data_majority = 5423, detector_count_heuristic = 22956, unweighted_mwpm = 148, mwpm = 82
- Seed 303: final_data_majority = 5386, detector_count_heuristic = 23123, unweighted_mwpm = 152, mwpm = 76

## Supersession Notes

- The earlier values in this file were generated with the incorrect majority-vote scoring target and are therefore legacy-only.
- The corrected comparison uses the same sampled measurement records, but final-data majority is now scored against the prepared logical bit instead of the raw detector event count.
- Pairwise overlap summaries remain in the per-seed files with suffix `_pairwise.csv`.

## Canonical Evidence Path

- `results/corrected_runs/decoder_comparison_d11_p002_seed101.csv`
- `results/corrected_runs/decoder_comparison_d11_p002_seed202.csv`
- `results/corrected_runs/decoder_comparison_d11_p002_seed303.csv`
- `results/corrected_runs/decoder_comparison_d11_p002_summary.csv`
