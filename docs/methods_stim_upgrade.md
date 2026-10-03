# Methods: Layer 2 Stim + PyMatching Upgrade

This document describes the Layer 2 local simulations:
- Stim generated repetition memory circuits
- Detector error model extraction
- MWPM decoding via PyMatching
- Bias sweeps, heterogeneous qubit noise, temporal drift scenarios
- Decoder comparison with a strong MWPM baseline, simple majority vote, and an optional toy neural baseline

The repetition code is not a complete arbitrary-state quantum error-correcting code, but it is a useful stabilizer-code testbed for studying syndrome extraction, decoder behavior, biased noise, and circuit-level error models.

Decoder-comparison note:
- `mwpm` is the serious reference decoder in this layer.
- `mwpm` already consumes Stim's detector error model through PyMatching, so it is the naturally weighted decoder for this benchmark.
- `detector_count_heuristic` is retained as a deliberately weak control baseline (it votes over detector events, not final data-bit majority).
- The optional toy FiLM decoder is exploratory and should not be interpreted as a competitive learned decoder benchmark.
