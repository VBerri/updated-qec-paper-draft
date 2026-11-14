# From Majority Vote to Bias-Aware Decoding: Stim Simulations and IBM Quantum Hardware Validation of Repetition-Code Quantum Memories

The repetition code is not a complete arbitrary-state quantum error-correcting code, but it is a useful stabilizer-code testbed for studying syndrome extraction, decoder behavior, biased noise, and circuit-level error models.

This phase runs local Layer 1 and Layer 2 only.

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
