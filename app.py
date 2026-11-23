"""
app.py — Interactive Dashboard: DeFi Liquidation Risk Lab (Mesa ABM & Smart Contract)
Bài tập lớn môn Blockchain: Nghiên cứu khả năng chống chịu rủi ro của giao thức cho vay DeFi.

Chạy: python -m streamlit run app.py
"""

import os
import sys
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from abm.model import DeFiLendingMesaModel
from abm.runner import EXPERIMENTS, run_single_experiment

st.set_page_config(
    page_title="DeFi Risk Lab — ABM & Smart Contract Simulator",
    page_icon="🏦",
    layout="wide"
)

st.title("🏦 DeFi Liquidation Risk Lab — Mesa ABM Simulator")
st.caption(
    "Nghiên cứu khả năng chống chịu rủi ro của giao thức cho vay DeFi dưới tác động của biến động thị trường và hành vi tương tác giữa các tác nhân (Bài tập lớn Blockchain)."
)

tab1, tab2, tab3 = st.tabs([
    "📊 Ma trận 12 Thực nghiệm (E1–E12)",
    "🎮 Giả lập Tương tác 168 Giờ (Live ABM)",
    "📜 Smart Contract (Sepolia & Benchmark)"
])

# ==============================================================================
# TAB 1: MA TRẬN 12 THỰC NGHIỆM E1–E12
# ==============================================================================
with tab1:
    st.subheader("📋 Bảng Tổng hợp Kết quả Thực nghiệm E1–E12")
    st.write("Dữ liệu thực nghiệm đối chứng giữa Chiến lược Cố định (Fixed) và Thích nghi (Adaptive) trên 6 kịch bản S0–S5 (Seed = 42).")

    summary_file = os.path.join(PROJECT_ROOT, "results", "experiments_E1_E12_summary.csv")
    timeseries_file = os.path.join(PROJECT_ROOT, "results", "experiments_E1_E12_timeseries.csv")

    if os.path.exists(summary_file):
        summary_df = pd.read_csv(summary_file)
        st.dataframe(summary_df, use_container_width=True)

        st.markdown("---")
        st.subheader("📈 So sánh Đối chứng Cố định (Fixed) vs Thích nghi (Adaptive)")

        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            selected_scenario = st.selectbox(
                "Chọn Kịch bản muốn so sánh:",
                ["S0 (Cơ sở)", "S1 (Cú sốc giá - H1, H4)", "S2 (Cú sốc thanh khoản - H3)", "S3 (Cú sốc lãi suất)", "S4 (Cú sốc chi phí vận hành - H2, H5)", "S5 (Cú sốc kết hợp - H5, H6)"]
            )
            scen_code = selected_scenario.split(" ")[0]

        if os.path.exists(timeseries_file):
            ts_df = pd.read_csv(timeseries_file)
            subset = ts_df[ts_df["scenario"] == scen_code]

            fixed_ts = subset[subset["strategy"] == "fixed"].reset_index(drop=True)
            adapt_ts = subset[subset["strategy"] == "adaptive"].reset_index(drop=True)

            col1, col2 = st.columns(2)

            with col1:
                fig, ax = plt.subplots(figsize=(8, 4))
                ax.plot(fixed_ts["step"], fixed_ts["utilization_rate"] * 100, label="Utilization (Fixed) %", color="red", linestyle="--")
                ax.plot(adapt_ts["step"], adapt_ts["utilization_rate"] * 100, label="Utilization (Adaptive) %", color="blue")
                ax.set_title(f"Tỷ lệ sử dụng vốn ({scen_code})")
                ax.set_xlabel("Thời gian (Giờ)")
                ax.set_ylabel("Utilization (%)")
                ax.grid(True, alpha=0.3)
                ax.legend()
                st.pyplot(fig)

            with col2:
                fig, ax = plt.subplots(figsize=(8, 4))
                ax.plot(fixed_ts["step"], fixed_ts["pending_withdrawals_usdc"], label="Rút kẹt trong Queue (Fixed)", color="orange", linestyle="--")
                ax.plot(adapt_ts["step"], adapt_ts["pending_withdrawals_usdc"], label="Rút kẹt trong Queue (Adaptive)", color="purple")
                ax.set_title(f"Quy mô Hàng chờ Rút tiền ({scen_code})")
                ax.set_xlabel("Thời gian (Giờ)")
                ax.set_ylabel("USDC đang kẹt")
                ax.grid(True, alpha=0.3)
                ax.legend()
                st.pyplot(fig)
    else:
        st.info("Chưa có sẵn file tổng kết kết quả. Vui lòng chạy lệnh: `python abm/runner.py` để tạo dữ liệu!")


# ==============================================================================
# TAB 2: GIẢ LẬP TƯƠNG TÁC LIVE ABM
# ==============================================================================
with tab2:
    st.subheader("⚙️ Tùy chỉnh & Chạy Trực tiếp Mô hình Đa tác nhân (Mesa)")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        run_scen = st.selectbox("Chọn Kịch bản:", ["S0", "S1", "S2", "S3", "S4", "S5"])
    with c2:
        run_strat = st.selectbox("Chọn Chiến lược:", ["Fixed", "Adaptive"])
    with c3:
        n_borrowers = st.slider("Số lượng Borrower:", min_value=20, max_value=200, value=50, step=10)
    with c4:
        run_seed = st.number_input("Random Seed:", value=42, step=1)

    if st.button("🚀 Chạy Mô phỏng 168 Giờ ngay", type="primary"):
        with st.spinner("Đang chạy mô phỏng 168 bước thời gian qua Mesa Scheduler..."):
            cfg = {"exp_id": "CUSTOM", "scenario": run_scen, "strategy": run_strat.lower(), "hyp": "Tùy biến trực tiếp"}
            summary, sim_df = run_single_experiment(cfg, num_borrowers=n_borrowers, seed=int(run_seed))

            st.success("✅ Mô phỏng hoàn tất!")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Tỷ lệ thanh lý", f"{summary['Tỷ lệ thanh lý (%)']}%", f"{summary['Số Borrower bị TL']} / {n_borrowers}")
            m2.metric("Nợ xấu phát sinh", f"${summary['Nợ xấu (USDC)']:,} USDC")
            m3.metric("Utilization lớn nhất", f"{summary['Utilization max (%)']}%")
            m4.metric("Rút tiền bị kẹt", f"${summary['Rút tiền bị kẹt (USDC)']:,} USDC")

            st.markdown("### 📈 Diễn biến 168 Bước Thời gian")
            col_a, col_b = st.columns(2)

            with col_a:
                fig, ax1 = plt.subplots(figsize=(8, 4))
                ax1.plot(sim_df["step"], sim_df["eth_price"], color="black", label="Giá ETH (USD)")
                ax1.set_xlabel("Thời gian (Giờ)")
                ax1.set_ylabel("Giá ETH ($)", color="black")
                ax1.grid(True, alpha=0.3)
                ax1.legend(loc="upper left")
                st.pyplot(fig)

            with col_b:
                fig, ax2 = plt.subplots(figsize=(8, 4))
                ax2.plot(sim_df["step"], sim_df["total_cash_usdc"], color="green", label="Cash khả dụng (USDC)")
                ax2.plot(sim_df["step"], sim_df["total_debt_usdc"], color="red", label="Tổng nợ (USDC)")
                ax2.set_xlabel("Thời gian (Giờ)")
                ax2.set_ylabel("USDC")
                ax2.grid(True, alpha=0.3)
                ax2.legend()
                st.pyplot(fig)


# ==============================================================================
# TAB 3: SMART CONTRACT SEPOLIA & BENCHMARK
# ==============================================================================
with tab3:
    st.subheader("📜 Cấu trúc Smart Contract Solidity (Mạng Ethereum Sepolia)")
    st.markdown("""
    Toàn bộ hệ thống Smart Contract được thiết kế chuẩn mực theo kiến trúc **Aave V3 Core Architecture**, lưu trữ trong thư mục:
    `contracts/` và `contract/`.
    """)

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("""
        #### 📦 Danh mục Hợp đồng:
        - `MockUSDC.sol`: Token USDC chuẩn ERC20 (6 decimals), có faucet mint.
        - `MockPriceOracle.sol`: Oracle giá ETH chuẩn Chainlink (8 decimals).
        - `InterestRateModel.sol`: Mô hình Lãi suất Kink ($U_{opt}=80\%$, $Slope_1=4\%$, $Slope_2=75\%$).
        - `DeFiLendingPool.sol`: Hợp đồng cho vay cốt lõi (Module hóa).
        - **`DeFiLendingPoolFlat.sol`**: File gộp toàn bộ, sẵn sàng copy 1 click vào **Remix IDE**.
        - `deploy.js`: Script deploy tự động lên Sepolia Testnet.
        """)

    with col_c2:
        st.markdown("""
        #### 🎯 Bộ Kiểm thử Chuẩn hóa (Benchmark Test Suite):
        Vị thế kiểm thử dùng chung: **2 ETH thế chấp, nợ 2.000 USDC, LT = 0.80**.
        | Giá ETH ($) | Giá trị thế chấp ($) | LTV | Health Factor | Trạng thái |
        |---|---|---|---|---|
        | **2.000** | 4.000 | 50.0% | **1.60** | ✅ An toàn |
        | **1.500** | 3.000 | 66.7% | **1.20** | ⚠️ Vùng rủi ro |
        | **1.250** | 2.500 | 80.0% | **1.00** | 🚨 Ngưỡng thanh lý |
        | **1.000** | 2.000 | 100.0% | **0.80** | 🔴 Đủ điều kiện thanh lý |
        """)

    st.info("💡 Bạn có thể mở file `contracts/README.md` hoặc `contract/README.md` để xem hướng dẫn chi tiết từng bước bấm test trên Remix IDE và Sepolia Testnet!")
