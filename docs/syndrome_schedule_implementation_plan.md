# Syndrome-Schedule Implementation Plan (Separate Extension)

## Purpose

This document proposes a separate experiment to compare syndrome rounds 0, 1, 3, and 5 at fixed per-data-qubit scheduled memory intervals.

This plan is additive. It does not replace existing Layer 1, Layer 2, or Layer 3 experiments.

## Scope and Guardrails

- Compare only round-count variants: 0, 1, 3, 5.
- Keep per-data-qubit scheduled memory interval fixed across variants.
- Use time-dependent idle-noise models in simulation.
- Split calibration and evaluation data into separate datasets.
- Do not submit hardware jobs as part of this extension.
- Do not claim novelty or improved performance in plan text or outputs.
- Keep physical noise rates fixed across compared schedules.

## Primary Question

At equal scheduled memory exposure per data qubit, how does changing syndrome round count (0, 1, 3, 5) affect logical error under time-dependent idle noise?

## Experimental Design

### 1) Schedule-Normalized Circuits

- Build four encoded circuit families with rounds in {0, 1, 3, 5}.
- For each family, tune delay placement so each data qubit has the same scheduled prep-to-final-measurement interval.
- Record schedule audit metadata per circuit:
  - target interval
  - achieved interval
  - residual delta
  - per-qubit interval vector

### 2) Time-Dependent Idle Noise

- Define nonstationary idle-noise profiles over the memory window (for example: low->high drift, high->low recovery, piecewise pulse).
- Apply the same profile class and the same physical rate parameters across all round-count variants.
- Integrate idle noise over each circuit's actual idle periods from schedule timing; do not renormalize rates to cancel schedule-dependent costs.
- Keep non-idle channels fixed unless explicitly part of sensitivity checks.

### 3) Calibration/Evaluation Split

- Calibration dataset:
  - Uses a fixed calibration budget (pre-specified number of shots and calibration windows).
  - Used to select syndrome round count R in {0, 1, 3, 5} using a predetermined selection rule.
  - May tune decoder weights only within the selected round count.
  - No final metric reporting from this split.
- Evaluation dataset:
  - Held out and never used for round-count selection or decoder tuning.
  - Used for all reported round-comparison metrics.
- Store split manifests and seeds for reproducibility.

Predetermined selection rule (example to lock before running):
- Select the round count with minimum calibration logical error; if ties are within epsilon, choose the smallest round count.
- Record the exact epsilon and tie-break priority in the calibration manifest.

### 4) Decoders

Evaluate at least:
- final_data_majority (including explicit R=0 decoding path)
- unweighted_mwpm
- mwpm (detector-model weighted)

Input-space coverage requirements:
- Evaluate both logical inputs (0 and 1).
- Track gate, measurement, reset, and idle-time costs for each round-count schedule.

Optional additional decoders may be included, but must be reported as secondary.

### 5) Outputs

Proposed new artifacts (separate from current baseline files):
- results/syndrome_schedule_round_comparison.csv
- results/syndrome_schedule_round_comparison_pairwise.csv
- results/syndrome_schedule_schedule_audit.csv
- results/syndrome_schedule_calibration_manifest.json
- results/syndrome_schedule_evaluation_manifest.json
- figures/syndrome_schedule_round_comparison.png
- figures/syndrome_schedule_schedule_residuals.png
- docs/syndrome_schedule_notes.md

## Analysis and Reporting Rules

- Report logical error rate and confidence intervals on evaluation split only.
- Include pairwise decoder disagreement summaries on the same shots.
- Include schedule residual summaries to demonstrate interval matching quality.
- Report fixed-schedule baselines (R=0, R=1, R=3, R=5) even when a calibration-selected round count is highlighted.
- Explicitly state this is a controlled extension experiment.
- Do not state or imply improved performance claims unless directly supported by held-out evaluation data.

## Implementation Steps

1. Add schedule-normalization helper for rounds {0,1,3,5}.
2. Add time-dependent idle-noise profile generator module.
3. Add calibration/evaluation split manifest writer.
4. Add experiment runner script (local simulation only).
5. Add plotting and audit-summary utilities.
6. Add tests for:
   - interval matching tolerance checks
   - split isolation (no overlap)
   - stable artifact schema
7. Document assumptions and limitations in syndrome_schedule_notes.

## Non-Goals

- No replacement of current decoder comparison or drift experiments.
- No IBM hardware submission.
- No claims of state-of-the-art performance.
