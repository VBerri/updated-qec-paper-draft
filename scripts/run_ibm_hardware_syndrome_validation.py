from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_cloud.ibm_hardware import run_ibm_hardware_syndrome_validation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run corrected IBM hardware syndrome validation.")
    parser.add_argument("--backend", default=None, help="Optional backend name (for example: ibm_fez).")
    parser.add_argument("--shots", type=int, default=1000, help="Shots per circuit.")
    parser.add_argument("--delay-dt", type=int, default=256, help="Delay duration (dt) inserted each round.")
    args = parser.parse_args()

    result = run_ibm_hardware_syndrome_validation(
        shots=args.shots,
        backend_name=args.backend,
        delay_dt=args.delay_dt,
        out_csv=ROOT / "results" / "ibm_hardware_syndrome_validation_results.csv",
        out_job_json=ROOT / "results" / "ibm_hardware_syndrome_validation_job_metadata.json",
        out_transpile_json=ROOT / "results" / "ibm_hardware_syndrome_transpile_summary.json",
    )

    print("Corrected hardware syndrome validation status:", result["status"])
    print("Backend:", result["backend"])
    print("Job ID:", result["job_id"])


if __name__ == "__main__":
    main()
