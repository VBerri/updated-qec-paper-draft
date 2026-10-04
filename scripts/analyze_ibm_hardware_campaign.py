from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd
from scipy.stats import binomtest


def _wilson(successes: int, shots: int, z: float = 1.96) -> tuple[float, float]:
    if shots <= 0:
        return 0.0, 0.0
    phat = successes / shots
    denom = 1.0 + (z**2 / shots)
    center = (phat + (z**2 / (2 * shots))) / denom
    radius = (z / denom) * math.sqrt((phat * (1 - phat) / shots) + (z**2 / (4 * shots * shots)))
    return max(0.0, center - radius), min(1.0, center + radius)


def _find_run_csvs(results_dir: Path, since_ts: str | None) -> list[Path]:
    run_csvs: list[Path] = []
    for p in sorted(results_dir.glob("ibm_hardware_syndrome_validation_results_syndrome_validation_*/ibm_hardware_syndrome_validation_results.csv")):
        if since_ts is not None:
            stem = p.parent.name
            ts = stem.rsplit("_", 1)[-1]
            if ts < since_ts:
                continue
        run_csvs.append(p)
    return run_csvs


def _read_run_list(path: Path) -> list[Path]:
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
    out = []
    for ln in lines:
        if not ln or ln.startswith("#"):
            continue
        p = Path(ln)
        if p.is_dir():
            p = p / "ibm_hardware_syndrome_validation_results.csv"
        out.append(p)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate IBM hardware campaign runs.")
    parser.add_argument("--results-dir", default="results", help="Results directory.")
    parser.add_argument("--out-csv", default="results/ibm_hardware_campaign_aggregate.csv", help="Aggregate CSV output.")
    parser.add_argument(
        "--out-summary-csv",
        default="results/ibm_hardware_campaign_summary.csv",
        help="Summary CSV output.",
    )
    parser.add_argument(
        "--since-ts",
        default=None,
        help="Optional UTC timestamp filter like 20261004T194438Z to ignore older run directories.",
    )
    parser.add_argument(
        "--run-list",
        default=None,
        help="Optional text file with explicit run directories/files to aggregate (one per line).",
    )
    parser.add_argument(
        "--min-shots",
        type=int,
        default=1000,
        help="Exclude runs with fewer shots than this threshold (used to explicitly exclude pilot runs).",
    )
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    if args.run_list:
        run_csvs = _read_run_list(Path(args.run_list))
    else:
        run_csvs = _find_run_csvs(results_dir, since_ts=args.since_ts)
    if not run_csvs:
        raise RuntimeError("No campaign run CSVs found")

    frames = []
    for run_csv in run_csvs:
        df = pd.read_csv(run_csv)
        required = {"kind", "rounds", "logical_bit", "delay_dt", "shots", "history_successes", "majority_successes"}
        if not required.issubset(set(df.columns)):
            continue
        if int(df["shots"].min()) < int(args.min_shots):
            continue
        df["run_dir"] = str(run_csv.parent)
        frames.append(df)

    if not frames:
        raise RuntimeError("No run CSVs with required campaign columns were found")

    all_df = pd.concat(frames, ignore_index=True)
    all_df.to_csv(args.out_csv, index=False)

    encoded = all_df[all_df["kind"] == "encoded"].copy()
    controls = all_df[all_df["kind"] == "unencoded"].copy()

    hist_summary = (
        encoded.groupby(["rounds", "logical_bit", "delay_dt"], as_index=False)
        .agg(
            shots=("shots", "sum"),
            history_successes=("history_successes", "sum"),
            majority_successes=("majority_successes", "sum"),
            paired_history_only=("paired_history_only", "sum"),
            paired_majority_only=("paired_majority_only", "sum"),
        )
    )
    hist_summary["history_error_rate"] = 1.0 - (hist_summary["history_successes"] / hist_summary["shots"])
    hist_summary["majority_error_rate"] = 1.0 - (hist_summary["majority_successes"] / hist_summary["shots"])

    history_error_ci95_low = []
    history_error_ci95_high = []
    majority_error_ci95_low = []
    majority_error_ci95_high = []
    paired_p_exact = []
    for _, row in hist_summary.iterrows():
        h_low, h_high = _wilson(int(row["history_successes"]), int(row["shots"]))
        m_low, m_high = _wilson(int(row["majority_successes"]), int(row["shots"]))
        history_error_ci95_low.append(1.0 - h_high)
        history_error_ci95_high.append(1.0 - h_low)
        majority_error_ci95_low.append(1.0 - m_high)
        majority_error_ci95_high.append(1.0 - m_low)

        b = int(row["paired_history_only"])
        c = int(row["paired_majority_only"])
        n = b + c
        if n == 0:
            paired_p_exact.append(1.0)
        else:
            paired_p_exact.append(float(binomtest(min(b, c), n=n, p=0.5, alternative="two-sided").pvalue))

    hist_summary["history_error_ci95_low"] = history_error_ci95_low
    hist_summary["history_error_ci95_high"] = history_error_ci95_high
    hist_summary["majority_error_ci95_low"] = majority_error_ci95_low
    hist_summary["majority_error_ci95_high"] = majority_error_ci95_high
    hist_summary["paired_exact_p_two_sided"] = [min(1.0, p) for p in paired_p_exact]

    ctrl_summary = (
        controls.groupby(["rounds", "logical_bit", "delay_dt", "control_data_index"], as_index=False)
        .agg(shots=("shots", "sum"), successes=("history_successes", "sum"))
    )
    ctrl_summary["control_error_rate"] = 1.0 - (ctrl_summary["successes"] / ctrl_summary["shots"])

    out = hist_summary.merge(
        ctrl_summary.groupby(["rounds", "logical_bit", "delay_dt"], as_index=False).agg(
            mean_control_error_rate=("control_error_rate", "mean"),
            max_control_error_rate=("control_error_rate", "max"),
            min_control_error_rate=("control_error_rate", "min"),
        ),
        on=["rounds", "logical_bit", "delay_dt"],
        how="left",
    )

    out.to_csv(args.out_summary_csv, index=False)
    print("Aggregate:", args.out_csv)
    print("Summary:", args.out_summary_csv)


if __name__ == "__main__":
    main()
