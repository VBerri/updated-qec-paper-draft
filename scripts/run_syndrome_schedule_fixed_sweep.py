from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from importlib.metadata import version as pkg_version

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_stim.syndrome_schedule import (  # noqa: E402
    FixedDurationSpec,
    NoiseModel,
    build_fixed_duration_memory_circuit,
    evaluate_fixed_duration_decoders,
)


def _safe_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def _wilson_interval(failures: int, shots: int, z: float = 1.96) -> tuple[float, float]:
    if shots <= 0:
        return 0.0, 1.0
    p = failures / shots
    denom = 1.0 + z * z / shots
    center = (p + z * z / (2 * shots)) / denom
    radius = z * np.sqrt((p * (1 - p) / shots) + (z * z / (4 * shots * shots))) / denom
    return float(max(0.0, center - radius)), float(min(1.0, center + radius))


def _normal_diff_ci(p_a: float, n_a: int, p_b: float, n_b: int, z: float = 1.96) -> tuple[float, float]:
    if n_a <= 0 or n_b <= 0:
        return -1.0, 1.0
    se = np.sqrt((p_a * (1 - p_a) / n_a) + (p_b * (1 - p_b) / n_b))
    return float((p_a - p_b) - z * se), float((p_a - p_b) + z * se)


def _sampler_seed(seed_group: int, regime_idx: int, distance: int, rounds: int, logical_bit: int) -> int:
    return int(seed_group * 1_000_000 + regime_idx * 100_000 + distance * 1_000 + rounds * 10 + logical_bit)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fixed-schedule syndrome sweep (no adaptive selection).")
    parser.add_argument("--shots", type=int, default=20000)
    parser.add_argument("--target-duration", type=int, default=24)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    if args.output_dir is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = ROOT / "results" / "syndrome_schedule_fixed_sweep" / ts
    else:
        out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    distances = [3, 5]
    rounds_set = [0, 1, 3, 5]
    logical_inputs = [0, 1]
    seed_groups = [101, 202, 303]

    regimes = [
        {
            "regime": "reference",
            "p_idle_tick": 0.001,
            "p_cx": 0.004,
        },
        {
            "regime": "higher_idle_noise",
            "p_idle_tick": 0.005,
            "p_cx": 0.004,
        },
        {
            "regime": "higher_cx_noise",
            "p_idle_tick": 0.001,
            "p_cx": 0.020,
        },
    ]

    shared_rates = {
        "p_data_round": 0.0,
        "p_meas_ancilla": 0.003,
        "p_reset_ancilla": 0.002,
        "p_final_data_meas": 0.002,
    }

    config = {
        "description": "Fixed-schedule simulation sweep (no adaptive selection).",
        "shots_per_configuration": args.shots,
        "target_duration_ticks": args.target_duration,
        "distances": distances,
        "rounds_set": rounds_set,
        "logical_inputs": logical_inputs,
        "seed_groups": seed_groups,
        "regimes": regimes,
        "fixed_rates": shared_rates,
        "notes": [
            "Simulation settings only; not estimates of IBM hardware noise.",
            "Rates are frozen and held fixed across round counts within each regime.",
            "R=0 uses majority only; R>0 also reports oracle-informed MWPM.",
        ],
    }

    (out_dir / "config_frozen.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _safe_git_commit(),
        "python_version": sys.version,
        "dependencies": {
            "numpy": pkg_version("numpy"),
            "pandas": pkg_version("pandas"),
            "stim": pkg_version("stim"),
            "pymatching": pkg_version("pymatching"),
        },
    }
    (out_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    circuits_dir = out_dir / "circuits"
    dem_dir = out_dir / "dem"
    circuits_dir.mkdir(parents=True, exist_ok=True)
    dem_dir.mkdir(parents=True, exist_ok=True)

    timing_rows: list[dict[str, object]] = []
    seed_rows: list[dict[str, object]] = []
    metric_rows: list[pd.DataFrame] = []
    pairwise_rows: list[pd.DataFrame] = []
    counts_rows: list[pd.DataFrame] = []

    for regime_idx, regime in enumerate(regimes):
        noise = NoiseModel(
            p_data_round=shared_rates["p_data_round"],
            p_idle_tick=regime["p_idle_tick"],
            p_cx=regime["p_cx"],
            p_meas_ancilla=shared_rates["p_meas_ancilla"],
            p_reset_ancilla=shared_rates["p_reset_ancilla"],
            p_final_data_meas=shared_rates["p_final_data_meas"],
        )

        for d in distances:
            for r in rounds_set:
                for lb in logical_inputs:
                    spec = FixedDurationSpec(distance=d, rounds=r, logical_bit=lb, target_duration_ticks=args.target_duration)
                    circuit, audit = build_fixed_duration_memory_circuit(spec=spec, noise=noise)

                    per_total = json.loads(str(audit["per_qubit_total_ticks_json"]))
                    if not all(int(v) == args.target_duration for v in per_total.values()):
                        raise RuntimeError(f"Timing budget mismatch for regime={regime['regime']} d={d} r={r} l={lb}")

                    c_name = f"{regime['regime']}_d{d}_r{r}_l{lb}.stim"
                    (circuits_dir / c_name).write_text(str(circuit), encoding="utf-8")
                    if circuit.num_detectors > 0:
                        dem = circuit.detector_error_model(decompose_errors=True)
                        (dem_dir / f"{regime['regime']}_d{d}_r{r}_l{lb}.dem").write_text(str(dem), encoding="utf-8")
                    else:
                        (dem_dir / f"{regime['regime']}_d{d}_r{r}_l{lb}.dem").write_text("# no detectors for R=0\n", encoding="utf-8")

                    timing_rows.append({
                        "regime": regime["regime"],
                        **audit,
                    })

                    for seed_group in seed_groups:
                        sampler_seed = _sampler_seed(seed_group, regime_idx, d, r, lb)
                        seed_rows.append(
                            {
                                "regime": regime["regime"],
                                "distance": d,
                                "rounds": r,
                                "logical_bit": lb,
                                "seed_group": seed_group,
                                "sampler_seed": sampler_seed,
                            }
                        )

                        methods_df, pair_df, counts_df = evaluate_fixed_duration_decoders(
                            circuit=circuit,
                            logical_bit=lb,
                            shots=args.shots,
                            seed=sampler_seed,
                        )
                        methods_df.insert(0, "sampler_seed", sampler_seed)
                        methods_df.insert(0, "seed_group", seed_group)
                        methods_df.insert(0, "logical_bit", lb)
                        methods_df.insert(0, "rounds", r)
                        methods_df.insert(0, "distance", d)
                        methods_df.insert(0, "regime", regime["regime"])
                        metric_rows.append(methods_df)

                        if not pair_df.empty:
                            pair_df.insert(0, "sampler_seed", sampler_seed)
                            pair_df.insert(0, "seed_group", seed_group)
                            pair_df.insert(0, "logical_bit", lb)
                            pair_df.insert(0, "rounds", r)
                            pair_df.insert(0, "distance", d)
                            pair_df.insert(0, "regime", regime["regime"])
                            pairwise_rows.append(pair_df)

                        counts_df.insert(0, "sampler_seed", sampler_seed)
                        counts_df.insert(0, "seed_group", seed_group)
                        counts_df.insert(0, "logical_bit", lb)
                        counts_df.insert(0, "rounds", r)
                        counts_df.insert(0, "distance", d)
                        counts_df.insert(0, "regime", regime["regime"])
                        counts_rows.append(counts_df)

    timing_df = pd.DataFrame(timing_rows)
    seeds_df = pd.DataFrame(seed_rows)
    metrics_df = pd.concat(metric_rows, ignore_index=True)
    pair_df = pd.concat(pairwise_rows, ignore_index=True) if pairwise_rows else pd.DataFrame()
    counts_df = pd.concat(counts_rows, ignore_index=True)

    timing_df.to_csv(out_dir / "timing_audit.csv", index=False)
    seeds_df.to_csv(out_dir / "seed_manifest.csv", index=False)
    metrics_df.to_csv(out_dir / "decoder_metrics.csv", index=False)
    counts_df.to_csv(out_dir / "counts.csv", index=False)
    if not pair_df.empty:
        pair_df.to_csv(out_dir / "paired_decoder_counts.csv", index=False)

    schedule_costs = (
        timing_df.groupby(["regime", "distance", "rounds"], as_index=False)
        .agg(
            two_qubit_gate_count=("two_qubit_gate_count", "first"),
            ancilla_measure_count=("ancilla_measure_count", "first"),
            ancilla_reset_count=("ancilla_reset_count", "first"),
            final_data_measure_count=("final_data_measure_count", "first"),
            target_duration_ticks=("target_duration_ticks", "first"),
        )
    )
    schedule_costs.to_csv(out_dir / "schedule_costs.csv", index=False)

    expected_cfg = len(regimes) * len(distances) * len(rounds_set) * len(logical_inputs)
    actual_cfg = len(timing_df)
    if actual_cfg != expected_cfg:
        raise RuntimeError(f"Config coverage mismatch: expected {expected_cfg}, got {actual_cfg}")

    expected_seed_cfg = expected_cfg * len(seed_groups)
    if len(seeds_df) != expected_seed_cfg:
        raise RuntimeError(f"Seed manifest mismatch: expected {expected_seed_cfg}, got {len(seeds_df)}")

    maj = metrics_df[metrics_df["method"] == "final_data_majority"].copy()
    oracle = metrics_df[metrics_df["method"] == "mwpm_oracle_informed"].copy()

    # Majority-only schedule comparison (fixed decoder across all R).
    maj_agg_rows = []
    for (regime, distance, logical_bit, rounds), sub in maj.groupby(["regime", "distance", "logical_bit", "rounds"]):
        failures = int(sub["failures"].sum())
        shots = int(sub["shots"].sum())
        p = failures / shots
        lo, hi = _wilson_interval(failures, shots)
        maj_agg_rows.append(
            {
                "regime": regime,
                "distance": distance,
                "logical_bit": logical_bit,
                "rounds": rounds,
                "failures": failures,
                "shots": shots,
                "logical_error_rate": p,
                "ci95_low": lo,
                "ci95_high": hi,
            }
        )
    maj_agg = pd.DataFrame(maj_agg_rows)
    maj_agg.to_csv(out_dir / "majority_by_round_aggregate.csv", index=False)

    # Per-seed majority estimates.
    maj_seed_rows = []
    for (regime, distance, logical_bit, rounds, seed_group), sub in maj.groupby(["regime", "distance", "logical_bit", "rounds", "seed_group"]):
        failures = int(sub["failures"].sum())
        shots = int(sub["shots"].sum())
        lo, hi = _wilson_interval(failures, shots)
        maj_seed_rows.append(
            {
                "regime": regime,
                "distance": distance,
                "logical_bit": logical_bit,
                "rounds": rounds,
                "seed_group": seed_group,
                "failures": failures,
                "shots": shots,
                "logical_error_rate": failures / shots,
                "ci95_low": lo,
                "ci95_high": hi,
            }
        )
    pd.DataFrame(maj_seed_rows).to_csv(out_dir / "majority_by_round_per_seed.csv", index=False)

    # Equally weighted logical average for majority.
    avg_rows = []
    for (regime, distance, rounds), sub in maj_agg.groupby(["regime", "distance", "rounds"]):
        p0 = float(sub[sub["logical_bit"] == 0]["logical_error_rate"].iloc[0])
        p1 = float(sub[sub["logical_bit"] == 1]["logical_error_rate"].iloc[0])
        n0 = int(sub[sub["logical_bit"] == 0]["shots"].iloc[0])
        n1 = int(sub[sub["logical_bit"] == 1]["shots"].iloc[0])
        p_avg = 0.5 * (p0 + p1)
        var = 0.25 * ((p0 * (1 - p0) / n0) + (p1 * (1 - p1) / n1))
        se = np.sqrt(var)
        avg_rows.append(
            {
                "regime": regime,
                "distance": distance,
                "rounds": rounds,
                "logical_error_rate_equal_weight": p_avg,
                "ci95_low": float(max(0.0, p_avg - 1.96 * se)),
                "ci95_high": float(min(1.0, p_avg + 1.96 * se)),
                "p_logical0": p0,
                "p_logical1": p1,
                "shots_per_logical": min(n0, n1),
            }
        )
    avg_df = pd.DataFrame(avg_rows)
    avg_df.to_csv(out_dir / "majority_by_round_equal_weighted.csv", index=False)

    # Gap to runner-up for majority schedule comparison.
    gap_rows = []
    for (regime, distance, logical_bit), sub in maj_agg.groupby(["regime", "distance", "logical_bit"]):
        ranked = sub.sort_values("logical_error_rate")
        leader = ranked.iloc[0]
        runner = ranked.iloc[1]
        diff_lo, diff_hi = _normal_diff_ci(
            float(runner["logical_error_rate"]),
            int(runner["shots"]),
            float(leader["logical_error_rate"]),
            int(leader["shots"]),
        )
        gap_rows.append(
            {
                "regime": regime,
                "distance": distance,
                "logical_bit": logical_bit,
                "leader_round": int(leader["rounds"]),
                "leader_rate": float(leader["logical_error_rate"]),
                "runner_up_round": int(runner["rounds"]),
                "runner_up_rate": float(runner["logical_error_rate"]),
                "gap_to_runner_up": float(runner["logical_error_rate"] - leader["logical_error_rate"]),
                "runner_minus_leader_ci95_low": diff_lo,
                "runner_minus_leader_ci95_high": diff_hi,
                "distinguishable_at_95": int(diff_lo > 0.0),
            }
        )
    pd.DataFrame(gap_rows).to_csv(out_dir / "majority_leader_gaps.csv", index=False)

    avg_gap_rows = []
    for (regime, distance), sub in avg_df.groupby(["regime", "distance"]):
        ranked = sub.sort_values("logical_error_rate_equal_weight")
        leader = ranked.iloc[0]
        runner = ranked.iloc[1]
        n = int(leader["shots_per_logical"])
        p_l0 = float(leader["p_logical0"])
        p_l1 = float(leader["p_logical1"])
        q_l0 = float(runner["p_logical0"])
        q_l1 = float(runner["p_logical1"])
        var_leader = 0.25 * ((p_l0 * (1 - p_l0) / n) + (p_l1 * (1 - p_l1) / n))
        var_runner = 0.25 * ((q_l0 * (1 - q_l0) / n) + (q_l1 * (1 - q_l1) / n))
        se = np.sqrt(var_leader + var_runner)
        diff = float(runner["logical_error_rate_equal_weight"] - leader["logical_error_rate_equal_weight"])
        diff_lo = diff - 1.96 * se
        diff_hi = diff + 1.96 * se
        avg_gap_rows.append(
            {
                "regime": regime,
                "distance": distance,
                "leader_round": int(leader["rounds"]),
                "leader_rate_equal_weight": float(leader["logical_error_rate_equal_weight"]),
                "runner_up_round": int(runner["rounds"]),
                "runner_up_rate_equal_weight": float(runner["logical_error_rate_equal_weight"]),
                "gap_to_runner_up": diff,
                "runner_minus_leader_ci95_low": float(diff_lo),
                "runner_minus_leader_ci95_high": float(diff_hi),
                "distinguishable_at_95": int(diff_lo > 0.0),
            }
        )
    pd.DataFrame(avg_gap_rows).to_csv(out_dir / "majority_equal_weight_leader_gaps.csv", index=False)

    # Strategy comparison: R=0 majority vs R>0 oracle-informed MWPM.
    strategy_rows = []
    for regime in [r["regime"] for r in regimes]:
        for distance in distances:
            for logical_bit in logical_inputs:
                base = maj_agg[
                    (maj_agg["regime"] == regime)
                    & (maj_agg["distance"] == distance)
                    & (maj_agg["logical_bit"] == logical_bit)
                    & (maj_agg["rounds"] == 0)
                ].iloc[0]
                p0 = float(base["logical_error_rate"])
                n0 = int(base["shots"])
                for rounds in [1, 3, 5]:
                    sub = oracle[
                        (oracle["regime"] == regime)
                        & (oracle["distance"] == distance)
                        & (oracle["logical_bit"] == logical_bit)
                        & (oracle["rounds"] == rounds)
                    ]
                    failures = int(sub["failures"].sum())
                    shots = int(sub["shots"].sum())
                    p = failures / shots
                    lo, hi = _normal_diff_ci(p, shots, p0, n0)
                    strategy_rows.append(
                        {
                            "regime": regime,
                            "distance": distance,
                            "logical_bit": logical_bit,
                            "baseline": "R0_majority",
                            "candidate": f"R{rounds}_oracle_mwpm",
                            "baseline_rate": p0,
                            "candidate_rate": p,
                            "candidate_minus_baseline": p - p0,
                            "ci95_low": lo,
                            "ci95_high": hi,
                            "baseline_shots": n0,
                            "candidate_shots": shots,
                        }
                    )
    pd.DataFrame(strategy_rows).to_csv(out_dir / "strategy_comparison_r0_majority_vs_oracle.csv", index=False)

    # Per-seed strategy estimates.
    strat_seed_rows = []
    maj_seed_df = pd.DataFrame(maj_seed_rows)
    oracle_seed_rows = []
    for (regime, distance, logical_bit, rounds, seed_group), sub in oracle.groupby(["regime", "distance", "logical_bit", "rounds", "seed_group"]):
        failures = int(sub["failures"].sum())
        shots = int(sub["shots"].sum())
        lo, hi = _wilson_interval(failures, shots)
        oracle_seed_rows.append(
            {
                "regime": regime,
                "distance": distance,
                "logical_bit": logical_bit,
                "rounds": rounds,
                "seed_group": seed_group,
                "failures": failures,
                "shots": shots,
                "logical_error_rate": failures / shots,
                "ci95_low": lo,
                "ci95_high": hi,
            }
        )
    oracle_seed_df = pd.DataFrame(oracle_seed_rows)
    maj_seed_df.to_csv(out_dir / "majority_by_round_per_seed.csv", index=False)
    oracle_seed_df.to_csv(out_dir / "oracle_by_round_per_seed.csv", index=False)

    for regime in [r["regime"] for r in regimes]:
        for distance in distances:
            for logical_bit in logical_inputs:
                for seed_group in seed_groups:
                    base = maj_seed_df[
                        (maj_seed_df["regime"] == regime)
                        & (maj_seed_df["distance"] == distance)
                        & (maj_seed_df["logical_bit"] == logical_bit)
                        & (maj_seed_df["rounds"] == 0)
                        & (maj_seed_df["seed_group"] == seed_group)
                    ].iloc[0]
                    for rounds in [1, 3, 5]:
                        cand = oracle_seed_df[
                            (oracle_seed_df["regime"] == regime)
                            & (oracle_seed_df["distance"] == distance)
                            & (oracle_seed_df["logical_bit"] == logical_bit)
                            & (oracle_seed_df["rounds"] == rounds)
                            & (oracle_seed_df["seed_group"] == seed_group)
                        ].iloc[0]
                        strat_seed_rows.append(
                            {
                                "regime": regime,
                                "distance": distance,
                                "logical_bit": logical_bit,
                                "seed_group": seed_group,
                                "baseline": "R0_majority",
                                "candidate": f"R{rounds}_oracle_mwpm",
                                "baseline_rate": float(base["logical_error_rate"]),
                                "candidate_rate": float(cand["logical_error_rate"]),
                                "candidate_minus_baseline": float(cand["logical_error_rate"] - base["logical_error_rate"]),
                            }
                        )
    pd.DataFrame(strat_seed_rows).to_csv(out_dir / "strategy_comparison_per_seed.csv", index=False)

    # Paired decoder summary: only same-shot decoder pairs.
    if not pair_df.empty:
        paired_summary_rows = []
        for keys, sub in pair_df.groupby(["regime", "distance", "rounds", "logical_bit"]):
            left = int(sub["left_only_failures"].sum())
            right = int(sub["right_only_failures"].sum())
            both_f = int(sub["both_failures"].sum())
            both_s = int(sub["both_success"].sum())
            n = left + right + both_f + both_s
            paired_summary_rows.append(
                {
                    "regime": keys[0],
                    "distance": keys[1],
                    "rounds": keys[2],
                    "logical_bit": keys[3],
                    "left_method": "final_data_majority",
                    "right_method": "mwpm_oracle_informed",
                    "left_only_failures": left,
                    "right_only_failures": right,
                    "both_failures": both_f,
                    "both_success": both_s,
                    "shots": n,
                    "paired_error_gap_left_minus_right": (left - right) / n if n > 0 else 0.0,
                }
            )
        pd.DataFrame(paired_summary_rows).to_csv(out_dir / "paired_decoder_summary.csv", index=False)

    print(f"Fixed sweep outputs written to: {out_dir}")


if __name__ == "__main__":
    main()
