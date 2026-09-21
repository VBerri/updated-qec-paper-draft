from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_stim_logical_error(csv_path: str | Path = "results/stim_mwpm_results.csv", fig_path: str | Path = "figures/stim_logical_error_vs_p.png") -> None:
    df = pd.read_csv(csv_path).sort_values(["distance", "p"])
    fig, ax = plt.subplots(figsize=(8, 5))
    for d in sorted(df["distance"].unique()):
        sub = df[df["distance"] == d]
        ax.plot(sub["p"], sub["logical_error_rate"], marker="o", label=f"d={d}")
    ax.set_yscale("log")
    ax.set_xlabel("Physical error probability p")
    ax.set_ylabel("Logical error rate")
    ax.set_title("Stim + PyMatching Logical Error vs p")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    Path(fig_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=180)
    plt.close(fig)


def plot_bias_results(
    csv_path: str | Path = "results/bias_sweep_results.csv",
    heatmap_path: str | Path = "figures/bias_heatmap.png",
    curves_path: str | Path = "figures/bias_curves_by_distance.png",
) -> None:
    df = pd.read_csv(csv_path)

    d_ref = sorted(df["distance"].unique())[0]
    sub = df[df["distance"] == d_ref]
    table = sub.pivot_table(index="bias_z", columns="p_total", values="logical_error_rate", aggfunc="mean")

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(table.values, aspect="auto", origin="lower")
    ax.set_xticks(range(len(table.columns)))
    ax.set_xticklabels([f"{c:.3f}" for c in table.columns], rotation=45)
    ax.set_yticks(range(len(table.index)))
    ax.set_yticklabels([f"{i:g}" for i in table.index])
    ax.set_xlabel("p_total")
    ax.set_ylabel("bias_z")
    ax.set_title(f"Bias Sweep Heatmap (d={d_ref})")
    fig.colorbar(im, ax=ax, label="Logical error rate")
    fig.tight_layout()
    Path(heatmap_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(heatmap_path, dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    fixed_p = sorted(df["p_total"].unique())[min(1, len(df["p_total"].unique()) - 1)]
    sub = df[df["p_total"] == fixed_p].sort_values(["distance", "bias_z"])
    for d in sorted(sub["distance"].unique()):
        dd = sub[sub["distance"] == d]
        ax.plot(dd["bias_z"], dd["logical_error_rate"], marker="o", label=f"d={d}")
    ax.set_xscale("log")
    ax.set_xlabel("bias_z")
    ax.set_ylabel("Logical error rate")
    ax.set_title(f"Bias Curves by Distance (p_total={fixed_p:.3f})")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(curves_path, dpi=180)
    plt.close(fig)


def plot_heterogeneous_noise(
    csv_path: str | Path = "results/heterogeneous_noise_results.csv",
    fig_path: str | Path = "figures/heterogeneous_noise_plot.png",
) -> None:
    df = pd.read_csv(csv_path)
    agg = (
        df.groupby(["spread", "distance"], as_index=False)["logical_error_rate"]
        .mean()
        .sort_values(["distance", "spread"])
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    for d in sorted(agg["distance"].unique()):
        sub = agg[agg["distance"] == d]
        ax.plot(sub["spread"], sub["logical_error_rate"], marker="o", label=f"d={d}")
    ax.set_xlabel("Lognormal spread")
    ax.set_ylabel("Mean logical error rate")
    ax.set_title("Heterogeneous Noise Impact")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    Path(fig_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=180)
    plt.close(fig)


def plot_temporal_drift(
    csv_path: str | Path = "results/temporal_drift_results.csv",
    fig_path: str | Path = "figures/temporal_drift_plot.png",
) -> None:
    df = pd.read_csv(csv_path)
    agg = df.groupby("snapshot", as_index=False)["logical_error_rate"].mean()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(agg["snapshot"], agg["logical_error_rate"], marker="o")
    ax.set_xlabel("Calibration snapshot")
    ax.set_ylabel("Mean logical error rate")
    ax.set_title("Temporal Drift Snapshots")
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    Path(fig_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=180)
    plt.close(fig)


def plot_decoder_comparison(
    csv_path: str | Path = "results/decoder_comparison_results.csv",
    fig_path: str | Path = "figures/decoder_comparison.png",
) -> None:
    df = pd.read_csv(csv_path)
    method_labels = {
        "majority_vote": "Majority vote",
        "unweighted_mwpm": "Unweighted MWPM",
        "mwpm": "MWPM",
        "toy_film_neural": "Toy FiLM neural",
    }
    method_order = [
        method
        for method in ["majority_vote", "unweighted_mwpm", "mwpm", "toy_film_neural"]
        if method in set(df["method"])
    ]

    distances = sorted(df["distance"].unique())
    fig, axes = plt.subplots(1, len(distances), figsize=(4.2 * len(distances), 4.5), sharey=True)
    if len(distances) == 1:
        axes = [axes]

    for ax, distance in zip(axes, distances):
        sub = df[df["distance"] == distance].sort_values(["method", "p"])
        for method in method_order:
            method_sub = sub[sub["method"] == method].sort_values("p")
            if method_sub.empty:
                continue
            y = np.maximum(method_sub["logical_error_rate"].to_numpy(dtype=float), 0.5 / method_sub["shots"].to_numpy(dtype=float))
            ax.plot(
                method_sub["p"],
                y,
                marker="o",
                linewidth=1.8,
                label=method_labels.get(method, method),
            )
        ax.set_title(f"d={distance}")
        ax.set_xlabel("Physical error probability p")
        ax.set_yscale("log")
        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel("Logical error rate")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=min(len(labels), 4), frameon=False)
    fig.suptitle("Decoder Comparison by Distance", y=1.03)
    fig.tight_layout()
    Path(fig_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=180)
    plt.close(fig)


def plot_pipeline_diagram(fig_path: str | Path = "figures/pipeline_diagram.png") -> None:
    fig, ax = plt.subplots(figsize=(11, 3.5))
    ax.axis("off")

    labels = [
        "Layer 1\nQiskit Baseline",
        "Layer 2\nStim + MWPM",
        "Bias/Hetero/Drift\nStress Tests",
        "Decoder\nComparison",
        "Layer 3 Placeholder\nIBM Validation",
    ]
    xs = [0.08, 0.30, 0.52, 0.74, 0.92]

    for i, (x, label) in enumerate(zip(xs, labels)):
        ax.text(
            x,
            0.5,
            label,
            ha="center",
            va="center",
            fontsize=10,
            bbox={"boxstyle": "round,pad=0.4", "facecolor": "#e8f1f8", "edgecolor": "#335c81"},
        )
        if i < len(xs) - 1:
            ax.annotate(
                "",
                xy=(xs[i + 1] - 0.08, 0.5),
                xytext=(x + 0.08, 0.5),
                arrowprops={"arrowstyle": "->", "lw": 1.8, "color": "#1d3557"},
            )

    fig.tight_layout()
    Path(fig_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=180)
    plt.close(fig)
