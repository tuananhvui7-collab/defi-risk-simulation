"""
app.py — Interactive Dashboard: DeFi Liquidation Risk Lab (Mesa ABM & Smart Contract)
Bài tập lớn môn Blockchain: Nghiên cứu khả năng chống chịu rủi ro của giao thức cho vay DeFi.

Chạy: python -m streamlit run app.py
"""

import os
import sys
import time
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

        # --- Bổ sung Phần Thống kê Monte Carlo 1.000 Vòng lặp ---
        mc_summary_path = os.path.join(PROJECT_ROOT, "results", "monte_carlo_1000_summary.csv")
        if os.path.exists(mc_summary_path):
            st.markdown("---")
            st.markdown("### 🎲 Phân phối Xác suất Rủi ro Monte Carlo 1.000 Lần Chạy (Official Benchmarks)")
            st.markdown("""
            Theo tiêu chuẩn kiểm định của **Chaudhary & Pinna (2022)** và Bảng tham số v0.1: Chạy **1.000 lần** mô phỏng ngẫu nhiên với hạt giống $Seed = 42 + k$ để tính toán **Độ lệch chuẩn**, **Trung vị** và **Giá trị Chịu rủi ro (VaR 95%)**.
            """)
            df_mc = pd.read_csv(mc_summary_path)
            st.dataframe(df_mc, use_container_width=True)
    else:
        st.info("Chưa có sẵn file tổng kết kết quả. Vui lòng chạy lệnh: `python abm/runner.py` để tạo dữ liệu!")


# ==============================================================================
# TAB 2: GIẢ LẬP TƯƠNG TÁC LIVE ABM & QUAN SÁT TỪNG BƯỚC
# ==============================================================================
with tab2:
    st.subheader("⚙️ Trực quan hóa Quá trình Chạy Mô hình Đa tác nhân (Mesa ABM)")
    st.markdown("Bạn có thể **tận mắt quan sát từng giờ trôi qua**: giá ETH sụt giảm, người vay tự vệ, bot thanh lý nhảy vào giải chấp, và người gửi tiền hoảng loạn rút vốn theo thời gian thực.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        run_scen = st.selectbox("Chọn Kịch bản:", ["S1", "S0", "S2", "S3", "S4", "S5"])
    with c2:
        run_strat = st.selectbox("Chọn Chiến lược:", ["Adaptive", "Fixed"])
    with c3:
        n_borrowers = st.slider("Số lượng Borrower:", min_value=20, max_value=150, value=50, step=10)
    with c4:
        run_seed = st.number_input("Random Seed:", value=42, step=1)

    mode = st.radio(
        "Chế độ hiển thị:",
        ["🎬 Xem trực tiếp chuyển động từng giờ (Live Playback)", "⚡ Chạy nhanh lấy toàn bộ kết quả (Instant)"],
        horizontal=True
    )

    if mode == "🎬 Xem trực tiếp chuyển động từng giờ (Live Playback)":
        speed = st.slider("Tốc độ chuyển động (giây / bước giờ):", min_value=0.01, max_value=0.15, value=0.03, step=0.01)
        start_btn = st.button("▶ Bắt đầu Mô phỏng Trực tiếp", type="primary")

        if start_btn:
            model = DeFiLendingMesaModel(
                scenario_id=run_scen,
                strategy=run_strat.lower(),
                num_borrowers=n_borrowers,
                seed=int(run_seed)
            )

            progress_bar = st.progress(0, text="Khởi động môi trường...")
            metric_box = st.empty()
            chart_box = st.empty()
            log_box = st.empty()

            for step_idx in range(168):
                model.step()

                # Cập nhật giao diện mỗi 2 bước để mượt mà
                if step_idx % 2 == 0 or step_idx == 167:
                    pct = (step_idx + 1) / 168.0
                    progress_bar.progress(pct, text=f"⏳ Đang chạy: Giờ {step_idx + 1}/168 (Ngày {(step_idx)//24 + 1}/7)")

                    # 1. Cập nhật Metrics thời gian thực
                    cur_state = model.market.get_market_state(step_idx)
                    cur_p = cur_state["eth_price"]
                    cur_u = model.pool.utilization_rate * 100.0
                    _, r_borrow, _ = model.pool.ir_model.compute_rates(model.pool.total_cash_usdc, model.pool.total_debt_usdc)
                    n_liquidated = sum(1 for b in model.borrowers if b.times_liquidated > 0)
                    n_undercol = sum(1 for b in model.borrowers if b.debt_usdc > 0 and b.health_factor(cur_p, model.pool.liquidation_threshold) < 1.0)
                    pending_q = model.pool.total_pending_withdrawals

                    with metric_box.container():
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("🪙 Giá ETH Hiện Tại", f"${cur_p:,.1f}", f"Giờ {step_idx+1}")
                        m2.metric("⚠️ Vị thế Dưới chuẩn / Bị TL", f"{n_undercol} nguy hiểm", f"{n_liquidated} đã thanh lý")
                        m3.metric("🏦 Utilization Bể", f"{cur_u:.1f}%", f"Lãi vay {r_borrow*100:.1f}% APR")
                        m4.metric("⏳ Hàng chờ Rút kẹt", f"${pending_q:,.0f} USDC", f"{len(model.pool.withdrawal_queue)} yêu cầu")

                    # 2. Cập nhật biểu đồ chuỗi thời gian đến giờ hiện tại
                    cur_df = model.datacollector.get_model_vars_dataframe()
                    with chart_box.container():
                        col_x, col_y = st.columns(2)
                        with col_x:
                            fig1, ax1 = plt.subplots(figsize=(6, 2.5))
                            ax1.plot(cur_df["step"], cur_df["eth_price"], color="#1f77b4", lw=2)
                            ax1.set_title("Biến động Giá ETH 168 Giờ ($)", fontsize=10)
                            ax1.set_xlabel("Giờ", fontsize=8)
                            ax1.grid(True, alpha=0.3)
                            st.pyplot(fig1)
                            plt.close(fig1)

                        with col_y:
                            fig2, ax2 = plt.subplots(figsize=(6, 2.5))
                            ax2.plot(cur_df["step"], cur_df["total_cash_usdc"], color="green", label="Cash khả dụng", lw=1.5)
                            ax2.plot(cur_df["step"], cur_df["total_debt_usdc"], color="red", label="Tổng nợ", lw=1.5)
                            ax2.set_title("Thanh khoản Bể (USDC)", fontsize=10)
                            ax2.set_xlabel("Giờ", fontsize=8)
                            ax2.grid(True, alpha=0.3)
                            ax2.legend(fontsize=8)
                            st.pyplot(fig2)
                            plt.close(fig2)

                    # 3. Cập nhật Nhật ký sự kiện trực tiếp
                    recent_events = model.event_logs[-6:] if hasattr(model, "event_logs") else []
                    with log_box.container():
                        st.markdown("**📜 Nhật ký Diễn biến Thời gian thực (Live Event Feed):**")
                        if recent_events:
                            for ev in reversed(recent_events):
                                st.caption(ev)
                        else:
                            st.caption("Chưa có sự kiện đột biến trong giờ này...")

                    time.sleep(speed)

            st.success("🎉 Mô phỏng 168 giờ hoàn tất!")

    else:
        # Chế độ chạy nhanh
        if st.button("🚀 Chạy Mô phỏng 168 Giờ ngay", type="primary"):
            with st.spinner("Đang tính toán qua Mesa Scheduler..."):
                cfg = {"exp_id": "CUSTOM", "scenario": run_scen, "strategy": run_strat.lower(), "hyp": "Tùy biến"}
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
                    ax1.set_ylabel("Giá ETH ($)")
                    ax1.grid(True, alpha=0.3)
                    st.pyplot(fig)
                    plt.close(fig)

                with col_b:
                    fig, ax2 = plt.subplots(figsize=(8, 4))
                    ax2.plot(sim_df["step"], sim_df["total_cash_usdc"], color="green", label="Cash khả dụng (USDC)")
                    ax2.plot(sim_df["step"], sim_df["total_debt_usdc"], color="red", label="Tổng nợ (USDC)")
                    ax2.set_xlabel("Thời gian (Giờ)")
                    ax2.set_ylabel("USDC")
                    ax2.grid(True, alpha=0.3)
                    ax2.legend()
                    st.pyplot(fig)
                    plt.close(fig)


# ==============================================================================
# TAB 3: SMART CONTRACT SEPOLIA & BENCHMARK
# ==============================================================================
with tab3:
    st.subheader("📜 Cấu trúc Smart Contract Solidity (Mạng Ethereum Sepolia)")
    st.markdown("""
    Toàn bộ hệ thống Smart Contract được thiết kế chuẩn mực theo kiến trúc **Aave V3 Core Architecture**, lưu trữ trong thư mục:
    `contract/`.
    """)

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("""
        #### 📦 Danh mục Hợp đồng:
        - `MockUSDC.sol`: Token USDC chuẩn ERC20 (6 decimals), có faucet mint.
        - **`MockPriceOracle.sol`**: Oracle giá ETH thật hỗ trợ 2 chế độ:
          - **Chainlink Live Feed** trên Sepolia: `0x694AA1769357215DE4FAC081bf1f309aDC325306`.
          - **Binance Real Data Feed**: Nạp trực tiếp 168 nến 1h sụp đổ thật từ Binance.
        - `InterestRateModel.sol`: Mô hình Lãi suất Kink ($U_{opt}=80\%$, $Slope_1=4\%$, $Slope_2=75\%$).
        - `DeFiLendingPool.sol`: Hợp đồng cho vay cốt lõi (Module hóa).
        - **`DeFiLendingPoolFlat.sol`**: File gộp toàn bộ, sẵn sàng copy 1 click vào **Remix IDE**.
        - `deploy.js`: Script deploy tự động lên Sepolia Testnet.
        - `feed_oracle_real_data.py`: Script nạp giá nến Binance thật vào Oracle on-chain.
        """)

    with col_c2:
        st.markdown("""
        #### 🌐 Nạp Dữ Liệu ETH Thật On-Chain:
        Khác với dữ liệu giả định lúc phát triển, Smart Contract hiện nay đã được cấu hình để **chạy hoàn toàn bằng dữ liệu thật**:
        1. **Giá ETH khởi điểm thật từ Binance**: `$3,465.98` (Đợt sụp đổ tháng 5/2021).
        2. **Chế độ Chainlink Live**: Bật `setUseChainlinkLive(true)` để hợp đồng tự động kéo giá thời gian thực từ mạng lưới Chainlink Sepolia.
        3. **Toàn bộ bộ kiểm thử (Test vectors)**: Được giữ độc lập và cách ly hoàn toàn trong Python (`pytest tests/ -v`).
        """)

    st.info("💡 Bạn có thể mở file `contract/README.md` để xem hướng dẫn chi tiết từng bước nạp dữ liệu thật trên Remix IDE và Sepolia Testnet!")
