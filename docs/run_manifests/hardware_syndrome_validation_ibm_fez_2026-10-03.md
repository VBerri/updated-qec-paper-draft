# Run Manifest: Corrected Hardware Syndrome Validation

Date: 2026-10-03

## Purpose

Execute the corrected Layer-3 hardware validation path with repeated syndrome rounds, syndrome-aware logical decoding, and confidence intervals.

## Code Provenance

- Repository: `VBerri/updated-qec-paper-draft`
- Entry point: `scripts/run_ibm_hardware_syndrome_validation.py`
- Core function: `qec_cloud.ibm_hardware.run_ibm_hardware_syndrome_validation`

## Runtime Command

Executed from project root:

```powershell
C:/Users/sansu/anaconda3/python.exe .\scripts\run_ibm_hardware_syndrome_validation.py --backend ibm_fez --shots 1200 --delay-dt 256
```

## Environment and Backend

- Python: 3.13.5 (conda)
- Backend: `ibm_fez`
- Job ID: `db0ph0ivog1s73fh5km0`
- Shots per circuit: 1200
- Number of circuits/specifications: 6
- Delay parameter: `delay_dt = 256`

## Artifacts

- Results table: `results/ibm_hardware_syndrome_validation_results.csv`
- Job metadata: `results/ibm_hardware_syndrome_validation_job_metadata.json`
- Transpile summary: `results/ibm_hardware_syndrome_transpile_summary.json`
- Execution log: `logs/hw_syndrome_run.log`

## Recorded Logical Success Results

From `results/ibm_hardware_syndrome_validation_results.csv`:

- `encoded_r1_log0`: 1200 / 1200, success 1.0000, logical error 0.0000
- `encoded_r1_log1`: 1188 / 1200, success 0.9900, logical error 0.0100
- `encoded_r3_log0`: 1200 / 1200, success 1.0000, logical error 0.0000
- `encoded_r3_log1`: 1164 / 1200, success 0.9700, logical error 0.0300
- `unencoded_r3_log0`: 1191 / 1200, success 0.9925, logical error 0.0075
- `unencoded_r3_log1`: 1080 / 1200, success 0.9000, logical error 0.1000

Wilson 95% confidence intervals are saved per row in the CSV (`ci95_low`, `ci95_high`).

## Notes

- Runtime API migration fix applied: hardware execution now uses Runtime SamplerV2 and syndrome-aware decoding from returned bitstring counts.
- This run is evidence of corrected execution/decoding path, not a threshold-level or broad hardware-advantage claim.
