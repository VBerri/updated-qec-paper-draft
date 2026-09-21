# Layer 3 Next Steps

Completed:
1. Finished Layer 1 and Layer 2.
2. Added real Layer 3 IBM execution path.
3. Ran one constrained hardware job (`n=3`, 3 circuits, 1000 shots).

Next practical steps:
1. Repeat the same Layer 3 run at least once at a different time window to check stability.
2. Optionally run one additional backend if available to measure backend-to-backend variance.
3. Add a short final comparison paragraph in the paper text using `results/ibm_hardware_validation_results.csv` and `results/ibm_hardware_job_metadata.json`.
4. Rotate IBM API credentials after validation runs if secrets were ever exposed.

Example PowerShell setup:

```powershell
$env:IBM_QUANTUM_TOKEN="your_api_key_here"
$env:IBM_QUANTUM_INSTANCE="your_instance_crn_here"
```
