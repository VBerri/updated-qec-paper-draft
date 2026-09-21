from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_cloud.cloud_plots import plot_ibm_hardware_validation
from qec_cloud.ibm_hardware import run_ibm_hardware_validation


def main() -> None:
    result = run_ibm_hardware_validation(
        shots=1000,
        max_circuits=3,
        code_size=3,
        out_csv=ROOT / "results" / "ibm_hardware_validation_results.csv",
        out_job_json=ROOT / "results" / "ibm_hardware_job_metadata.json",
    )
    plot_ibm_hardware_validation(
        csv_path=ROOT / "results" / "ibm_hardware_validation_results.csv",
        fig_path=ROOT / "figures" / "ibm_hardware_validation.png",
    )
    print("Layer 3 hardware validation status:", result["status"])
    print("Backend:", result["backend"])
    print("Job ID:", result["job_id"])


if __name__ == "__main__":
    main()
