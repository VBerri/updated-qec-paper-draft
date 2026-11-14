# Professor Response Summary

## Professor suggestion 1
Try biased error or more complicated error modeling beyond uniform Pauli errors using Stim.

## Response
We added Stim circuit-level simulations, biased Pauli noise, measurement noise, heterogeneous noise, and temporal drift.

## Professor suggestion 2
Try something more interesting on the decoder side.

## Response
We compared `final_data_majority`, `unweighted_mwpm`, and detector-model weighted `mwpm` (PyMatching from Stim DEM), with `detector_count_heuristic` as a control baseline and an optional toy FiLM-style neural decoder.

## IBM validation
Completed on `ibm_fez` with raw evidence preserved.

Manifest and evidence links:
- [docs/run_manifests/hardware_campaign_2026-10-04.md](docs/run_manifests/hardware_campaign_2026-10-04.md)
- [results/ibm_hardware_main_campaign_run_list.txt](results/ibm_hardware_main_campaign_run_list.txt)
- [results/ibm_hardware_scheduler_timing_report.json](results/ibm_hardware_scheduler_timing_report.json)
