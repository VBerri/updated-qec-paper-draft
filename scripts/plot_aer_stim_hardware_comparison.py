from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_aer_curve() -> tuple[list[float], list[float]]:
    rows = _read_csv(RESULTS_DIR / "baseline_qiskit_results.csv")
    # Use bit-flip, code_size=3 as the baseline reference slice.
    sel = [
        r for r in rows if r["experiment"] == "bit_flip" and int(r["code_size"]) == 3
    ]
    sel.sort(key=lambda r: float(r["p"]))
    p = [float(r["p"]) for r in sel]
    logical_error = [float(r["logical_error_rate"]) for r in sel]
    return p, logical_error


def _load_stim_curve() -> tuple[list[float], list[float]]:
    rows = _read_csv(RESULTS_DIR / "stim_mwpm_results.csv")
    # Use distance=3 to match the small-code baseline scale.
    sel = [r for r in rows if int(r["distance"]) == 3]
    sel.sort(key=lambda r: float(r["p"]))
    p = [float(r["p"]) for r in sel]
    logical_error = [float(r["logical_error_rate"]) for r in sel]
    return p, logical_error


def _load_hardware_points() -> tuple[list[str], list[float]]:
    rows = _read_csv(RESULTS_DIR / "ibm_hardware_validation_results.csv")
    labels = [r["label"] for r in rows]
    logical_error = [float(r["logical_error_rate"]) for r in rows]
    return labels, logical_error


def main() -> None:
    aer_p, aer_err = _load_aer_curve()
    stim_p, stim_err = _load_stim_curve()
    hw_labels, hw_err = _load_hardware_points()

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), dpi=160)

    # Panel A: matched x-axis comparison for simulation layers.
    ax0 = axes[0]
    ax0.plot(aer_p, aer_err, marker="o", lw=2.0, label="Aer baseline (bit-flip, n=3)")
    ax0.plot(stim_p, stim_err, marker="s", lw=2.0, label="Stim+MWPM (distance=3)")
    ax0.set_xlabel("Physical error rate p")
    ax0.set_ylabel("Logical error rate")
    ax0.set_title("Simulation comparison on shared axis")
    ax0.set_yscale("log")
    ax0.grid(alpha=0.25)
    ax0.legend(frameon=False, fontsize=9)

    # Panel B: hardware outcomes with simulation reference at p=0.01.
    ax1 = axes[1]
    x = np.arange(len(hw_labels))
    ax1.bar(x, hw_err, color="#3e7cb1", width=0.7, label="IBM hardware (observed)")

    # Reference anchors for interpretation.
    aer_anchor = next(err for p, err in zip(aer_p, aer_err) if abs(p - 0.01) < 1e-12)
    stim_anchor = next(err for p, err in zip(stim_p, stim_err) if abs(p - 0.01) < 1e-12)
    ax1.axhline(aer_anchor, color="#d1495b", ls="--", lw=1.8, label="Aer n=3 at p=0.01")
    ax1.axhline(stim_anchor, color="#2a9d8f", ls=":", lw=2.0, label="Stim d=3 at p=0.01")

    ax1.set_xticks(x)
    ax1.set_xticklabels(hw_labels, rotation=18, ha="right")
    ax1.set_ylabel("Logical error rate")
    ax1.set_title("Hardware outcomes with simulation anchors")
    ax1.set_yscale("log")
    ax1.grid(axis="y", alpha=0.25)
    ax1.legend(frameon=False, fontsize=9)

    fig.suptitle(
        "Aer vs Stim vs IBM hardware: logical-error comparison (lower is better)",
        fontsize=12,
        y=1.02,
    )
    fig.text(
        0.5,
        -0.01,
        "Note: hardware bars are constrained validation circuits (not a full threshold benchmark).",
        ha="center",
        fontsize=9,
    )

    out_path = FIGURES_DIR / "aer_stim_hardware_comparison.png"
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
