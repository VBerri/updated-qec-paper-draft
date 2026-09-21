# From Majority Vote to Bias-Aware Decoding: Stim Simulations and IBM Quantum Hardware Validation of Repetition-Code Quantum Memories

The repetition code is not a complete arbitrary-state quantum error-correcting code, but it is a useful stabilizer-code testbed for studying syndrome extraction, decoder behavior, biased noise, and circuit-level error models.

This repository is currently focused on local Layer 1 and Layer 2 results:
- Layer 1: Qiskit Aer repetition-code baseline
- Layer 2: Stim + PyMatching upgrades
- Layer 3: IBM hardware validation implemented and executed (constrained protocol)

Local Layer 2 decoder note:
- The main decoder comparison is majority vote versus MWPM/PyMatching.
- MWPM is constructed directly from Stim's detector error model, so it is already the weighted detector-model decoder for this benchmark.

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

## Layer 3 hardware validation

Windows PowerShell:

```powershell
$env:IBM_QUANTUM_TOKEN="your_api_key_here"
$env:IBM_QUANTUM_INSTANCE="your_instance_crn_here"

python scripts/run_ibm_hardware_validation.py
```

Current Layer 3 artifacts:
- `results/ibm_hardware_validation_results.csv`
- `results/ibm_hardware_job_metadata.json`
- `figures/ibm_hardware_validation.png`
- `docs/layer3_results_summary.md`

Security warning:
- Never commit IBM_QUANTUM_TOKEN.
- Never paste the token into source files.
- Never share the token publicly.
