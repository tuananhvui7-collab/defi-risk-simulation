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


@st.cache_data(show_spinner=False)
def load_results_csv(path: str, modified_time: float) -> pd.DataFrame:
    """Cache result tables and invalidate the cache when a CSV is regenerated."""
    del modified_time
    return pd.read_csv(path)


def read_results(filename: str):
    path = os.path.join(PROJECT_ROOT, "results", filename)
    if not os.path.exists(path):
        return None
    return load_results_csv(path, os.path.getmtime(path))

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
        summary_df = read_results("experiments_E1_E12_summary.csv")
        st.dataframe(summary_df, width="stretch", hide_index=True,
                     alt="Tổng hợp kết quả thực nghiệm E1 đến E12 và các chỉ số rủi ro")

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
            ts_df = read_results("experiments_E1_E12_timeseries.csv")
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
                st.pyplot(fig, alt=f"Diễn biến utilization của Fixed và Adaptive trong {scen_code}")
                plt.close(fig)

            with col2:
                fig, ax = plt.subplots(figsize=(8, 4))
                ax.plot(fixed_ts["step"], fixed_ts["pending_withdrawals_usdc"], label="Rút kẹt trong Queue (Fixed)", color="orange", linestyle="--")
                ax.plot(adapt_ts["step"], adapt_ts["pending_withdrawals_usdc"], label="Rút kẹt trong Queue (Adaptive)", color="purple")
                ax.set_title(f"Quy mô Hàng chờ Rút tiền ({scen_code})")
                ax.set_xlabel("Thời gian (Giờ)")
                ax.set_ylabel("USDC đang kẹt")
                ax.grid(True, alpha=0.3)
                ax.legend()
                st.pyplot(fig, alt=f"Số tiền rút còn kẹt của Fixed và Adaptive trong {scen_code}")
                plt.close(fig)

        # --- Bổ sung Phần Thống kê Monte Carlo 1.000 Vòng lặp ---
        df_mc = read_results("monte_carlo_1000_summary.csv")
        if df_mc is not None:
            st.markdown("---")
            st.markdown("### Monte Carlo: S0, S1 và S5")
            st.caption("1.000 run cho mỗi cặp kịch bản/chiến lược; seed chạy từ 42 đến 1041. VaR95 là phân vị thực nghiệm 95% của từng chỉ số trong mỗi nhóm.")
            st.dataframe(df_mc, width="stretch", hide_index=True,
                         alt="Mean, Median, độ lệch chuẩn và VaR95 của các chỉ số Monte Carlo")

        ablation_df = read_results("ablation_S5_summary.csv")
        if ablation_df is not None:
            st.markdown("---")
            st.markdown("### S5 Ablation Study: A1–A5")
            st.caption("Cùng seed 42, chỉ thay đổi Fixed/Adaptive của từng nhóm tác nhân.")
            ablation_columns = [
                "Mã thực nghiệm", "Ablation", "borrower_strategy", "lender_strategy",
                "liquidator_strategy", "Tỷ lệ thanh lý (%)", "liquidation_coverage_ratio",
                "realized_bad_debt_usdc", "unrealized_bad_debt_usdc",
                "total_bad_debt_exposure_usdc", "Rút tiền bị kẹt (USDC)",
                "withdrawal_fulfillment_rate",
            ]
            ablation_columns = [c for c in ablation_columns if c in ablation_df.columns]
            st.dataframe(ablation_df[ablation_columns], width="stretch", hide_index=True,
                         alt="Kết quả năm cấu hình S5 Ablation Study")

        s4_control_df = read_results("s4_liquidator_adaptive_only.csv")
        if s4_control_df is not None:
            st.markdown("### Đối chứng H5: chỉ Liquidator Adaptive trong S4")
            st.caption("Seed 42; Borrower và Lender giữ Fixed. Cùng đường giá S1 (-43%), chỉ thêm sốc gas và trượt giá.")
            s4_columns = [
                "Mã thực nghiệm", "Kịch bản", "borrower_strategy", "lender_strategy",
                "liquidator_strategy", "Tỷ lệ thanh lý (%)", "Lợi nhuận Liquidator ($)",
                "liquidation_coverage_ratio", "total_bad_debt_exposure_usdc",
            ]
            s4_columns = [c for c in s4_columns if c in s4_control_df.columns]
            st.dataframe(s4_control_df[s4_columns], width="stretch", hide_index=True,
                         alt="Đối chứng S4 chỉ bật chiến lược Liquidator Adaptive")
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
        ["Theo dõi theo giờ (chọn mốc)", "Chạy nhanh toàn bộ 168 giờ"],
        horizontal=True
    )

    if mode == "Theo dõi theo giờ (chọn mốc)":
        observed_hour = st.slider("Số giờ đã mô phỏng:", min_value=0, max_value=168, value=168)
        if st.button("Chạy mô phỏng đến mốc đã chọn", type="primary"):
            with st.spinner("Đang chạy mô hình đến thời điểm đã chọn..."):
                model = DeFiLendingMesaModel(
                    scenario_id=run_scen,
                    strategy=run_strat.lower(),
                    num_borrowers=n_borrowers,
                    seed=int(run_seed)
                )
                for _ in range(observed_hour):
                    model.step()
                sim_df = model.datacollector.get_model_vars_dataframe()
                current_step = max(0, observed_hour - 1)
                cur_price = model.market.get_market_state(current_step)["eth_price"]
                _, borrow_apr, _ = model.pool.ir_model.compute_rates(
                    model.pool.total_cash_usdc, model.pool.total_debt_usdc
                )
                n_liquidated = model._count_liquidated_borrowers()
                n_ever = model._count_ever_eligible()
                coverage = n_liquidated / n_ever if n_ever else 1.0
                unrealized = model._unrealized_bad_debt_at_price(cur_price)

            st.success(f"Đã mô phỏng {observed_hour}/168 giờ.")
            metrics = st.columns(4)
            metrics[0].metric("Giá ETH", f"${cur_price:,.2f}")
            metrics[1].metric("Utilization", f"{model.pool.utilization_rate:.1%}", f"Lãi vay {borrow_apr:.2%} APR")
            metrics[2].metric("Coverage Ratio", f"{coverage:.1%}", f"{n_liquidated}/{n_ever} borrower")
            metrics[3].metric("Tiền rút còn kẹt", f"${model.pool.total_pending_withdrawals:,.0f} USDC")
            risk_metrics = st.columns(4)
            risk_metrics[0].metric("Bad Debt thực hiện", f"${model.pool.total_bad_debt_usdc:,.2f}")
            risk_metrics[1].metric("Bad Debt tiềm ẩn", f"${unrealized:,.2f}")
            risk_metrics[2].metric("Fulfillment Rate", f"{model.pool.withdrawal_fulfillment_rate:.1%}")
            risk_metrics[3].metric("Vị thế HF < 1 hiện tại", str(model._count_undercollateralized()))

            chart_columns = st.columns(2)
            with chart_columns[0]:
                fig, ax = plt.subplots(figsize=(7, 3.5))
                ax.plot(sim_df["step"], sim_df["eth_price"], color="black")
                ax.set(title="Giá ETH", xlabel="Thời gian (giờ)", ylabel="USD")
                ax.grid(True, alpha=0.3)
                st.pyplot(fig, alt="Giá ETH từ đầu đến mốc giờ được chọn")
                plt.close(fig)
            with chart_columns[1]:
                fig, ax = plt.subplots(figsize=(7, 3.5))
                ax.plot(sim_df["step"], sim_df["pending_withdrawals_usdc"], color="black", linestyle="--")
                ax.set(title="Tiền rút đang chờ", xlabel="Thời gian (giờ)", ylabel="USDC")
                ax.grid(True, alpha=0.3)
                st.pyplot(fig, alt="USDC chưa giải ngân trong hàng chờ rút theo thời gian")
                plt.close(fig)
            recent_events = model.event_logs[-8:]
            if recent_events:
                st.markdown("#### Nhật ký sự kiện gần nhất")
                for event in reversed(recent_events):
                    st.caption(event)

    else:
        # Chạy nhanh toàn bộ mô phỏng
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

                m5, m6, m7, m8 = st.columns(4)
                m5.metric("Liquidation Coverage Ratio", f"{summary['liquidation_coverage_ratio']:.1%}",
                          f"{summary['Số Borrower bị TL']}/{summary['n_ever_eligible']} đã thanh lý/từng đủ điều kiện")
                m6.metric("Bad Debt thực hiện", f"${summary['realized_bad_debt_usdc']:,.2f} USDC")
                m7.metric("Bad Debt tiềm ẩn", f"${summary['unrealized_bad_debt_usdc']:,.2f} USDC")
                m8.metric("Withdrawal Fulfillment Rate", f"{summary['withdrawal_fulfillment_rate']:.1%}")

                st.markdown("### 📈 Diễn biến 168 Bước Thời gian")
                col_a, col_b = st.columns(2)
                with col_a:
                    fig, ax1 = plt.subplots(figsize=(8, 4))
                    ax1.plot(sim_df["step"], sim_df["eth_price"], color="black", label="Giá ETH (USD)")
                    ax1.set_xlabel("Thời gian (Giờ)")
                    ax1.set_ylabel("Giá ETH ($)")
                    ax1.grid(True, alpha=0.3)
                    st.pyplot(fig, alt="Giá ETH trong 168 giờ mô phỏng")
                    plt.close(fig)

                with col_b:
                    fig, ax2 = plt.subplots(figsize=(8, 4))
                    ax2.plot(sim_df["step"], sim_df["total_cash_usdc"], color="green", label="Cash khả dụng (USDC)")
                    ax2.plot(sim_df["step"], sim_df["total_debt_usdc"], color="red", label="Tổng nợ (USDC)")
                    ax2.set_xlabel("Thời gian (Giờ)")
                    ax2.set_ylabel("USDC")
                    ax2.grid(True, alpha=0.3)
                    ax2.legend()
                    st.pyplot(fig, alt="Cash khả dụng và tổng nợ qua 168 giờ")
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
