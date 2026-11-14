from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_cloud.ibm_hardware import run_ibm_hardware_validation


def main() -> None:
    parser = argparse.ArgumentParser(description="Layer 3 IBM hardware validation placeholder.")
    parser.add_argument("--backend", default=None, help="Optional backend name for future Layer 3 runs.")
    parser.add_argument("--shots", type=int, default=1000, help="Shots per circuit for future Layer 3 runs.")
    args = parser.parse_args()

    token = os.getenv("IBM_QUANTUM_TOKEN")
    if not token:
        raise SystemExit(
            "IBM_QUANTUM_TOKEN is not set. Layer 3 validation is deferred. "
            "Set credentials later and rerun this script when Layer 3 is enabled."
        )

    result = run_ibm_hardware_validation(
        shots=args.shots,
        max_circuits=3,
        code_size=3,
        backend_name=args.backend,
        out_csv=ROOT / "results" / "ibm_hardware_validation_results.csv",
        out_job_json=ROOT / "results" / "ibm_hardware_job_metadata.json",
    )

    print("Layer 3 hardware validation status:", result["status"])
    print(result["message"])


if __name__ == "__main__":
    main()
