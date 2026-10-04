# Submission Materials Index

This folder contains publication-ready copies of final non-hardware figures and reproducibility artifacts that are tracked in Git.

## Figure Bundle (Tracked)

The following figure files are tracked here even though the main `figures/` folder PNGs are ignored:

- figures/bias_heatmap.png
- figures/bias_curves_by_distance.png
- figures/heterogeneous_noise_plot.png
- figures/temporal_drift_plot.png
- figures/calibration_adaptive_rounds.png
- figures/decoder_comparison.png
- figures/stim_logical_error_vs_p.png

## Reproducibility Artifacts

Representative `.stim` circuits and matching `.dem` files are in:

- reproducibility/stim_dem/

Included exports:

- decoder_comparison_d11_r11_p0p02.{stim,dem}
- bias_sweep_d7_r7_ptotal0p02_bias10.{stim,dem}
- heterogeneous_center_defect_d7_r7_pmean0p02.{stim,dem}
- temporal_fronthalf_low_backhalf_high_d7_r10_pmean0p02.{stim,dem}
- calibration_friday_d5_r7_ptotal0p02_bias2p5.{stim,dem}

## Provenance Notes

- Refresh workflow baseline before new regeneration work: commit 2c3cc67.
- Refresh implementation and regenerated outputs were committed as d183967.
- Exact refresh replay requires d183967 or later because seed-enabled non-hardware commands were added there.

## Scope Notes

- This folder now contains two distinct evidence tiers:
	- Single-seed refresh tier (seed 12345) from the first non-hardware correction pass.
	- Multi-seed broader-claim tier (seeds 101, 202, 303) stored under results/multiseed_claims with pooled summaries and pairwise summaries.
- The corrected decoder-comparison diagnostic slice at d=11, p=0.02 in results/corrected_runs uses 300,000 total shots (three seeds x 100,000 shots).
- The broader decoder grid in results/multiseed_claims uses 75,000 total shots per grid point (three seeds x 25,000 shots).
- Different estimates between the 300,000-shot diagnostic slice and the 75,000-shot grid slice are expected finite-sample variation, not a methodological contradiction.
