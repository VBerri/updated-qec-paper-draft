from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_cloud.cloud_plots import plot_ibm_hardware_validation
from qec_cloud.ibm_hardware import run_ibm_hardware_validation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deep-memory IBM hardware validation.")
    parser.add_argument("--backend", default=None, help="Optional backend name (for example: ibm_fez).")
    parser.add_argument("--shots", type=int, default=12000, help="Shots per circuit.")
    args = parser.parse_args()

    # Deeper memory stress: larger idle depth and more shots to reveal logical decay.
    circuit_specs = [
        {"label": "z_idle_8", "basis": "Z", "idle_steps": 8},
        {"label": "z_idle_16", "basis": "Z", "idle_steps": 16},
        {"label": "z_idle_32", "basis": "Z", "idle_steps": 32},
        {"label": "x_idle_8", "basis": "X", "idle_steps": 8},
        {"label": "x_idle_16", "basis": "X", "idle_steps": 16},
        {"label": "x_idle_32", "basis": "X", "idle_steps": 32},
    ]

    result = run_ibm_hardware_validation(
        shots=args.shots,
        max_circuits=len(circuit_specs),
        code_size=3,
        backend_name=args.backend,
        circuit_specs=circuit_specs,
        out_csv=ROOT / "results" / "ibm_hardware_validation_deep_memory.csv",
        out_job_json=ROOT / "results" / "ibm_hardware_job_metadata_deep_memory.json",
    )

    plot_ibm_hardware_validation(
        csv_path=ROOT / "results" / "ibm_hardware_validation_deep_memory.csv",
        fig_path=ROOT / "figures" / "ibm_hardware_validation_deep_memory.png",
    )
    print("Deep-memory hardware validation status:", result["status"])
    print("Backend:", result["backend"])
    print("Job ID:", result["job_id"])


if __name__ == "__main__":
    main()
