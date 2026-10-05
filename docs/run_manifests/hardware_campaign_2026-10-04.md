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
- The **completed main campaign** (`...002755Z` through `...003102Z`, 9 runs) matches the **per-data-qubit preparation-to-final-measurement interval in the transpiler schedule**. Every control reports `memory_interval_delta_dt = 0` in `timing_comparison.json` (the scheduled control delay reproduces the encoded data qubit's scheduled memory interval exactly), and `runtime_metadata.json` records `matching_defined_over = "data_qubit_memory_interval"`.
- This match is established from the local transpiler schedule, not from the returned device pulse trace. Where the returned experimental `scheduler_timing` traces are reliably associated and comparable, the encoded-vs-control memory interval agrees to a median of ~1 dt and at most ~8 dt (~32 ns) in 60 of 61 comparable traces. The returned scheduler-timing field is itself unreliable: 34 of 144 traces carry measured-qubit/preparation signatures inconsistent with their label (despite correct returned circuit identifiers), so it is treated as indicative only, not as exact on-device verification. Decoder counts and circuit identification are unaffected and independently verified.
- The earlier `...200757Z / ...200817Z / ...200831Z` runs are a 128-shot pilot that matched only **total scheduled circuit duration** (unequal per-qubit memory exposure, up to ~473 dt / ~1.9 us). They are retained as archival pilot evidence and are not used for the memory comparison.

## Frozen Configuration

- Backend: `ibm_fez`
- Physical path order: `data0, anc0, data1, anc1, data2 = [0,1,2,3,16]`
- Transpiler seed: `7`
- Optimization level: `1`
- Acquired main campaign (interval-matched): `2000` shots/circuit, delays `0, 128, 384` dt, `3` blocks (9 runs, 6000 encoded shots per condition)
- Earlier pilot (archival): `128` shots/circuit, delays `0, 128, 384` dt, one run per delay

## Commands

```powershell
python scripts/run_ibm_hardware_pilot.py --backend ibm_fez --shots 256 --delay-dt 0 --physical-path 0,1,2,3,16 --seed-transpiler 7
python scripts/run_ibm_hardware_main_blocks.py --backend ibm_fez --shots 2000 --delays-dt 0,128,384 --blocks 3 --physical-path 0,1,2,3,16 --seed-transpiler 7 --shuffle-circuit-order
python scripts/analyze_ibm_hardware_campaign.py --run-list results/ibm_hardware_main_campaign_run_list.txt --min-shots 1000
python scripts/run_ibm_hardware_fault_diagnostic.py --backend ibm_fez --shots 256 --rounds 3 --delay-dt 0 --physical-path 0,1,2,3,16
```

## Execution Status

- Early placeholder/pilot jobs and the pre-fix main attempt produced run directories from `20261004T181808Z` onward; these are retained as archival evidence only.
- **Completed interval-matched main campaign** (2000 shots/circuit, 3 blocks x delays 0/128/384, interleaved circuit order): 9 run directories from `20261005T002755Z` through `20261005T003102Z`, listed in `results/ibm_hardware_main_campaign_run_list.txt`.
- Across all 9 runs: every control reports `memory_interval_delta_dt = 0` in the transpiler schedule, every `pub_association_check.json` reports matching measured qubits, and every returned `circuit_id` matches the submitted circuit (144/144).
- Aggregated to 6000 encoded shots per (rounds, logical_bit, delay) condition in `results/ibm_hardware_campaign_summary.csv`.
- Returned device scheduler-timing traces analyzed in `results/ibm_hardware_scheduler_timing_report.json`: among reliably-associated traces the encoded-vs-control interval agrees to ~1 dt median / ~8 dt max; 34/144 returned traces are mis-associated by measured-qubit signature (an experimental-field limitation that does not affect counts or circuit identification).
- Earlier 128-shot pilot (`...200757Z / ...200817Z / ...200831Z`, total-duration-matched) retained as archival pilot evidence.
- Fault-diagnostic run completed (12 encoded diagnostic circuits): `job_id=db1b29uegvvc73bhdfeg`.
- Circuit-to-label association for all campaign runs verified offline from QPY artifacts: `results/ibm_hardware_association_report.json` (`all_ok = true`).

Reproduce the association check:

```powershell
python scripts/verify_hardware_run_association.py (Get-Content results/ibm_hardware_main_campaign_run_list.txt) --out results/ibm_hardware_association_report.json
```

Analyze returned device scheduler-timing traces (interval tolerance and signature consistency):

```powershell
python scripts/analyze_hardware_scheduler_timing.py (Get-Content results/ibm_hardware_main_campaign_run_list.txt) --out results/ibm_hardware_scheduler_timing_report.json
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
- In the 9 main-campaign run directories, every control row in `timing_comparison.json` reports `memory_interval_delta_dt = 0` in the transpiler schedule.
- Returned device pulse traces agree to ~1 dt median / ~8 dt max among reliably-associated traces (`results/ibm_hardware_scheduler_timing_report.json`); the returned scheduler-timing field is mis-associated for 34/144 circuits and is therefore indicative only.
- The archival 128-shot pilot runs report only `duration_match_delta_dt = 0` (total scheduled duration) and predate memory-interval matching.

## Notes

- Claims are restricted to computational-basis memory behavior with offline decoding.
- The history decoder is a history-based heuristic dynamic-programming decoder, not a full detector-graph MWPM implementation on hardware counts.
- The main campaign uses transpiler-schedule interval-matched controls. The observed encoded-vs-control advantage is specific to these computational-basis preparations, this fixed layout, and these schedule conditions; it is not an established general memory-lifetime advantage, a universal decoder ranking, a threshold claim, or real-time correction.
