from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_stim.syndrome_schedule import run_syndrome_schedule_model_check, run_syndrome_schedule_smoke


def main() -> None:
    parser = argparse.ArgumentParser(description="Run milestone-1 syndrome-schedule smoke/model-check experiment.")
    parser.add_argument("--mode", choices=["smoke", "model-check"], default="smoke")
    parser.add_argument("--shots", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20261114)
    parser.add_argument("--target-duration", type=int, default=30)
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.mode == "smoke":
        out_dir = ROOT / "results" / "syndrome_schedule_smoke" / ts
        run_syndrome_schedule_smoke(
            output_dir=out_dir,
            target_duration_ticks=args.target_duration,
            shots=args.shots,
            seed=args.seed,
            distances=(3, 5),
            rounds_set=(0, 1, 3, 5),
            logical_inputs=(0, 1),
        )
    else:
        out_dir = ROOT / "results" / "syndrome_schedule_model_check" / ts
        run_syndrome_schedule_model_check(
            output_dir=out_dir,
            target_duration_ticks=args.target_duration,
            shots=args.shots,
            seed=args.seed,
            distances=(3, 5),
            rounds_set=(0, 1, 3, 5),
            logical_inputs=(0, 1),
        )
    print(f"Syndrome-schedule {args.mode} outputs written to: {out_dir}")


if __name__ == "__main__":
    main()
