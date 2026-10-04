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
    parser.add_argument("--shots", type=int, default=256, help="Shots per circuit.")
    parser.add_argument("--delay-dt", type=int, default=0, help="Additional delay duration (dt) inserted each round.")
    parser.add_argument(
        "--physical-path",
        default="0,1,2,3,4",
        help="Five physical qubit IDs in logical order data0,anc0,data1,anc1,data2 (for example: 12,15,18,21,24).",
    )
    parser.add_argument("--seed-transpiler", type=int, default=7, help="Fixed transpiler seed for reproducibility.")
    parser.add_argument(
        "--shuffle-circuit-order",
        action="store_true",
        help="Shuffle circuit execution order for time-interleaving across conditions.",
    )
    parser.add_argument("--shuffle-seed", type=int, default=31415, help="Deterministic seed for circuit order shuffle.")
    args = parser.parse_args()
    physical_path = [int(x.strip()) for x in args.physical_path.split(",") if x.strip()]

    result = run_ibm_hardware_syndrome_validation(
        shots=args.shots,
        backend_name=args.backend,
        delay_dt=args.delay_dt,
        physical_path=physical_path,
        seed_transpiler=args.seed_transpiler,
        shuffle_circuit_order=args.shuffle_circuit_order,
        shuffle_seed=args.shuffle_seed,
        out_csv=ROOT / "results" / "ibm_hardware_syndrome_validation_results.csv",
        out_job_json=ROOT / "results" / "ibm_hardware_syndrome_validation_job_metadata.json",
        out_transpile_json=ROOT / "results" / "ibm_hardware_syndrome_transpile_summary.json",
    )

    print("Corrected hardware syndrome validation status:", result["status"])
    print("Backend:", result["backend"])
    print("Job ID:", result["job_id"])


if __name__ == "__main__":
    main()
