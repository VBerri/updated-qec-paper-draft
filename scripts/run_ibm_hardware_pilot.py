from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_cloud.ibm_hardware import run_ibm_hardware_syndrome_validation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run IBM hardware pilot matrix (16 circuits, 256 shots each).")
    parser.add_argument("--backend", default=None, help="Backend name, for example ibm_fez.")
    parser.add_argument("--shots", type=int, default=256, help="Shots per circuit for pilot.")
    parser.add_argument("--delay-dt", type=int, default=0, help="Additional delay per round in dt.")
    parser.add_argument(
        "--physical-path",
        default="0,1,2,3,4",
        help="Logical order path data0,anc0,data1,anc1,data2.",
    )
    parser.add_argument("--seed-transpiler", type=int, default=7, help="Fixed transpiler seed.")
    args = parser.parse_args()

    physical_path = [int(x.strip()) for x in args.physical_path.split(",") if x.strip()]

    result = run_ibm_hardware_syndrome_validation(
        shots=args.shots,
        backend_name=args.backend,
        delay_dt=args.delay_dt,
        physical_path=physical_path,
        seed_transpiler=args.seed_transpiler,
        out_csv=ROOT / "results" / "ibm_hardware_syndrome_validation_results.csv",
        out_job_json=ROOT / "results" / "ibm_hardware_syndrome_validation_job_metadata.json",
        out_transpile_json=ROOT / "results" / "ibm_hardware_syndrome_transpile_summary.json",
    )

    print("Pilot status:", result["status"])
    print("Backend:", result["backend"])
    print("Job ID:", result["job_id"])
    print("Run dir:", result["run_dir"])


if __name__ == "__main__":
    main()
