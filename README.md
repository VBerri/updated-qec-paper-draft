# From Majority Vote to Bias-Aware Decoding: Stim Simulations and IBM Quantum Hardware Validation of Repetition-Code Quantum Memories

The repetition code is not a complete arbitrary-state quantum error-correcting code, but it is a useful stabilizer-code testbed for studying syndrome extraction, decoder behavior, biased noise, and circuit-level error models.

Local workflows in this repository run Layer 1 and Layer 2 experiments. Layer 3 hardware runners are invoked separately.

## Install

```bash
pip install -r requirements.txt
```

## Quick local test

```bash
python scripts/run_all.py --mode quick
```

## Full local Layer 1 + Layer 2 run

```bash
python scripts/run_all.py --mode full-local
```

## Layer 3 later

Completed campaign note:
- A completed IBM hardware campaign on `ibm_fez` is documented in [docs/run_manifests/hardware_campaign_2026-10-04.md](docs/run_manifests/hardware_campaign_2026-10-04.md).
- Campaign run-list manifest: [results/ibm_hardware_main_campaign_run_list.txt](results/ibm_hardware_main_campaign_run_list.txt).

Windows PowerShell:

```powershell
$env:IBM_QUANTUM_TOKEN="your_api_key_here"
$env:IBM_QUANTUM_INSTANCE="your_instance_crn_here"

python scripts/run_ibm_hardware_validation.py
```

Security warning:
- Never commit IBM_QUANTUM_TOKEN.
- Never paste the token into source files.
- Never share the token publicly.

Decoder naming used in Layer 2:
- `final_data_majority`
- `detector_count_heuristic` (control baseline)
- `unweighted_mwpm`
- `mwpm` (detector-model weighted via PyMatching)
