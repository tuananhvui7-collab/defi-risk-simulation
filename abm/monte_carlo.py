"""
abm/monte_carlo.py — Động cơ Mô phỏng Monte Carlo 1.000 lần (Chính thức)
Theo Bảng tham số mô phỏng v0.1:
- Số lần Monte Carlo: 1.000 (Mức chính thức - Chaudhary & Pinna 2022)
- Seed biến thiên: base_seed + k (tái lập hoàn toàn)
- Đánh giá phân phối rủi ro: Tỷ lệ thanh lý, Giá trị chịu rủi ro (VaR 95%, VaR 99%), Nợ xấu, Tắc nghẽn rút vốn
"""

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from abm.model import DeFiLendingMesaModel

RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")


def _single_mc_worker(args: tuple) -> dict:
    """Hàm worker độc lập để chạy song song trên đa nhân CPU."""
    run_idx, scenario_id, strategy, num_borrowers, base_seed = args
    seed = base_seed + run_idx

    model = DeFiLendingMesaModel(
        scenario_id=scenario_id,
        strategy=strategy,
        num_borrowers=num_borrowers,
        seed=seed
    )
    df = model.run_simulation(steps=168)

    final = df.iloc[-1]
    risk = model.final_risk_metrics(final_step=model.max_steps)
    n_liq = int(final["n_liquidated_total"])
    liq_rate = (n_liq / num_borrowers) * 100.0
    bad_debt = float(final["total_bad_debt_usdc"])
    max_u = float(df["utilization_rate"].max() * 100.0)
    max_apr = float(df["borrow_rate_apr"].max() * 100.0)
    max_pending_q = float(df["pending_withdrawals_usdc"].max())
    liq_profit = float(final["total_liquidator_profit"])

    return {
        "run_id": run_idx,
        "scenario": scenario_id,
        "strategy": strategy.capitalize(),
        "seed": seed,
        "liquidation_rate_pct": liq_rate,
        "num_liquidated": n_liq,
        "bad_debt_usdc": bad_debt,
        "realized_bad_debt_usdc": risk["realized_bad_debt_usdc"],
        "unrealized_bad_debt_usdc": risk["unrealized_bad_debt_usdc"],
        "unrealized_bad_debt_peak_usdc": risk["unrealized_bad_debt_peak_usdc"],
        "total_bad_debt_exposure_usdc": risk["total_bad_debt_exposure_usdc"],
        "max_utilization_pct": max_u,
        "max_borrow_apr_pct": max_apr,
        "max_pending_withdrawals_usdc": max_pending_q,
        "pending_withdrawals_usdc": float(model.pool.total_pending_withdrawals),
        "withdrawal_fulfillment_rate": risk["withdrawal_fulfillment_rate"],
        "n_ever_eligible": risk["n_ever_eligible"],
        "liquidation_coverage_ratio": risk["liquidation_coverage_ratio"],
        "liquidator_profit_usd": liq_profit
    }


MC_METRICS = {
    "liquidation_rate_pct": "Tỷ lệ thanh lý (%)",
    "liquidation_coverage_ratio": "Liquidation Coverage Ratio",
    "total_bad_debt_exposure_usdc": "Tổng Bad Debt Exposure (USDC)",
    "pending_withdrawals_usdc": "Tiền rút bị kẹt (USDC)",
    "withdrawal_fulfillment_rate": "Withdrawal Fulfillment Rate",
}


def summarize_monte_carlo(df_runs: pd.DataFrame) -> pd.DataFrame:
    """Compute empirical mean, median, sample std, and 95th percentile per group."""
    rows = []
    for (scenario, strategy), group in df_runs.groupby(["scenario", "strategy"], sort=True):
        row = {"Kịch bản": scenario, "Chiến lược": strategy, "Số lần chạy (N)": len(group)}
        for column in MC_METRICS:
            values = group[column]
            row[f"{column}_mean"] = values.mean()
            row[f"{column}_median"] = values.median()
            row[f"{column}_std"] = values.std(ddof=1)
            row[f"{column}_var95"] = values.quantile(0.95)
        # Retain commonly used diagnostics from previous summary files.
        row["Utilization Max TB (%)"] = group["max_utilization_pct"].mean()
        row["Lãi vay Max TB (% APR)"] = group["max_borrow_apr_pct"].mean()
        row["Lợi nhuận Liquidator TB ($)"] = group["liquidator_profit_usd"].mean()
        rows.append(row)
    return pd.DataFrame(rows)


def run_monte_carlo(
    n_runs: int = 1000,
    scenarios: list = None,
    strategies: list = None,
    num_borrowers: int = 50,
    base_seed: int = 42,
    max_workers: int = None
) -> tuple:
    """
    Chạy Monte Carlo n_runs lần cho các kịch bản và chiến lược chỉ định.
    Mặc định: Chạy S0 (Baseline), S1 (Sốc giá) và S5 (Sốc kết hợp)
    so sánh giữa Fixed và Adaptive qua 1.000 vòng lặp.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    if scenarios is None:
        scenarios = ["S0", "S1", "S5"]
    if strategies is None:
        strategies = ["fixed", "adaptive"]

    all_results = []
    print("==================================================================")
    print(f"🎲 BẮT ĐẦU CHẠY MONTE CARLO {n_runs:,} VÒNG LẶP (CHÍNH THỨC)")
    print(f"   Kịch bản: {scenarios} | Chiến lược: {strategies}")
    print(f"   Số Borrower: {num_borrowers} | Base Seed: {base_seed}")
    print("==================================================================")

    t0 = time.time()

    for scen in scenarios:
        for strat in strategies:
            sub_t0 = time.time()
            print(f"▶ Đang chạy: Kịch bản {scen} | Chiến lược {strat.upper()} ({n_runs} runs)...", end="", flush=True)

            tasks = [
                (i, scen, strat, num_borrowers, base_seed)
                for i in range(n_runs)
            ]

            # Dùng đa tiến trình nếu có nhiều CPU core
            if max_workers == 1:
                batch_res = [_single_mc_worker(t) for t in tasks]
            else:
                workers = max_workers if max_workers is not None else min(os.cpu_count() or 1, 8)
                with ProcessPoolExecutor(max_workers=workers) as executor:
                    batch_res = list(executor.map(_single_mc_worker, tasks, chunksize=20))

            all_results.extend(batch_res)
            sub_elapsed = time.time() - sub_t0
            print(f" Xong trong {sub_elapsed:.2f}s!")

    total_elapsed = time.time() - t0
    df_runs = pd.DataFrame(all_results)

    # Xuất toàn bộ dữ liệu 1.000 runs
    runs_file = os.path.join(RESULTS_DIR, f"monte_carlo_{n_runs}_runs.csv")
    df_runs.to_csv(runs_file, index=False, encoding="utf-8-sig")

    # The VaR field is the empirical 95th percentile of each run-level metric.
    df_summary = summarize_monte_carlo(df_runs)
    summary_file = os.path.join(RESULTS_DIR, f"monte_carlo_{n_runs}_summary.csv")
    df_summary.to_csv(summary_file, index=False, encoding="utf-8-sig")

    print("\n==================================================================")
    print(f"✅ HOÀN TẤT MONTE CARLO {n_runs:,} RUNS TRONG {total_elapsed:.2f} GIÂY!")
    print(f"   - File chi tiết: {runs_file}")
    print(f"   - File thống kê: {summary_file}")
    print("==================================================================")
    print(df_summary.to_string(index=False))

    return df_summary, df_runs


if __name__ == "__main__":
    run_monte_carlo(n_runs=1000, scenarios=["S0", "S1", "S5"], strategies=["fixed", "adaptive"], num_borrowers=50)
