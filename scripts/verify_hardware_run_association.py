from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from qiskit import qpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

TRANSPILED_RE = re.compile(r"^(\d+)_(.+)_transpiled\.qpy$")


def _measured_physical_qubits(circuit) -> list[int]:
    qubits: set[int] = set()
    for inst in circuit.data:
        if inst.operation.name == "measure":
            for q in inst.qubits:
                qubits.add(int(circuit.find_bit(q).index))
    return sorted(qubits)


def _prep_x_physical_qubits(circuit) -> list[int]:
    qubits: set[int] = set()
    for inst in circuit.data:
        if inst.operation.name == "x":
            for q in inst.qubits:
                qubits.add(int(circuit.find_bit(q).index))
    return sorted(qubits)


def _is_control_label(label: str) -> bool:
    return label.startswith("unencoded")


def _expected_measured_from_label(label: str, physical_path: list[int]) -> list[int]:
    if not _is_control_label(label):
        return sorted(set(physical_path))
    dq_match = re.search(r"dq(\d+)", label)
    dq = int(dq_match.group(1)) if dq_match else 0
    data_positions = [physical_path[0], physical_path[2], physical_path[4]]
    return [int(data_positions[dq])]


def _expected_logical_bit(label: str) -> int:
    log_match = re.search(r"log(\d+)", label)
    return int(log_match.group(1)) if log_match else 0


def verify_run(run_dir: Path) -> dict:
    meta_path = run_dir / "runtime_metadata.json"
    physical_path = [0, 1, 2, 3, 4]
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        physical_path = [int(x) for x in meta.get("physical_path_logical_order", physical_path)]

    circuits_dir = run_dir / "circuits"
    raw_counts = {}
    raw_counts_path = run_dir / "raw_counts.json"
    if raw_counts_path.exists():
        raw_counts = json.loads(raw_counts_path.read_text(encoding="utf-8"))

    records = []
    ok = True
    for qpy_file in sorted(circuits_dir.glob("*_transpiled.qpy")):
        m = TRANSPILED_RE.match(qpy_file.name)
        if not m:
            continue
        index = int(m.group(1))
        label = m.group(2)
        with open(qpy_file, "rb") as fh:
            circuit = qpy.load(fh)[0]

        measured = _measured_physical_qubits(circuit)
        expected_measured = _expected_measured_from_label(label, physical_path)
        measured_match = measured == expected_measured

        logical_bit = _expected_logical_bit(label)
        prep_x = _prep_x_physical_qubits(circuit)
        prep_ok = True
        if _is_control_label(label):
            if logical_bit == 1:
                prep_ok = expected_measured[0] in prep_x
            else:
                prep_ok = expected_measured[0] not in prep_x

        counts_ok = None
        if label in raw_counts and raw_counts[label]:
            sample_key = next(iter(raw_counts[label].keys()))
            bit_len = len(sample_key.replace(" ", ""))
            counts_ok = bit_len == int(circuit.num_clbits)

        record_ok = bool(measured_match and prep_ok and (counts_ok in (None, True)))
        ok = ok and record_ok
        records.append(
            {
                "index": index,
                "label": label,
                "measured_physical_qubits": measured,
                "expected_measured_physical_qubits": expected_measured,
                "measured_qubits_match": measured_match,
                "prep_consistent": prep_ok,
                "counts_bit_length_match": counts_ok,
                "record_ok": record_ok,
            }
        )

    report = {
        "run_dir": str(run_dir),
        "physical_path_logical_order": physical_path,
        "num_circuits": len(records),
        "all_ok": ok,
        "records": records,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify hardware run circuit-to-label association from committed QPY artifacts.")
    parser.add_argument("run_dirs", nargs="+", help="One or more run directories to verify.")
    parser.add_argument(
        "--out",
        default=None,
        help="Optional output JSON path for the combined verification report.",
    )
    args = parser.parse_args()

    reports = [verify_run(Path(d)) for d in args.run_dirs]
    combined = {"all_ok": all(r["all_ok"] for r in reports), "reports": reports}

    if args.out:
        Path(args.out).write_text(json.dumps(combined, indent=2), encoding="utf-8")
        print("Wrote report:", args.out)

    for r in reports:
        print(f"{'OK ' if r['all_ok'] else 'FAIL'} {r['run_dir']} ({r['num_circuits']} circuits)")
        for rec in r["records"]:
            if not rec["record_ok"]:
                print("  MISMATCH:", rec)

    if not combined["all_ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
