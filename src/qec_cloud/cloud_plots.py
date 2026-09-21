from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def placeholder_cloud_plot_message() -> str:
    return "IBM cloud plots are deferred to Layer 3 and are not generated in this phase."


def plot_ibm_hardware_validation(
    csv_path: str | Path = "results/ibm_hardware_validation_results.csv",
    fig_path: str | Path = "figures/ibm_hardware_validation.png",
) -> None:
    df = pd.read_csv(csv_path)
    ordered = df.sort_values(["basis", "idle_steps"])
    labels = [f"{b}-idle{s}" for b, s in zip(ordered["basis"], ordered["idle_steps"])]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, ordered["logical_success_probability"], color="#335c81")
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("Logical success probability")
    ax.set_xlabel("Circuit")
    ax.set_title("IBM Hardware Validation (n=3)")
    ax.grid(True, axis="y", alpha=0.3)
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()

    Path(fig_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=180)
    plt.close(fig)
