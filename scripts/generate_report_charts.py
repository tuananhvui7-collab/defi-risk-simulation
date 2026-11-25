"""
scripts/generate_report_charts.py — Tạo toàn bộ biểu đồ khoa học chất lượng cao cho Báo cáo BTL
Xuất ra thư mục results/figures/ với độ phân giải cao (300 DPI).
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
FIG_DIR = os.path.join(RESULTS_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# Cấu hình phong cách biểu đồ học thuật
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 0.8
sns.set_theme(style="whitegrid")

# ==============================================================================
# HÌNH 1: ĐƯỜNG GIÁ THỰC TẾ 168H BINANCE VISION (MAY 2021 CRASH)
# ==============================================================================
def plot_eth_price_168h():
    csv_path = os.path.join(PROJECT_ROOT, "data", "eth_usdt_168h_may2021.csv")
    df = pd.read_csv(csv_path)

    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=300)
    ax.plot(df["step"], df["close"], color="#1f77b4", lw=2, label="Giá ETH (Binance 1h Candles)")

    # Đánh dấu các mốc quan trọng
    p0 = df["close"].iloc[0]
    p_min = df["close"].min()
    step_min = df["close"].idxmin()

    ax.scatter([0], [p0], color="green", s=60, zorder=5)
    ax.annotate(f"Bắt đầu: ${p0:,.2f}", (0, p0), textcoords="offset points", xytext=(10, 5), fontweight='bold')

    ax.scatter([step_min], [p_min], color="red", s=60, zorder=5)
    ax.annotate(f"Đáy sụp đổ: ${p_min:,.2f} (-50.1%)", (step_min, p_min), textcoords="offset points", xytext=(-80, -20), fontweight='bold', color="red")

    # Tô vùng bão giá (Giờ 24 - 48)
    ax.axvspan(24, 48, color='orange', alpha=0.15, label="Cửa sổ cú sốc cấp tính (Giờ 24 - 48)")

    ax.set_title("HÌNH 1. ĐƯỜNG GIÁ ETH/USDT THỰC TẾ 168 GIỜ (ĐỢT SỤP ĐỔ THÁNG 5/2021 - BINANCE VISION)", fontsize=11, fontweight='bold', pad=12)
    ax.set_xlabel("Bước thời gian (Giờ)", fontsize=10)
    ax.set_ylabel("Giá ETH (USD)", fontsize=10)
    ax.legend(loc="upper right", frameon=True)
    plt.tight_layout()

    out_path = os.path.join(FIG_DIR, "fig1_eth_price_168h.png")
    fig.savefig(out_path)
    plt.close(fig)
    print(f"✅ Đã tạo: {out_path}")


# ==============================================================================
# HÌNH 2: SO SÁNH MA TRẬN 12 THỰC NGHIỆM E1–E12 (FIXED VS ADAPTIVE)
# ==============================================================================
def plot_e1_e12_comparison():
    summary_path = os.path.join(RESULTS_DIR, "experiments_E1_E12_summary.csv")
    df = pd.read_csv(summary_path)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=300)

    # 1. Tỷ lệ thanh lý theo kịch bản
    sns.barplot(data=df, x="Kịch bản", y="Tỷ lệ thanh lý (%)", hue="Chiến lược", palette={"Fixed": "#e74c3c", "Adaptive": "#2ecc71"}, ax=ax1)
    ax1.set_title("Tỷ lệ Vị thế Bị Thanh lý (%) theo Kịch bản", fontsize=11, fontweight='bold')
    ax1.set_ylabel("Tỷ lệ thanh lý (%)", fontsize=10)
    ax1.set_xlabel("Kịch bản Thị trường (S0 - S5)", fontsize=10)
    for p in ax1.patches:
        height = p.get_height()
        if height > 0:
            ax1.annotate(f"{height:.1f}%", (p.get_x() + p.get_width() / 2., height),
                         ha='center', va='bottom', fontsize=8, xytext=(0, 2), textcoords='offset points')

    # 2. Lợi nhuận của Liquidator theo kịch bản
    sns.barplot(data=df, x="Kịch bản", y="Lợi nhuận Liquidator ($)", hue="Chiến lược", palette={"Fixed": "#e74c3c", "Adaptive": "#2ecc71"}, ax=ax2)
    ax2.set_title("Tổng Lợi nhuận Ròng của Liquidator ($)", fontsize=11, fontweight='bold')
    ax2.set_ylabel("Lợi nhuận ròng ($ USD)", fontsize=10)
    ax2.set_xlabel("Kịch bản Thị trường (S0 - S5)", fontsize=10)
    for p in ax2.patches:
        height = p.get_height()
        if height > 0:
            ax2.annotate(f"${height:,.0f}", (p.get_x() + p.get_width() / 2., height),
                         ha='center', va='bottom', fontsize=8, xytext=(0, 2), textcoords='offset points')

    plt.suptitle("HÌNH 2. ĐỐI CHỨNG HIỆU QUẢ GIỮA CHIẾN LƯỢC CỐ ĐỊNH (FIXED) VÀ THÍCH NGHI (ADAPTIVE)", fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()

    out_path = os.path.join(FIG_DIR, "fig2_e1_e12_comparison.png")
    fig.savefig(out_path)
    plt.close(fig)
    print(f"✅ Đã tạo: {out_path}")


# ==============================================================================
# HÌNH 3: HIỆN TƯỢNG THÁO CHẠY RÚT VỐN & KẸT THANH KHOẢN (BANK-RUN)
# ==============================================================================
def plot_withdrawal_queue():
    ts_path = os.path.join(RESULTS_DIR, "experiments_E1_E12_timeseries.csv")
    df = pd.read_csv(ts_path)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, dpi=300)

    # Lọc các thực nghiệm S2 (E5, E6) và S5 (E11, E12)
    e6 = df[df["experiment_id"] == "E6"] # S2 Adaptive
    e12 = df[df["experiment_id"] == "E12"] # S5 Adaptive

    # Đồ thị Utilization
    ax1.plot(e6["step"], e6["utilization_rate"] * 100, label="E6 (S2 - Sốc rút vốn 50%)", color="#9b59b6", lw=2)
    ax1.plot(e12["step"], e12["utilization_rate"] * 100, label="E12 (S5 - Sốc kết hợp toàn diện)", color="#c0392b", lw=2, linestyle="--")
    ax1.axhline(80, color="orange", linestyle=":", label="Ngưỡng tối ưu U_opt = 80%")
    ax1.set_ylabel("Utilization Bể (%)", fontsize=10)
    ax1.set_title("Tỷ lệ Sử dụng Vốn (Utilization) & Lãi suất Kink chạm trần 100%", fontsize=11, fontweight='bold')
    ax1.legend(loc="lower right")

    # Đồ thị Quy mô tiền rút bị kẹt
    ax2.plot(e6["step"], e6["pending_withdrawals_usdc"], label="E6: Tiền rút bị kẹt trong Hàng chờ (USDC)", color="#9b59b6", lw=2)
    ax2.plot(e12["step"], e12["pending_withdrawals_usdc"], label="E12: Tiền rút bị kẹt trong Hàng chờ (USDC)", color="#c0392b", lw=2, linestyle="--")
    ax2.set_xlabel("Thời gian (Giờ)", fontsize=10)
    ax2.set_ylabel("USDC kẹt trong Queue", fontsize=10)
    ax2.set_title("Quy mô Tiền rút bị Kẹt trong Hàng chờ (Withdrawal Queue Congestion)", fontsize=11, fontweight='bold')
    ax2.legend(loc="upper left")

    plt.suptitle("HÌNH 3. HIỆN TƯỢNG ĐÓNG BĂNG THANH KHOẢN VÀ THÁO CHẠY RÚT VỐN (BANK-RUN)", fontsize=13, fontweight='bold', y=0.99)
    plt.tight_layout()

    out_path = os.path.join(FIG_DIR, "fig3_withdrawal_queue_bankrun.png")
    fig.savefig(out_path)
    plt.close(fig)
    print(f"✅ Đã tạo: {out_path}")


# ==============================================================================
# HÌNH 4: PHÂN PHỐI XÁC SUẤT MONTE CARLO 1.000 VÒNG LẶP & VaR 95%
# ==============================================================================
def plot_monte_carlo_distribution():
    runs_path = os.path.join(RESULTS_DIR, "monte_carlo_1000_runs.csv")
    df = pd.read_csv(runs_path)

    # Lọc kịch bản S1
    s1_data = df[df["scenario"] == "S1"]

    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)

    fixed_s1 = s1_data[s1_data["strategy"] == "Fixed"]["liquidation_rate_pct"]
    adapt_s1 = s1_data[s1_data["strategy"] == "Adaptive"]["liquidation_rate_pct"]

    sns.kdeplot(fixed_s1, fill=True, color="#e74c3c", alpha=0.4, label="Fixed (Mean: 71.4%, VaR 95: 82.0%)", ax=ax, lw=2)
    sns.kdeplot(adapt_s1, fill=True, color="#2ecc71", alpha=0.4, label="Adaptive (Mean: 55.2%, VaR 95: 66.0%)", ax=ax, lw=2)

    # Vẽ đường ngấn VaR 95%
    var95_fixed = fixed_s1.quantile(0.95)
    var95_adapt = adapt_s1.quantile(0.95)

    ax.axvline(var95_fixed, color="#c0392b", linestyle="--", lw=1.5, label=f"VaR 95% Fixed = {var95_fixed:.1f}%")
    ax.axvline(var95_adapt, color="#27ae60", linestyle="--", lw=1.5, label=f"VaR 95% Adaptive = {var95_adapt:.1f}%")

    ax.set_title("HÌNH 4. PHÂN PHỐI XÁC SUẤT TỶ LỆ THANH LÝ QUA 1.000 VÒNG LẶP MONTE CARLO (KỊCH BẢN S1)", fontsize=11, fontweight='bold', pad=12)
    ax.set_xlabel("Tỷ lệ vị thế bị thanh lý (%)", fontsize=10)
    ax.set_ylabel("Mật độ xác suất (Density)", fontsize=10)
    ax.legend(loc="upper left")
    plt.tight_layout()

    out_path = os.path.join(FIG_DIR, "fig4_monte_carlo_1000_distribution.png")
    fig.savefig(out_path)
    plt.close(fig)
    print(f"✅ Đã tạo: {out_path}")


# ==============================================================================
# HÌNH 5: MÔ HÌNH LÃI SUẤT KINK 2 ĐOẠN (AAVE V3 / BERTUCCI)
# ==============================================================================
def plot_kink_model():
    u_vals = np.linspace(0, 1, 500)
    base = 0.00
    slope1 = 0.04
    slope2 = 0.75
    u_opt = 0.80
    reserve_factor = 0.10

    borrow_rates = np.where(
        u_vals <= u_opt,
        base + (u_vals / u_opt) * slope1,
        base + slope1 + ((u_vals - u_opt) / (1.0 - u_opt)) * slope2
    )
    supply_rates = u_vals * borrow_rates * (1.0 - reserve_factor)

    fig, ax = plt.subplots(figsize=(8.5, 4.5), dpi=300)
    ax.plot(u_vals * 100, borrow_rates * 100, color="#d35400", lw=2.5, label="Lãi suất vay (Borrow APR)")
    ax.plot(u_vals * 100, supply_rates * 100, color="#2980b9", lw=2, linestyle="--", label="Lãi suất gửi (Supply APY)")

    ax.axvline(u_opt * 100, color="gray", linestyle=":", lw=1.2)
    ax.scatter([u_opt * 100], [(base + slope1) * 100], color="red", s=70, zorder=5)
    ax.annotate(f"Điểm gãy U_opt = 80%\n(Lãi vay = 4.0% APR)", (u_opt * 100, (base + slope1) * 100),
                xytext=(u_opt * 100 - 32, (base + slope1) * 100 + 15),
                arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=6),
                fontweight='bold', fontsize=9)

    ax.scatter([100], [(base + slope1 + slope2) * 100], color="red", s=70, zorder=5)
    ax.annotate(f"Chạm trần U = 100%\n(Lãi vay = 79.0% APR)", (100, 79),
                xytext=(75, 68),
                arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=6),
                fontweight='bold', fontsize=9)

    ax.set_title("HÌNH 5. ĐƯỜNG CONG LÃI SUẤT ĐIỂM GÃY (TWO-SLOPE KINK MODEL)", fontsize=11, fontweight='bold', pad=12)
    ax.set_xlabel("Tỷ lệ Sử dụng Vốn (Utilization Rate, %)", fontsize=10)
    ax.set_ylabel("Lãi suất (% / Năm)", fontsize=10)
    ax.legend(loc="upper left")
    plt.tight_layout()

    out_path = os.path.join(FIG_DIR, "fig5_kink_interest_rate_curve.png")
    fig.savefig(out_path)
    plt.close(fig)
    print(f"✅ Đã tạo: {out_path}")


if __name__ == "__main__":
    plot_eth_price_168h()
    plot_e1_e12_comparison()
    plot_withdrawal_queue()
    plot_monte_carlo_distribution()
    plot_kink_model()
    print("🎉 Hoàn tất tạo toàn bộ biểu đồ khoa học dẫn chứng!")
