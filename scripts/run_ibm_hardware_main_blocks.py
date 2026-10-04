from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_cloud.ibm_hardware import run_ibm_hardware_syndrome_validation


def _build_main_specs(delay_dt: int) -> list[dict]:
    specs: list[dict] = []
    for rounds in (1, 3):
        for logical_bit in (0, 1):
            specs.append(
                {
                    "label": f"encoded_r{rounds}_log{logical_bit}_delay{delay_dt}",
                    "kind": "encoded",
                    "rounds": rounds,
                    "logical_bit": logical_bit,
                    "delay_dt": delay_dt,
                }
            )
            for control_data_index in (0, 1, 2):
                specs.append(
                    {
                        "label": f"unencoded_r{rounds}_log{logical_bit}_dq{control_data_index}_delay{delay_dt}",
                        "kind": "unencoded",
                        "rounds": rounds,
                        "logical_bit": logical_bit,
                        "delay_dt": delay_dt,
                        "control_data_index": control_data_index,
                    }
                )
    return specs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run three hardware blocks for frozen main matrix conditions.")
    parser.add_argument("--backend", default=None, help="Backend name, for example ibm_fez.")
    parser.add_argument("--shots", type=int, default=2000, help="Shots per circuit per block.")
    parser.add_argument(
        "--delays-dt",
        default="0,128,384",
        help="Comma-separated per-round added delays in dt for frozen blocks.",
    )
    parser.add_argument("--blocks", type=int, default=3, help="Number of repeated execution blocks.")
    parser.add_argument(
        "--physical-path",
        default="0,1,2,3,4",
        help="Logical order path data0,anc0,data1,anc1,data2.",
    )
    parser.add_argument("--seed-transpiler", type=int, default=7, help="Fixed transpiler seed.")
    args = parser.parse_args()

    delays = [int(x.strip()) for x in args.delays_dt.split(",") if x.strip()]
    physical_path = [int(x.strip()) for x in args.physical_path.split(",") if x.strip()]

    run_dirs: list[str] = []
    for block in range(args.blocks):
        for delay_dt in delays:
            result = run_ibm_hardware_syndrome_validation(
                shots=args.shots,
                backend_name=args.backend,
                delay_dt=delay_dt,
                circuit_specs=_build_main_specs(delay_dt=delay_dt),
                physical_path=physical_path,
                seed_transpiler=args.seed_transpiler,
                out_csv=ROOT / "results" / "ibm_hardware_syndrome_validation_results.csv",
                out_job_json=ROOT / "results" / "ibm_hardware_syndrome_validation_job_metadata.json",
                out_transpile_json=ROOT / "results" / "ibm_hardware_syndrome_transpile_summary.json",
            )
            run_dirs.append(result["run_dir"])
            print(f"block={block} delay_dt={delay_dt} job_id={result['job_id']}")

    print("Completed run directories:")
    for run_dir in run_dirs:
        print(run_dir)


if __name__ == "__main__":
    main()
