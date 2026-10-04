# Run Manifest: Hardware Syndrome Campaign (Assignment Patch)

Date: 2026-10-04

## Scope

This manifest tracks the assignment-driven hardware campaign with:
- fixed five-qubit physical path
- computational-basis memory only
- offline decoding only
- two decoders on identical encoded shots (final-data majority and history-aware)
- duration-matched unencoded controls on all three data qubits

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
python scripts/run_ibm_hardware_main_blocks.py --backend ibm_fez --shots 2000 --delays-dt 0,128,384 --blocks 3 --physical-path 0,1,2,3,16 --seed-transpiler 7
python scripts/analyze_ibm_hardware_campaign.py
```

## Execution Status

- Pilot completed on frozen path: `job_id=db1ap7rid5ic73eqt3t0`.
- Main campaign produced 10 run directories from `20261004T194515Z` onward.
- Target design required 9 runs (3 blocks x 3 delays); one additional delay-384 run was collected as an extra replication.

Current run-directory count command:

```powershell
python -c "from pathlib import Path; d=Path('results'); xs=sorted([p.name for p in d.glob('ibm_hardware_syndrome_validation_results_syndrome_validation_*')]); ys=[x for x in xs if x.rsplit('_',1)[-1]>='20261004T194515Z']; print(len(ys)); [print(x) for x in ys]"
```

Returned count: `10`.

## Required Artifacts

Each run directory under `results/ibm_hardware_syndrome_validation_results_syndrome_validation_*` contains:
- `ibm_hardware_syndrome_validation_results.csv`
- `raw_counts.json`
- `runtime_metadata.json`
- `bit_mapping.json`
- `circuits/*_original.qpy`
- `circuits/*_transpiled.qpy`

Global outputs:
- `results/ibm_hardware_syndrome_validation_job_metadata.json`
- `results/ibm_hardware_syndrome_transpile_summary.json`
- `results/ibm_hardware_campaign_aggregate.csv`
- `results/ibm_hardware_campaign_summary.csv`

Shot totals in `results/ibm_hardware_campaign_summary.csv`:
- Delay `0` and `128`: 6000 encoded shots per (rounds, logical_bit) condition (3 runs x 2000).
- Delay `384`: 8000 encoded shots per (rounds, logical_bit) condition (4 runs x 2000, includes extra replication).

## Notes

- Claims are restricted to computational-basis memory behavior with offline decoding.
- This is not a threshold claim and not real-time correction.
