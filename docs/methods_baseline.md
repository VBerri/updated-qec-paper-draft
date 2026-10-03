# Methods: Layer 1 Qiskit Aer Baseline

This document describes the Layer 1 local baseline:
- Code sizes n = 1, 3, 5
- Physical error sweep over specified p values
- Idle-step noise accumulation over 4 steps
- Majority-vote decoding in protected measurement basis

The repetition code is not a complete arbitrary-state quantum error-correcting code, but it is a useful stabilizer-code testbed for studying syndrome extraction, decoder behavior, biased noise, and circuit-level error models.
