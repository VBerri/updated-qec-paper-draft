# Layer 3 Next Steps

Completed hardware campaign:
- Backend: `ibm_fez`
- Primary manifest: [docs/run_manifests/hardware_campaign_2026-10-04.md](docs/run_manifests/hardware_campaign_2026-10-04.md)
- Campaign run-list: [results/ibm_hardware_main_campaign_run_list.txt](results/ibm_hardware_main_campaign_run_list.txt)

Recommended next steps:
1. Keep Layer 1 and Layer 2 local refreshes reproducible before any new hardware submission.
2. Re-run hardware only with explicit objective updates and a new run manifest.
3. Preserve raw run directories and update aggregate summaries without rewriting historical artifacts.
4. If running additional validation jobs, keep n = 3 only, at most 3 circuits, 1000 shots, one job unless a new protocol is approved.

Windows PowerShell setup:

```powershell
$env:IBM_QUANTUM_TOKEN="your_api_key_here"
$env:IBM_QUANTUM_INSTANCE="your_instance_crn_here"
```
