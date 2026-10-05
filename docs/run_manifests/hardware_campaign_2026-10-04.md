# Run Manifest: Hardware Syndrome Campaign (Assignment Patch)

Date: 2026-10-04

## Scope

This manifest tracks the assignment-driven hardware work with:
- fixed five-qubit physical path
- computational-basis memory only
- offline decoding only
- two decoders on identical encoded shots (final-data majority and history-based heuristic decoder)
- unencoded controls on all three data qubits

Timing-matching status:
- The committed `...200757Z / ...200817Z / ...200831Z` runs matched **total scheduled circuit duration** between encoded and control circuits. They did **not** equalize the per-data-qubit preparation-to-final-measurement interval (memory exposure). In those runs the single-qubit control places all of its wait before one measurement, whereas the encoded data qubit is measured before the final ancilla operations, so the control was exposed longer (up to roughly 473 dt, about 1.9 us at dt = 4 ns). These runs must not be used to claim a fair memory-lifetime advantage.
- The runner now matches the **data-qubit memory interval** (`matching_defined_over = "data_qubit_memory_interval"` in `runtime_metadata.json`). New runs record per-qubit interval deltas in `timing_comparison.json`. Interval-matched hardware data has not yet been acquired.

## Frozen Configuration

- Backend: `ibm_fez`
- Physical path order: `data0, anc0, data1, anc1, data2 = [0,1,2,3,16]`
- Transpiler seed: `7`
- Optimization level: `1`
- Planned main design (not yet acquired): `2000` shots/circuit, delays `0, 128, 384` dt, `3` blocks
- Acquired pilot: `128` shots/circuit, delays `0, 128, 384` dt, one run per delay

## Commands

```powershell
python scripts/run_ibm_hardware_pilot.py --backend ibm_fez --shots 256 --delay-dt 0 --physical-path 0,1,2,3,16 --seed-transpiler 7
python scripts/run_ibm_hardware_main_blocks.py --backend ibm_fez --shots 2000 --delays-dt 0,128,384 --blocks 3 --physical-path 0,1,2,3,16 --seed-transpiler 7 --shuffle-circuit-order
python scripts/analyze_ibm_hardware_campaign.py --run-list results/ibm_hardware_main_campaign_run_list.txt --min-shots 100
python scripts/run_ibm_hardware_fault_diagnostic.py --backend ibm_fez --shots 256 --rounds 3 --delay-dt 0 --physical-path 0,1,2,3,16
```

## Execution Status

- Early placeholder/pilot jobs and the pre-fix main attempt produced run directories from `20261004T181808Z` onward; these are retained as archival evidence only.
- Acquired corrected pilot (128 shots/circuit, one run per delay, total-duration-matched controls):
	- `results/ibm_hardware_syndrome_validation_results_syndrome_validation_20261004T200757Z` (delay 0)
	- `results/ibm_hardware_syndrome_validation_results_syndrome_validation_20261004T200817Z` (delay 128)
	- `results/ibm_hardware_syndrome_validation_results_syndrome_validation_20261004T200831Z` (delay 384)
- This is a pilot, not the planned 3-block, 2000-shot main campaign. The planned campaign is deferred until interval-matched controls are acquired.
- Fault-diagnostic run completed (12 encoded diagnostic circuits): `job_id=db1b29uegvvc73bhdfeg`.
- Circuit-to-label association for all committed runs verified offline from QPY artifacts: `results/ibm_hardware_association_report.json` (`all_ok = true`).

Reproduce the association check:

```powershell
python scripts/verify_hardware_run_association.py (Get-Content results/ibm_hardware_main_campaign_run_list.txt) --out results/ibm_hardware_association_report.json
```

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
- `pub_association_check.json` (new runs)
- `circuits/*_original.qpy`
- `circuits/*_transpiled.qpy`

Global outputs:
- `results/ibm_hardware_syndrome_validation_job_metadata.json`
- `results/ibm_hardware_syndrome_transpile_summary.json`
- `results/ibm_hardware_campaign_aggregate.csv`
- `results/ibm_hardware_campaign_summary.csv`
- `results/ibm_hardware_fault_diagnostic_results_syndrome_validation_20261004T200358Z/ibm_hardware_fault_diagnostic_results.csv`

Timing check:
- In the committed pilot run directories, `timing_comparison.json` reports `duration_match_delta_dt = 0` (total scheduled circuit duration matched).
- These pilot runs predate memory-interval matching, so per-qubit `memory_interval_delta_dt` is not reported for them. New runs report it and target `0`.

## Notes

- Claims are restricted to computational-basis memory behavior with offline decoding.
- The history decoder is a history-based heuristic dynamic-programming decoder, not a full detector-graph MWPM implementation on hardware counts.
- The committed hardware data is a 128-shot pilot. Fair memory-lifetime comparison requires the interval-matched acquisition that is implemented but not yet run.
- This is not a threshold claim and not real-time correction.
