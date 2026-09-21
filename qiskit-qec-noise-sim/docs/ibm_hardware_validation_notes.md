# IBM Hardware Validation Notes (Layer 3)

Layer 3 hardware validation is now executable and has been run once in this workspace.

Run constraints used:
- n = 3 repetition circuits only.
- At most 3 circuits in one job.
- 1000 shots.
- Credentials from environment variables only.

Produced artifacts:
- `results/ibm_hardware_validation_results.csv`
- `results/ibm_hardware_job_metadata.json`
- `figures/ibm_hardware_validation.png`

Operational notes:
- The IBM Runtime API now requires modern channels (`ibm_cloud` or `ibm_quantum_platform`).
- Older `backend.run()` paths may be unavailable; the code now falls back to Runtime Sampler primitives.
- Tokens should be rotated if they were ever pasted into chat or screenshots.
