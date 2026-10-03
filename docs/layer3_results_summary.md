# Layer 3 Results Summary

## Run metadata
- Backend: `ibm_fez`
- Latest job ID: `danhhhlr85ps73fe2ffg`
- Shots: `1000`
- Circuits: `3`

Three-run metadata:
- Run 1 job ID: `danhfqn8gn2s739mlcp0`
- Run 2 job ID: `danhhqg2fm4c73f47lfg`
- Run 3 job ID: `danhhhlr85ps73fe2ffg`

Source files:
- `results/ibm_hardware_job_metadata.json`
- `results/ibm_hardware_validation_results.csv`
- `figures/ibm_hardware_validation.png`

## Hardware outcomes
Latest run outcomes:

| label   | basis | idle_steps | logical_success_probability | logical_error_rate |
|---------|-------|------------|-----------------------------|--------------------|
| z_idle_2 | Z     | 2          | 0.999                       | 0.001              |
| z_idle_4 | Z     | 4          | 1.0                         | 0.0                |
| x_idle_4 | X     | 4          | 1.0                         | 0.0                |

## Comparison against local reference trend
For this minimal validation, the hardware values were compared against ideal local-reference expectation (`success = 1.0`) at the same circuit structure (`results/layer3_hardware_vs_reference.csv`).

## Three-run stability check
Three constrained runs were completed on the same backend and shot budget. Pairwise run-1/run-2 deltas are recorded in `results/layer3_repeatability_summary.csv`, and aggregated three-run statistics are in `results/layer3_three_run_summary.csv`.

Per-circuit aggregate over 3 runs:

| label   | min_success | max_success | mean_success | range |
|---------|-------------|-------------|--------------|-------|
| z_idle_2 | 0.999       | 1.000       | 0.9997       | 0.001 |
| z_idle_4 | 0.999       | 1.000       | 0.9997       | 0.001 |
| x_idle_4 | 1.000       | 1.000       | 1.0000       | 0.000 |

Interpretation:
- The observed variation is very small (maximum range across 3 runs = `0.001`) and consistent with finite-shot statistical fluctuation at 1000-shot scale.
- Layer 3 is now validated for execution, artifact generation, and short-horizon repeatability under the constrained protocol.

This confirms the end-to-end cloud path, credential flow, job submission, and result extraction are working.

## Recommended follow-up
1. If available, run one additional backend to sample backend-to-backend variance.
2. Keep Layer 3 in constrained mode until final paper packaging.