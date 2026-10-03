# From Majority Vote to Bias-Aware Decoding: Stim Simulations and IBM Quantum Hardware Validation of Repetition-Code Quantum Memories

The repetition code is not a complete arbitrary-state quantum error-correcting code, but it is a useful stabilizer-code testbed for studying syndrome extraction, decoder behavior, biased noise, and circuit-level error models.

This repository is currently focused on local Layer 1 and Layer 2 results:
- Layer 1: Qiskit Aer repetition-code baseline
- Layer 2: Stim + PyMatching upgrades
- Layer 3: IBM hardware validation implemented and executed (constrained protocol)

Local Layer 2 decoder note:
- The main decoder comparison is majority vote versus MWPM/PyMatching.
- MWPM is constructed directly from Stim's detector error model, so it is already the weighted detector-model decoder for this benchmark.

New adaptive-decoder experiment:
- Uses the same circuit, same shots, and same sampled syndrome records, then changes only the decoder.
- Compares four decoders on identical syndrome samples: majority vote, uniform MWPM, static weighted MWPM, calibration-aware MWPM.
- Sweeps repeated syndrome rounds and multiple calibration snapshots (monday/wednesday/friday style).
- Reports logical error with Wilson 95% confidence intervals and adaptive-minus-static gain summary.

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

## Calibration-aware decoder study (same-syndrome fairness design)

```bash
python scripts/run_calibration_adaptive_decoder.py --mode quick
```

Outputs:
- `results/calibration_adaptive_decoder_results.csv`
- `results/calibration_adaptive_gain_summary.csv`
- `figures/calibration_adaptive_rounds.png`

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
