# From Majority Vote to Bias-Aware Decoding: Stim Simulations and IBM Quantum Hardware Validation of Repetition-Code Quantum Memories

## 1. Abstract

This project studies repetition-code memory in a layered workflow. Layer 1 reproduces a Qiskit Aer baseline across bit-flip, phase-flip, and depolarizing noise. Layer 2 upgrades the analysis to Stim detector-model simulations with PyMatching decoders, including biased noise, heterogeneous per-qubit noise, temporal drift, and decoder comparisons.

The repetition code is not a complete arbitrary-state quantum error-correcting code, but it is a useful stabilizer-code testbed for studying syndrome extraction, decoder behavior, biased noise, and circuit-level error models.

## 2. Introduction

The research objective is to build a transparent progression from majority-vote decoding to detector-aware decoding while preserving reproducibility and clear local execution.

## 3. Background

Repetition memory codes protect one basis at a time. They are useful for benchmarking noise-model assumptions and decoder behavior without claiming universal arbitrary-state protection.

## 4. Methods

- Qiskit Aer baseline
- Stim/PyMatching simulation
- Biased noise
- Heterogeneous noise
- Temporal drift
- Decoder comparison
- Planned IBM hardware validation

## 5. Results

- Baseline reproduction
- Stim circuit-level results
- Biased noise results
- Heterogeneous noise results
- Temporal drift results
- Decoder comparison

## 6. Discussion

The layered design isolates contributions from code distance, noise structure, and decoding strategy.

## 7. Limitations

No IBM hardware data is included in this phase. The repetition code remains a basis-protection benchmark rather than full arbitrary-state QEC.

## 8. Conclusion

Layer 1 and Layer 2 provide a complete local pipeline for studying repetition-code memories under increasingly realistic models.

## 9. Planned Layer 3 IBM Hardware Validation

Layer 3 is reserved for a later prompt and execution step once credentials are configured.
