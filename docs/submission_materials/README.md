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

- Refreshed bias, heterogeneity, temporal-drift, and calibration sweeps in this package are single-seed runs (`12345`) for the reported simulated conditions.
- The corrected decoder-comparison slice at `d=11, p=0.02` uses three seeds and remains the designated corrected comparison evidence.
