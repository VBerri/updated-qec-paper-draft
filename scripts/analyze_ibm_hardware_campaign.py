from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


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
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    run_csvs = _find_run_csvs(results_dir, since_ts=args.since_ts)
    if not run_csvs:
        raise RuntimeError("No campaign run CSVs found")

    frames = []
    for run_csv in run_csvs:
        df = pd.read_csv(run_csv)
        required = {"kind", "rounds", "logical_bit", "delay_dt", "shots", "history_successes", "majority_successes"}
        if not required.issubset(set(df.columns)):
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
