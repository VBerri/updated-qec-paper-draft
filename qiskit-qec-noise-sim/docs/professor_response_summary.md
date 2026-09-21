# Professor Response Summary

## Professor suggestion 1
Try biased error or more complicated error modeling beyond uniform Pauli errors using Stim.

## Response
We added Stim circuit-level simulations, biased Pauli noise, measurement noise, heterogeneous noise, and temporal drift.

## Professor suggestion 2
Try something more interesting on the decoder side.

## Response
We compared majority vote with MWPM/PyMatching as the serious decoder baseline, and kept the toy FiLM-style neural path as optional exploratory work. We also clarified the methodology: the MWPM decoder already uses Stim's detector error model, so it is already the weighted decoder for this benchmark. The main scientific result is therefore a clean majority-vote versus MWPM comparison, with MWPM consistently strongest.

## IBM validation
Executed in Layer 3 using a constrained protocol (`n=3`, 3 circuits, 1000 shots/job) on IBM backend `ibm_fez`.

Completed hardware job IDs:
- `danhfqn8gn2s739mlcp0`
- `danhhqg2fm4c73f47lfg`
- `danhhhlr85ps73fe2ffg`

Observed Layer 3 stability was strong over these runs (maximum per-circuit success variation `0.001`), supporting repeatability at the current shot budget.
