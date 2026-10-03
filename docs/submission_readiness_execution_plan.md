# Submission Readiness Execution Plan (Evidence-Aligned)

This plan operationalizes the review constraints and includes a required hardware workstream.

## Goal

Produce a professor-ready paper where every claim is backed by corrected experiments, run manifests, and reproducible artifacts.

## Workstream A: Decoder Comparison Fix (Required, first)

Files:
- `src/qec_stim/decoder_comparison.py`
- `src/qec_stim/mwpm_decode.py`
- `tests/test_decoders.py`

Actions:
1. Keep `detector_count_heuristic` as weak control only.
2. Add true final-data majority baseline from terminal data-qubit readout.
3. Score matching and majority on identical shots.
4. Save pairwise win/loss counts (or per-shot masks).
5. Add sanity checks:
- zero noise -> zero failures
- single data fault -> expected detector/local logical behavior
- measurement fault -> expected time-like pattern
- both logical input values tested

Run grid:
- `d = 3,5,7,9,11`, `r = d`, `p = 0.005, 0.01, 0.02, 0.05`
- fixed-duration slice `r = 5` at `p = 0.01, 0.02`
- 3 recorded seeds
- start 100,000 shots/point/seed

## Workstream B: Real Biased Noise (Required for bias claims)

Files:
- `src/qec_stim/stim_circuits.py`
- `src/qec_stim/stim_experiments.py`
- `tests/test_noise_models.py`

Actions:
1. Replace end-of-circuit `PAULI_CHANNEL_1` approximation with explicit round-aware insertion before syndrome/readout.
2. Use correct data-qubit mapping, not `0..distance-1` assumption.
3. Hold non-bias rates fixed while sweeping bias.
4. Document exactly what channels are included/excluded.

Run grid:
- `d = 3,5,7`, `r = d`
- `p_total = 0.01, 0.02`
- `b = 0.1, 1, 10, 100`
- 3 recorded seeds, 100,000 shots/point/seed

## Workstream C: True Spatial Heterogeneity (Recommended)

Files:
- `src/qec_stim/stim_experiments.py`
- `src/qec_stim/stim_circuits.py`

Actions:
1. Apply per-qubit rates directly (not mean-collapsed).
2. Same-mean control vs local-defect scenarios.
3. Compare:
- final-data majority
- unit-weight MWPM
- nominal uniform-weight MWPM
- model-matched DEM-weighted MWPM (oracle control)

Initial scope:
- `d = 5,7`, `r = d`, mean rates `0.01, 0.02`
- edge-defect and center-defect
- 3 seeds, 100,000 shots/point/seed

## Workstream D: Temporal Drift (Optional unless claimed)

Files:
- `src/qec_stim/stim_experiments.py`

Actions:
1. Implement real per-round schedules (not averaged collapse).
2. Separate data-drift and measurement-only perturbations.
3. Decode with nominal vs true schedule models on identical samples.

Initial scope:
- `d = 5,7`, `r = 10`
- constant vs front-half/late-half schedule with same mean
- 3 seeds, 100,000 shots/point/seed

## Workstream E: Hardware (Required by project direction)

Current hardware files remain execution checks only:
- `src/qec_baseline/qiskit_circuits.py`
- `src/qec_cloud/ibm_hardware.py`

To claim hardware QEC behavior, implement new validated circuits with ancillas and repeated syndrome rounds:
1. `d=3` data + 2 ancillas parity extraction for 1 and 3 rounds.
2. Mid-circuit measure/reset retained and verified post-transpile.
3. Explicit delays with units (not only identity gate counts).
4. Save original + transpiled circuits, layout, timing, and job metadata.
5. Include unencoded duration-matched control.
6. Test both logical input values.
7. Decoder must consume syndrome record from hardware outputs.

Budget policy:
- start with constrained jobs
- no additional quota burn until local validation passes

## Artifact and Provenance Requirements (Mandatory for all runs)

For each corrected run, save:
1. Git commit hash
2. command/config and software versions
3. seed(s), shot budget, decoder settings
4. circuit hash and exported `.stim` + DEM
5. integer failures + total shots
6. full spatial rates or temporal schedules (not only averages)
7. verification checks report (zero-noise/single-fault/measurement-fault)

## Paper Rewrite Constraints

Allowed strong claims now:
- Stim distance scaling
- weighted vs unweighted matching comparison

Constrained claims:
- detector_count_heuristic is weak control, not true majority decoder
- heterogeneous/drift claims only after corrected implementations
- hardware results currently execution-path checks unless new syndrome-round hardware workflow is completed
