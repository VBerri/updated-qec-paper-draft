from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_cloud.ibm_hardware import run_ibm_hardware_syndrome_validation


def _diagnostic_specs(rounds: int, delay_dt: int) -> list[dict]:
    specs: list[dict] = []
    for logical_bit in (0, 1):
        prefix = f"diag_logical_{logical_bit}"
        specs.append(
            {
                "label": f"{prefix}_nofault",
                "kind": "encoded",
                "rounds": rounds,
                "logical_bit": logical_bit,
                "delay_dt": delay_dt,
            }
        )

        for data_q in (0, 1, 2):
            specs.append(
                {
                    "label": f"{prefix}_data_fault_q{data_q}",
                    "kind": "encoded",
                    "rounds": rounds,
                    "logical_bit": logical_bit,
                    "delay_dt": delay_dt,
                    "fault_model": {
                        "data_fault_qubit": data_q,
                        "data_fault_stage": rounds,
                    },
                }
            )

        for anc_q in (0, 1):
            specs.append(
                {
                    "label": f"{prefix}_meas_fault_anc{anc_q}",
                    "kind": "encoded",
                    "rounds": rounds,
                    "logical_bit": logical_bit,
                    "delay_dt": delay_dt,
                    "fault_model": {
                        "meas_fault_ancilla": anc_q,
                        "meas_fault_round": rounds - 1,
                    },
                }
            )
    return specs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run hardware fault-diagnostic encoded-only circuits.")
    parser.add_argument("--backend", default=None, help="Optional backend name (for example: ibm_fez).")
    parser.add_argument("--shots", type=int, default=512, help="Shots per circuit.")
    parser.add_argument("--rounds", type=int, default=3, help="Syndrome rounds for diagnostics.")
    parser.add_argument("--delay-dt", type=int, default=0, help="Delay inserted each round.")
    parser.add_argument(
        "--physical-path",
        default="0,1,2,3,4",
        help="Five physical qubit IDs in logical order data0,anc0,data1,anc1,data2 (for example: 12,15,18,21,24).",
    )
    parser.add_argument("--seed-transpiler", type=int, default=7, help="Fixed transpiler seed for reproducibility.")
    args = parser.parse_args()

    physical_path = [int(x.strip()) for x in args.physical_path.split(",") if x.strip()]
    specs = _diagnostic_specs(rounds=args.rounds, delay_dt=args.delay_dt)

    result = run_ibm_hardware_syndrome_validation(
        shots=args.shots,
        backend_name=args.backend,
        delay_dt=args.delay_dt,
        circuit_specs=specs,
        physical_path=physical_path,
        seed_transpiler=args.seed_transpiler,
        out_csv=ROOT / "results" / "ibm_hardware_fault_diagnostic_results.csv",
        out_job_json=ROOT / "results" / "ibm_hardware_fault_diagnostic_job_metadata.json",
        out_transpile_json=ROOT / "results" / "ibm_hardware_fault_diagnostic_transpile_summary.json",
    )

    print("Fault diagnostic status:", result["status"])
    print("Backend:", result["backend"])
    print("Job ID:", result["job_id"])


if __name__ == "__main__":
    main()
