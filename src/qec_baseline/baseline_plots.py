from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def _plot_experiment(df: pd.DataFrame, experiment: str, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    sub = df[df["experiment"] == experiment].sort_values(["code_size", "p"])
    for code_size in sorted(sub["code_size"].unique()):
        d = sub[sub["code_size"] == code_size]
        ax.plot(d["p"], d["logical_success_probability"], marker="o", label=f"n={code_size}")
    ax.set_title(f"Baseline {experiment.replace('_', ' ').title()} Logical Success")
    ax.set_xlabel("Physical error probability p")
    ax.set_ylabel("Logical success probability")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def generate_baseline_plots(
    csv_path: str | Path = "results/baseline_qiskit_results.csv",
    figure_dir: str | Path = "figures",
) -> None:
    figure_dir = Path(figure_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(csv_path)

    _plot_experiment(df, "bit_flip", figure_dir / "baseline_bitflip.png")
    _plot_experiment(df, "phase_flip", figure_dir / "baseline_phaseflip.png")
    _plot_experiment(df, "depolarizing", figure_dir / "baseline_depolarizing.png")

    p_target = 0.10
    summary = df[df["p"].round(2) == p_target]
    fig, ax = plt.subplots(figsize=(8, 5))
    for idx, exp in enumerate(["bit_flip", "phase_flip", "depolarizing"]):
        sub = summary[summary["experiment"] == exp].sort_values("code_size")
        x = [v + idx * 0.2 for v in range(len(sub))]
        ax.bar(x, sub["logical_success_probability"], width=0.2, label=exp)
    ax.set_xticks([0.2, 1.2, 2.2])
    ax.set_xticklabels(["n=1", "n=3", "n=5"])
    ax.set_title("Baseline Summary at p=0.10")
    ax.set_ylabel("Logical success probability")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(figure_dir / "baseline_summary_p010.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    sim = df[df["experiment"] == "bit_flip"].sort_values(["code_size", "p"])
    for code_size in sorted(sim["code_size"].unique()):
        sub = sim[sim["code_size"] == code_size]
        ax.plot(
            sub["p"],
            sub["logical_success_probability"],
            marker="o",
            label=f"sim n={code_size}",
        )
        if sub["theory_success_probability"].notna().any():
            ax.plot(
                sub["p"],
                sub["theory_success_probability"],
                linestyle="--",
                label=f"theory n={code_size}",
            )
    ax.set_title("Theory vs Simulation (Bit-Flip, 4 Idle Steps)")
    ax.set_xlabel("Physical error probability p")
    ax.set_ylabel("Logical success probability")
    ax.grid(True, alpha=0.3)
    ax.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(figure_dir / "baseline_theory_vs_sim.png", dpi=180)
    plt.close(fig)
