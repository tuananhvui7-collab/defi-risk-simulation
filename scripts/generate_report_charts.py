"""Generate black-and-white-friendly Vietnamese report figures from current results."""

import os
import sys
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
FIG_DIR = os.path.join(PROJECT_ROOT, "figures")
LEGACY_FIG_DIR = os.path.join(RESULTS_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(LEGACY_FIG_DIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "black",
    "axes.linewidth": 0.8,
    "figure.dpi": 150,
    "savefig.dpi": 300,
})


def save_figure(fig, filename, tight_rect=None):
    path = os.path.join(FIG_DIR, filename)
    if tight_rect is None:
        fig.tight_layout()
    else:
        fig.tight_layout(rect=tight_rect)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"Đã tạo {path}")
    # Keep the project's pre-existing results/figures location in sync.
    import shutil
    shutil.copy2(path, os.path.join(LEGACY_FIG_DIR, filename))


def plot_eth_price_168h():
    from abm.market import MarketEnvironment

    base = MarketEnvironment(scenario_id="S0", seed=42)
    shock = MarketEnvironment(scenario_id="S1", seed=42)
    steps = np.arange(168)
    fig, ax = plt.subplots(figsize=(10, 4.7))
    ax.plot(steps, base.prices, color="black", linestyle="-", linewidth=2,
            label="S0 — Baseline ổn định", marker="o", markevery=24, markersize=3)
    ax.plot(steps, shock.prices, color="#555555", linestyle="--", linewidth=1.8,
            label="S1 — Sốc giá (-43%)", marker="s", markevery=24, markersize=3)
    ax.axvspan(24, 48, facecolor="none", edgecolor="#777777", hatch="////",
               linewidth=0, label="Cửa sổ sốc, giờ 24–47")
    ax.set(title="Hình 1. Đường giá ETH mô phỏng: Baseline và Sốc giá",
           xlabel="Thời gian (giờ)", ylabel="Giá ETH (USD)")
    ax.grid(True, color="#bbbbbb", linewidth=0.5)
    ax.legend(frameon=True)
    save_figure(fig, "fig1_eth_price_168h.png")


def plot_e1_e12_comparison():
    path = os.path.join(RESULTS_DIR, "experiments_E1_E12_summary.csv")
    df = pd.read_csv(path)
    fig, axes = plt.subplots(3, 1, figsize=(13, 11), sharex=True)
    series = [
        ("Tỷ lệ thanh lý (%)", "Tỷ lệ borrower từng bị thanh lý (%)"),
        ("liquidation_coverage_ratio", "Liquidation Coverage Ratio"),
        ("Rút tiền bị kẹt (USDC)", "Tiền rút còn kẹt cuối phiên (USDC)"),
    ]
    x = np.arange(len(df) // 2)
    experiment_order = [f"E{i}" for i in range(1, 13)]
    fixed = df[df["Chiến lược"].str.lower() == "fixed"].copy()
    adaptive = df[df["Chiến lược"].str.lower() == "adaptive"].copy()
    for run in (fixed, adaptive):
        run["Mã thực nghiệm"] = pd.Categorical(run["Mã thực nghiệm"], categories=experiment_order, ordered=True)
    fixed = fixed.sort_values("Mã thực nghiệm")
    adaptive = adaptive.sort_values("Mã thực nghiệm")
    labels = [f"S{i} (E{2 * i + 1}–E{2 * i + 2})" for i in range(6)]
    for ax, (metric, ylabel) in zip(axes, series):
        width = 0.38
        a = ax.bar(x - width / 2, fixed[metric], width, label="Fixed",
                   facecolor="white", edgecolor="black", hatch="///")
        b = ax.bar(x + width / 2, adaptive[metric], width, label="Adaptive",
                   facecolor="#bdbdbd", edgecolor="black", hatch="...")
        ax.bar_label(a, fmt="%.2f", padding=2, fontsize=7)
        ax.bar_label(b, fmt="%.2f", padding=2, fontsize=7)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", color="#bbbbbb", linewidth=0.5)
        ax.legend(ncols=2)
    axes[-1].set_xticks(x, labels)
    axes[-1].set_xlabel("Kịch bản và cặp thực nghiệm")
    fig.suptitle("Hình 2. So sánh E1–E12 theo dữ liệu vừa chạy", fontsize=13)
    save_figure(fig, "fig2_e1_e12_comparison.png")


def plot_withdrawal_queue():
    path = os.path.join(RESULTS_DIR, "experiments_E1_E12_timeseries.csv")
    df = pd.read_csv(path)
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for exp_id, label, style, marker in [
        ("E6", "E6 — S2 Adaptive", "-", "o"),
        ("E12", "E12 — S5 Adaptive", "--", "s"),
    ]:
        run = df[df["experiment_id"] == exp_id]
        axes[0].plot(run["step"], run["utilization_rate"] * 100, label=label,
                     linestyle=style, color="black", marker=marker, markevery=24, markersize=3)
        axes[1].plot(run["step"], run["pending_withdrawals_usdc"], label=label,
                     linestyle=style, color="black", marker=marker, markevery=24, markersize=3)
    axes[0].axhline(80, color="#555555", linestyle=":", label="Điểm gãy lãi suất: 80%")
    axes[0].set_ylabel("Utilization (%)")
    axes[0].set_title("Mức sử dụng vốn")
    axes[1].set_ylabel("USDC đang chờ rút")
    axes[1].set_xlabel("Thời gian (giờ)")
    axes[1].set_title("Khối lượng yêu cầu rút chưa được đáp ứng")
    for ax in axes:
        ax.grid(True, color="#bbbbbb", linewidth=0.5)
        ax.legend()
    fig.suptitle("Hình 3. Hàng chờ rút tiền trong hai kịch bản thanh khoản", fontsize=12)
    save_figure(fig, "fig3_withdrawal_queue_bankrun.png")


def plot_monte_carlo_distribution():
    path = os.path.join(RESULTS_DIR, "monte_carlo_1000_runs.csv")
    df = pd.read_csv(path)
    groups = []
    labels = []
    hatches = []
    for scenario in ["S0", "S1", "S5"]:
        for strategy in ["Fixed", "Adaptive"]:
            vals = df.loc[(df["scenario"] == scenario) & (df["strategy"] == strategy), "liquidation_rate_pct"]
            if vals.empty:
                continue
            groups.append(vals.to_numpy())
            labels.append(f"{scenario}\n{strategy}")
            hatches.append("///" if strategy == "Fixed" else "...")
    fig, ax = plt.subplots(figsize=(10, 5.5))
    boxes = ax.boxplot(groups, patch_artist=True, showmeans=True,
                       meanprops={"marker": "D", "markerfacecolor": "black", "markeredgecolor": "black"},
                       medianprops={"color": "black", "linewidth": 1.6},
                       whiskerprops={"color": "black"}, capprops={"color": "black"},
                       flierprops={"marker": ".", "markerfacecolor": "#777777", "markeredgecolor": "#777777"})
    for i, box in enumerate(boxes["boxes"]):
        box.set(facecolor="white" if i % 2 == 0 else "#dddddd", edgecolor="black", hatch=hatches[i])
    ax.set_xticks(np.arange(1, len(labels) + 1), labels)
    ax.set_ylabel("Tỷ lệ thanh lý (%)")
    ax.set_title("Hình 4. Phân phối tỷ lệ thanh lý qua 1.000 lượt mỗi nhóm")
    ax.grid(axis="y", color="#bbbbbb", linewidth=0.5)
    ax.plot([], [], marker="D", color="black", linestyle="none", label="Mean")
    ax.plot([], [], color="black", linewidth=1.6, label="Median")
    ax.legend()
    save_figure(fig, "fig4_monte_carlo_1000_distribution.png")


def plot_kink_model():
    utilization = np.linspace(0, 1, 500)
    borrow = np.where(utilization <= 0.8, (utilization / 0.8) * 0.04,
                      0.04 + ((utilization - 0.8) / 0.2) * 0.75)
    supply = utilization * borrow * 0.9
    fig, ax = plt.subplots(figsize=(8.5, 4.7))
    ax.plot(utilization * 100, borrow * 100, color="black", linewidth=2,
            label="Lãi suất vay (APR)")
    ax.plot(utilization * 100, supply * 100, color="#555555", linestyle="--", linewidth=1.8,
            label="Lãi suất gửi (APR)")
    ax.axvline(80, color="#777777", linestyle=":", label="Điểm gãy Uopt = 80%")
    ax.set(title="Hình 5. Đường cong lãi suất Kink", xlabel="Utilization (%)", ylabel="Lãi suất (%/năm)")
    ax.grid(True, color="#bbbbbb", linewidth=0.5)
    ax.legend()
    save_figure(fig, "fig5_kink_interest_rate_curve.png")


def plot_s5_ablation():
    path = os.path.join(RESULTS_DIR, "ablation_S5_summary.csv")
    df = pd.read_csv(path)
    metrics = [
        ("Tỷ lệ thanh lý (%)", "Tỷ lệ thanh lý (%)"),
        ("liquidation_coverage_ratio", "Liquidation Coverage Ratio"),
        ("Rút tiền bị kẹt (USDC)", "USDC kẹt cuối phiên"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    hatches = ["///", "\\\\", "xx", "..", "++"]
    for ax, (metric, title) in zip(axes, metrics):
        bars = ax.bar(df["Mã thực nghiệm"], df[metric], facecolor="white", edgecolor="black")
        for bar, hatch in zip(bars, hatches):
            bar.set_hatch(hatch)
        if metric == "Rút tiền bị kẹt (USDC)":
            labels = [f"{value / 1000:.1f}k" if abs(value) >= 1000 else f"{value:.1f}" for value in df[metric]]
            ax.bar_label(bars, labels=labels, padding=2, fontsize=8)
        else:
            ax.bar_label(bars, fmt="%.2f", padding=2, fontsize=8)
        ax.set_title(title)
        ax.grid(axis="y", color="#bbbbbb", linewidth=0.5)
    fig.suptitle("Hình 6. So sánh năm cấu hình Ablation trong S5", fontsize=13)
    fig.text(0.5, 0.015,
             "A1 All-Fixed   |   A2 Borrower-Adaptive   |   A3 Liquidator-Adaptive   |   A4 Lender-Adaptive   |   A5 All-Adaptive",
             ha="center", va="bottom", fontsize=9)
    fig.subplots_adjust(top=0.82, wspace=0.32)
    save_figure(fig, "fig6_s5_ablation.png", tight_rect=[0, 0.10, 1, 0.92])


if __name__ == "__main__":
    plot_eth_price_168h()
    plot_e1_e12_comparison()
    plot_withdrawal_queue()
    plot_monte_carlo_distribution()
    plot_kink_model()
    plot_s5_ablation()
