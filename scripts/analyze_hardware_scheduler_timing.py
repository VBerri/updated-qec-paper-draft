from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

QUBIT_RE = re.compile(r"Qubit (\d+)")


def _parse_timing(timing_str: str) -> dict[int, list[tuple[str, int, int, str]]]:
    events: dict[int, list[tuple[str, int, int, str]]] = {}
    for line in timing_str.split("\n"):
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 6:
            continue
        op, qlabel, start, dur, ptype = parts[1], parts[2], parts[3], parts[4], parts[5]
        m = QUBIT_RE.match(qlabel)
        if not m:
            continue
        try:
            start_i = int(start)
            dur_i = int(dur)
        except ValueError:
            continue
        events.setdefault(int(m.group(1)), []).append((op, start_i, dur_i, ptype))
    return events


def _init_end(evs: list[tuple[str, int, int, str]]) -> int:
    ends = [s + d for (op, s, d, _pt) in evs if op.startswith("INIT_")]
    return max(ends) if ends else 0


def _device_interval(events: dict, qubit: int, logical_bit: int) -> int | None:
    evs = events.get(qubit, [])
    meas = [s for (op, s, _d, pt) in evs if op.startswith("measure_") and pt == "play"]
    if not meas:
        return None
    meas_start = min(meas)
    if logical_bit == 1:
        x_ends = [s + d for (op, s, d, _pt) in evs if op == f"x_{qubit}"]
        prep_end = min(x_ends) if x_ends else _init_end(evs)
    else:
        prep_end = _init_end(evs)
    return int(meas_start - prep_end)


def _observed_signature(events: dict) -> tuple[set[int], set[int]]:
    measured = {q for q, evs in events.items() if any(op.startswith("measure_") and pt == "play" for (op, _s, _d, pt) in evs)}
    prepared = {q for q, evs in events.items() if any(op == f"x_{q}" for (op, _s, _d, _pt) in evs)}
    return measured, prepared


def _expected_signature(label: str, path: list[int]) -> tuple[set[int], set[int]]:
    data = [path[0], path[2], path[4]]
    log = int(re.search(r"log(\d+)", label).group(1)) if re.search(r"log(\d+)", label) else 0
    if label.startswith("unencoded"):
        dq = int(re.search(r"dq(\d+)", label).group(1)) if re.search(r"dq(\d+)", label) else 0
        q = data[dq]
        return {q}, ({q} if log == 1 else set())
    return set(path), (set(data) if log == 1 else set())


def analyze_run(run_dir: Path) -> dict:
    meta = json.loads((run_dir / "runtime_metadata.json").read_text())
    path = [int(x) for x in meta["physical_path_logical_order"]]
    dt_seconds = meta.get("dt_seconds")
    pubs = meta.get("scheduler_pub_metadata", [])
    data = [path[0], path[2], path[4]]

    encoded_dev: dict[tuple[int, int, int], dict[int, int]] = {}
    control_dev: dict[tuple[int, int, int, int], int] = {}
    signature_mismatches = []
    records = []

    for pub in pubs:
        cm = (pub or {}).get("circuit_metadata") or {}
        cid = cm.get("circuit_id") or ""
        label = cid.split(":", 1)[1] if ":" in cid else cid
        timing = ((pub or {}).get("compilation", {}) or {}).get("scheduler_timing", {}).get("timing", "")
        events = _parse_timing(timing)

        logical_bit = int(re.search(r"log(\d+)", label).group(1)) if re.search(r"log(\d+)", label) else 0
        rounds = int(re.search(r"r(\d+)", label).group(1)) if re.search(r"r(\d+)", label) else 0
        delay = int(re.search(r"delay(\d+)", label).group(1)) if re.search(r"delay(\d+)", label) else 0

        measured, prepared = _observed_signature(events)
        exp_meas, exp_prep = _expected_signature(label, path)
        sig_ok = measured == exp_meas and prepared == exp_prep
        if not sig_ok:
            signature_mismatches.append(
                {
                    "label": label,
                    "observed_measured": sorted(measured),
                    "expected_measured": sorted(exp_meas),
                    "observed_prepared": sorted(prepared),
                    "expected_prepared": sorted(exp_prep),
                }
            )

        if label.startswith("unencoded"):
            dq = int(re.search(r"dq(\d+)", label).group(1))
            q = data[dq]
            iv = _device_interval(events, q, logical_bit)
            if iv is not None and sig_ok:
                control_dev[(rounds, logical_bit, delay, dq)] = iv
        else:
            ivs = {q: _device_interval(events, q, logical_bit) for q in data}
            if sig_ok:
                encoded_dev[(rounds, logical_bit, delay)] = {q: v for q, v in ivs.items() if v is not None}

        records.append({"label": label, "signature_ok": sig_ok})

    deltas = []
    for (rounds, logical_bit, delay, dq), ctrl_iv in control_dev.items():
        enc = encoded_dev.get((rounds, logical_bit, delay))
        if not enc:
            continue
        q = data[dq]
        if q not in enc:
            continue
        deltas.append(
            {
                "rounds": rounds,
                "logical_bit": logical_bit,
                "delay_dt": delay,
                "control_data_index": dq,
                "physical_qubit": q,
                "encoded_interval_dt": enc[q],
                "control_interval_dt": ctrl_iv,
                "delta_dt": enc[q] - ctrl_iv,
            }
        )

    return {
        "run_dir": str(run_dir),
        "dt_seconds": dt_seconds,
        "num_pubs": len(pubs),
        "num_signature_mismatches": len(signature_mismatches),
        "signature_mismatches": signature_mismatches,
        "device_interval_deltas": deltas,
        "note": "device_interval_deltas computed only from signature-consistent returned traces",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze returned hardware scheduler timing traces for memory-interval tolerance and label/signature consistency.")
    parser.add_argument("run_dirs", nargs="+")
    parser.add_argument("--out", default="results/ibm_hardware_scheduler_timing_report.json")
    args = parser.parse_args()

    reports = [analyze_run(Path(d)) for d in args.run_dirs]

    all_deltas = [d["delta_dt"] for r in reports for d in r["device_interval_deltas"]]
    abs_deltas = [abs(x) for x in all_deltas]
    total_mismatch = sum(r["num_signature_mismatches"] for r in reports)
    total_pubs = sum(r["num_pubs"] for r in reports)
    dt_seconds = next((r["dt_seconds"] for r in reports if r["dt_seconds"]), None)

    max_abs = max(abs_deltas) if abs_deltas else 0
    mean_abs = (sum(abs_deltas) / len(abs_deltas)) if abs_deltas else 0.0

    summary = {
        "num_runs": len(reports),
        "num_control_encoded_pairs": len(all_deltas),
        "device_interval_delta_dt_max_abs": max_abs,
        "device_interval_delta_dt_mean_abs": mean_abs,
        "device_interval_delta_ns_max_abs": (max_abs * dt_seconds * 1e9) if dt_seconds else None,
        "device_interval_delta_ns_mean_abs": (mean_abs * dt_seconds * 1e9) if dt_seconds else None,
        "total_pubs": total_pubs,
        "total_signature_mismatches": total_mismatch,
    }

    combined = {"summary": summary, "reports": reports}
    Path(args.out).write_text(json.dumps(combined, indent=2), encoding="utf-8")

    print("Wrote:", args.out)
    print("Control/encoded device-interval pairs:", summary["num_control_encoded_pairs"])
    print("Device interval delta (dt): max_abs =", max_abs, "mean_abs =", round(mean_abs, 3))
    if dt_seconds:
        print("Device interval delta (ns): max_abs =", round(summary["device_interval_delta_ns_max_abs"], 2), "mean_abs =", round(summary["device_interval_delta_ns_mean_abs"], 2))
    print("Signature mismatches:", total_mismatch, "/", total_pubs)


if __name__ == "__main__":
    main()
