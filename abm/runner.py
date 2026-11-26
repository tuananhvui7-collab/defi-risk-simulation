"""
abm/runner.py — Trình điều phối chạy Ma trận Thực nghiệm E1–E12
Chạy 12 thực nghiệm đối chứng giữa Chiến lược Cố định (Fixed) và Thích nghi (Adaptive)
cho 6 kịch bản S0–S5 trên cùng đường giá (Seed 42), trích xuất chỉ số kiểm chứng H1–H6.
"""

import os
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import numpy as np

from abm.model import DeFiLendingMesaModel

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")

EXPERIMENTS = [
    {"exp_id": "E1",  "scenario": "S0", "strategy": "fixed",    "desc": "Baseline, Fixed Strategy",            "hyp": "Đường cơ sở so sánh"},
    {"exp_id": "E2",  "scenario": "S0", "strategy": "adaptive", "desc": "Baseline, Adaptive Strategy",         "hyp": "Đường cơ sở so sánh"},
    {"exp_id": "E3",  "scenario": "S1", "strategy": "fixed",    "desc": "Price Shock (-43%), Fixed",           "hyp": "Kiểm tra H1, H4 (Rủi ro thanh lý)"},
    {"exp_id": "E4",  "scenario": "S1", "strategy": "adaptive", "desc": "Price Shock (-43%), Adaptive",        "hyp": "Kiểm tra H1, H4 (Rủi ro thanh lý)"},
    {"exp_id": "E5",  "scenario": "S2", "strategy": "fixed",    "desc": "Liquidity Shock (50% Run), Fixed",     "hyp": "Kiểm tra H3 (Khả năng đáp ứng rút tiền)"},
    {"exp_id": "E6",  "scenario": "S2", "strategy": "adaptive", "desc": "Liquidity Shock (50% Run), Adaptive",  "hyp": "Kiểm tra H3 (Khả năng đáp ứng rút tiền)"},
    {"exp_id": "E7",  "scenario": "S3", "strategy": "fixed",    "desc": "Interest Rate Shock (U=0.90), Fixed",  "hyp": "Chi phí vay và áp lực thanh khoản"},
    {"exp_id": "E8",  "scenario": "S3", "strategy": "adaptive", "desc": "Interest Rate Shock (U=0.90), Adaptive","hyp": "Chi phí vay và áp lực thanh khoản"},
    {"exp_id": "E9",  "scenario": "S4", "strategy": "fixed",    "desc": "Cost Shock (Gas 100, Slippage), Fixed","hyp": "Kiểm tra H2, H5 (Hiệu quả thanh lý)"},
    {"exp_id": "E10", "scenario": "S4", "strategy": "adaptive", "desc": "Cost Shock (Gas 100, Slippage), Adapt","hyp": "Kiểm tra H2, H5 (Hiệu quả thanh lý)"},
    {"exp_id": "E11", "scenario": "S5", "strategy": "fixed",    "desc": "Combined Shock (All Shocks), Fixed",   "hyp": "Kiểm tra H5, H6 (Khả năng chống chịu)"},
    {"exp_id": "E12", "scenario": "S5", "strategy": "adaptive", "desc": "Combined Shock (All Shocks), Adaptive","hyp": "Kiểm tra H5, H6 (Khả năng chống chịu)"},
]


def run_single_experiment(exp_config: dict, num_borrowers: int = 100, seed: int = 42) -> tuple:
    """Chạy 1 thực nghiệm cụ thể và trả về (summary_metrics, timeseries_df)."""
    model = DeFiLendingMesaModel(
        scenario_id=exp_config["scenario"],
        strategy=exp_config["strategy"],
        num_borrowers=num_borrowers,
        seed=seed,
        borrower_strategy=exp_config.get("borrower_strategy"),
        lender_strategy=exp_config.get("lender_strategy"),
        liquidator_strategy=exp_config.get("liquidator_strategy")
    )
    df = model.run_simulation(steps=168)

    # Tính toán các chỉ số tổng kết cuối phiên
    final_step = df.iloc[-1]
    bad_debt = final_step["total_bad_debt_usdc"]
    n_liquidated = final_step["n_liquidated_total"]
    liq_rate = (n_liquidated / num_borrowers) * 100
    max_u = df["utilization_rate"].max() * 100
    max_borrow_apr = df["borrow_rate_apr"].max() * 100
    avg_cash = df["total_cash_usdc"].mean()
    pending_withdrawals = final_step["pending_withdrawals_usdc"]
    avg_delay = final_step["avg_withdrawal_delay_hours"]
    liq_profit = final_step["total_liquidator_profit"]
    risk_metrics = model.final_risk_metrics(final_step=model.max_steps)

    # Tổng kết
    summary = {
        "Mã thực nghiệm": exp_config["exp_id"],
        "Kịch bản": exp_config["scenario"],
        "Chiến lược": exp_config["strategy"].capitalize(),
        "Nợ xấu (USDC)": round(bad_debt, 2),
        "Số Borrower bị TL": int(n_liquidated),
        "Tỷ lệ thanh lý (%)": round(liq_rate, 2),
        "Utilization max (%)": round(max_u, 2),
        "Lãi vay max (% APR)": round(max_borrow_apr, 2),
        "Cash khả dụng TB (USDC)": round(avg_cash, 2),
        "Rút tiền bị kẹt (USDC)": round(pending_withdrawals, 2),
        "Độ trễ rút TB (giờ)": round(avg_delay, 2),
        "avg_fulfilled_delay_h": round(risk_metrics["avg_fulfilled_delay_h"], 4),
        "avg_all_wait_h": round(risk_metrics["avg_all_wait_h"], 4),
        "withdrawal_fulfillment_rate": round(risk_metrics["withdrawal_fulfillment_rate"], 6),
        "n_ever_eligible": risk_metrics["n_ever_eligible"],
        "liquidation_coverage_ratio": round(risk_metrics["liquidation_coverage_ratio"], 6),
        "unliquidated_positions_end": risk_metrics["unliquidated_positions_end"],
        "unliquidated_debt_at_risk_usdc": round(risk_metrics["unliquidated_debt_at_risk_usdc"], 2),
        "realized_bad_debt_usdc": round(risk_metrics["realized_bad_debt_usdc"], 2),
        "unrealized_bad_debt_usdc": round(risk_metrics["unrealized_bad_debt_usdc"], 2),
        "unrealized_bad_debt_peak_usdc": round(risk_metrics["unrealized_bad_debt_peak_usdc"], 2),
        "total_bad_debt_exposure_usdc": round(risk_metrics["total_bad_debt_exposure_usdc"], 2),
        "total_bad_debt_exposure_peak_usdc": round(risk_metrics["total_bad_debt_exposure_peak_usdc"], 2),
        "exogenous_debt_usdc": round(float(final_step["exogenous_debt_usdc"]), 2),
        "Lợi nhuận Liquidator ($)": round(liq_profit, 2),
        "Mục đích kiểm chứng": exp_config["hyp"]
    }

    df["experiment_id"] = exp_config["exp_id"]
    df["scenario"] = exp_config["scenario"]
    df["strategy"] = exp_config["strategy"]

    return summary, df


S5_ABLATION_CONFIGS = [
    {"exp_id": "A1", "name": "All-Fixed", "borrower_strategy": "fixed", "lender_strategy": "fixed", "liquidator_strategy": "fixed"},
    {"exp_id": "A2", "name": "Borrower-Adaptive only", "borrower_strategy": "adaptive", "lender_strategy": "fixed", "liquidator_strategy": "fixed"},
    {"exp_id": "A3", "name": "Liquidator-Adaptive only", "borrower_strategy": "fixed", "lender_strategy": "fixed", "liquidator_strategy": "adaptive"},
    {"exp_id": "A4", "name": "Lender-Adaptive only", "borrower_strategy": "fixed", "lender_strategy": "adaptive", "liquidator_strategy": "fixed"},
    {"exp_id": "A5", "name": "All-Adaptive", "borrower_strategy": "adaptive", "lender_strategy": "adaptive", "liquidator_strategy": "adaptive"},
]


def run_s5_ablation_study(
    num_borrowers: int = 100,
    seed: int = 42,
    verbose: bool = True,
    save: bool = True
) -> tuple:
    """Run five S5 strategy ablations with a shared random seed."""
    summaries = []
    timeseries = []
    for config in S5_ABLATION_CONFIGS:
        exp = {
            "exp_id": config["exp_id"],
            "scenario": "S5",
            "strategy": "mixed",
            "desc": config["name"],
            "hyp": "S5 ablation study",
            **{key: config[key] for key in ("borrower_strategy", "lender_strategy", "liquidator_strategy")}
        }
        summary, df = run_single_experiment(exp, num_borrowers=num_borrowers, seed=seed)
        summary["Ablation"] = config["name"]
        summary["borrower_strategy"] = config["borrower_strategy"]
        summary["lender_strategy"] = config["lender_strategy"]
        summary["liquidator_strategy"] = config["liquidator_strategy"]
        df["ablation_id"] = config["exp_id"]
        for key in ("borrower_strategy", "lender_strategy", "liquidator_strategy"):
            df[key] = config[key]
        summaries.append(summary)
        timeseries.append(df)
        if verbose:
            print(f"{config['exp_id']} {config['name']}: {summary['Tỷ lệ thanh lý (%)']}% liquidated")

    summary_df = pd.DataFrame(summaries)
    timeseries_df = pd.concat(timeseries, ignore_index=True)
    if save:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        summary_df.to_csv(os.path.join(RESULTS_DIR, "ablation_S5_summary.csv"), index=False, encoding="utf-8-sig")
        timeseries_df.to_csv(os.path.join(RESULTS_DIR, "ablation_S5_timeseries.csv"), index=False, encoding="utf-8-sig")
    return summary_df, timeseries_df


def run_s4_liquidator_adaptive_only(
    num_borrowers: int = 100,
    seed: int = 42,
    save: bool = True,
) -> tuple:
    """Run S4 with only the liquidator strategy adaptive (seed-matched control)."""
    exp = {
        "exp_id": "S4_LiqAdaptive_Only",
        "scenario": "S4",
        "strategy": "mixed",
        "desc": "S4 — chỉ Liquidator Adaptive",
        "hyp": "Đối chứng cô lập vai trò Liquidator trong S4",
        "borrower_strategy": "fixed",
        "lender_strategy": "fixed",
        "liquidator_strategy": "adaptive",
    }
    summary, timeseries = run_single_experiment(exp, num_borrowers=num_borrowers, seed=seed)
    summary["borrower_strategy"] = "fixed"
    summary["lender_strategy"] = "fixed"
    summary["liquidator_strategy"] = "adaptive"
    if save:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        pd.DataFrame([summary]).to_csv(
            os.path.join(RESULTS_DIR, "s4_liquidator_adaptive_only.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        timeseries.to_csv(
            os.path.join(RESULTS_DIR, "s4_liquidator_adaptive_only_timeseries.csv"),
            index=False,
            encoding="utf-8-sig",
        )
    return summary, timeseries


def run_all_experiments(num_borrowers: int = 100, seed: int = 42, verbose: bool = True) -> tuple:
    """Chạy toàn bộ 12 thực nghiệm E1 đến E12."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    summaries = []
    timeseries_list = []

    print("==================================================================")
    print("🚀 BẮT ĐẦU CHẠY MA TRẬN 12 THỰC NGHIỆM E1–E12 (MESA ABM SIMULATOR)")
    print(f"   Quy mô: {num_borrowers} Borrowers | 168 bước/run | Seed: {seed}")
    print("==================================================================")

    t0 = time.time()
    for exp in EXPERIMENTS:
        exp_id = exp["exp_id"]
        scen = exp["scenario"]
        strat = exp["strategy"].upper()

        if verbose:
            print(f"▶ Đang chạy {exp_id} ({scen} - {strat})...", end="", flush=True)

        summary, df = run_single_experiment(exp, num_borrowers=num_borrowers, seed=seed)
        summaries.append(summary)
        timeseries_list.append(df)

        if verbose:
            print(f" Xong! Nợ xấu: {summary['Nợ xấu (USDC)']}$ | Tỷ lệ TL: {summary['Tỷ lệ thanh lý (%)']}%")

    total_time = time.time() - t0
    print(f"\n🎉 HOÀN THÀNH TOÀN BỘ 12 THỰC NGHIỆM TRONG {total_time:.2f} GIÂY!")

    summary_df = pd.DataFrame(summaries)
    all_timeseries = pd.concat(timeseries_list, ignore_index=True)

    summary_path = os.path.join(RESULTS_DIR, "experiments_E1_E12_summary.csv")
    timeseries_path = os.path.join(RESULTS_DIR, "experiments_E1_E12_timeseries.csv")

    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
    all_timeseries.to_csv(timeseries_path, index=False, encoding="utf-8-sig")

    print(f"📁 Đã lưu bảng tổng kết vào: {summary_path}")
    print(f"📁 Đã lưu chuỗi thời gian 168h vào: {timeseries_path}")
    print("==================================================================")

    return summary_df, all_timeseries


if __name__ == "__main__":
    summary_df, _ = run_all_experiments()
    print("\nBẢNG KẾT QUẢ THỰC NGHIỆM ĐỂ ĐƯA VÀO CHƯƠNG 6 BÁO CÁO:")
    print(summary_df.to_string(index=False))
