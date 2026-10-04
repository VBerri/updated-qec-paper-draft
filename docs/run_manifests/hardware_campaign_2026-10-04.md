# Run Manifest: Hardware Syndrome Campaign (Assignment Patch)

Date: 2026-10-04

## Scope

This manifest tracks the assignment-driven hardware campaign with:
- fixed five-qubit physical path
- computational-basis memory only
- offline decoding only
- two decoders on identical encoded shots (final-data majority and history-based heuristic decoder)
- exact transpiled-duration-matched unencoded controls on all three data qubits

## Frozen Configuration

- Backend: `ibm_fez`
- Physical path order: `data0, anc0, data1, anc1, data2 = [0,1,2,3,16]`
- Transpiler seed: `7`
- Optimization level: `1`
- Pilot shots per circuit: `256`
- Main shots per circuit per block: `2000`
- Main delays (dt): `0, 128, 384`
- Blocks: `3`

## Commands

```powershell
python scripts/run_ibm_hardware_pilot.py --backend ibm_fez --shots 256 --delay-dt 0 --physical-path 0,1,2,3,16 --seed-transpiler 7
python scripts/run_ibm_hardware_main_blocks.py --backend ibm_fez --shots 2000 --delays-dt 0,128,384 --blocks 3 --physical-path 0,1,2,3,16 --seed-transpiler 7 --shuffle-circuit-order
python scripts/analyze_ibm_hardware_campaign.py --run-list results/ibm_hardware_main_campaign_run_list.txt --min-shots 100
python scripts/run_ibm_hardware_fault_diagnostic.py --backend ibm_fez --shots 256 --rounds 3 --delay-dt 0 --physical-path 0,1,2,3,16
```

## Execution Status

- Pilot completed on frozen path: `job_id=db1ap7rid5ic73eqt3t0`.
- Pre-fix main campaign produced 10 run directories from `20261004T194515Z` onward; these are retained as archival evidence.
- Corrected timing validation multi-delay run list (exact encoded/control transpiled duration match):
	- `results/ibm_hardware_syndrome_validation_results_syndrome_validation_20261004T200757Z`
	- `results/ibm_hardware_syndrome_validation_results_syndrome_validation_20261004T200817Z`
	- `results/ibm_hardware_syndrome_validation_results_syndrome_validation_20261004T200831Z`
- Fault-diagnostic campaign completed (12 encoded diagnostic circuits): `job_id=db1b29uegvvc73bhdfeg`.

Current corrected-run list file:

```powershell
Get-Content results/ibm_hardware_main_campaign_run_list.txt
```

## Required Artifacts

Each run directory under `results/ibm_hardware_syndrome_validation_results_syndrome_validation_*` contains:
- `ibm_hardware_syndrome_validation_results.csv`
- `raw_counts.json`
- `runtime_metadata.json`
- `bit_mapping.json`
- `timing_comparison.json`
- `transpile_summary.json`
- `circuits/*_original.qpy`
- `circuits/*_transpiled.qpy`

Global outputs:
- `results/ibm_hardware_syndrome_validation_job_metadata.json`
- `results/ibm_hardware_syndrome_transpile_summary.json`
- `results/ibm_hardware_campaign_aggregate.csv`
- `results/ibm_hardware_campaign_summary.csv`
- `results/ibm_hardware_fault_diagnostic_results_syndrome_validation_20261004T200358Z/ibm_hardware_fault_diagnostic_results.csv`

Corrected timing check:
- In each corrected run directory listed in `results/ibm_hardware_main_campaign_run_list.txt`, all rows in `timing_comparison.json` report `duration_match_delta_dt = 0`.

## Notes

- Claims are restricted to computational-basis memory behavior with offline decoding.
- The history decoder is a history-based heuristic dynamic-programming decoder, not a full detector-graph MWPM implementation on hardware counts.
- This is not a threshold claim and not real-time correction.
