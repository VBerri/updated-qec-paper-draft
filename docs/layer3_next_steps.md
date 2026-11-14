# Layer 3 Next Steps

1. Finish Layer 1 and Layer 2 first.
2. Then set IBM credentials in PowerShell.
3. Then run scripts/run_ibm_hardware_validation.py.
4. IBM validation should use n = 3 only, at most 3 circuits, 1000 shots, one job.

Windows PowerShell setup:

```powershell
$env:IBM_QUANTUM_TOKEN="your_api_key_here"
$env:IBM_QUANTUM_INSTANCE="your_instance_crn_here"
```
