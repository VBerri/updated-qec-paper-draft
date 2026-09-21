from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_cloud.ibm_hardware import run_ibm_hardware_validation


def main() -> None:
    result = run_ibm_hardware_validation(
        shots=1000,
        max_circuits=3,
        code_size=3,
        out_csv=ROOT / "results" / "ibm_hardware_validation_results_run2.csv",
        out_job_json=ROOT / "results" / "ibm_hardware_job_metadata_run2.json",
    )
    print(result)


if __name__ == "__main__":
    main()