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
        "liquidation_rate_pct": round(liq_rate, 2),
        "num_liquidated": n_liq,
        "bad_debt_usdc": round(bad_debt, 2),
        "max_utilization_pct": round(max_u, 2),
        "max_borrow_apr_pct": round(max_apr, 2),
        "max_pending_withdrawals_usdc": round(max_pending_q, 2),
        "liquidator_profit_usd": round(liq_profit, 2)
    }


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
    Mặc định: Chạy kịch bản trọng tâm S1 (Sốc giá) và S5 (Sốc kết hợp)
    so sánh giữa Fixed và Adaptive qua 1.000 vòng lặp.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    if scenarios is None:
        scenarios = ["S1", "S5"]
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
                with ProcessPoolExecutor(max_workers=max_workers) as executor:
                    batch_res = list(executor.map(_single_mc_worker, tasks))

            all_results.extend(batch_res)
            sub_elapsed = time.time() - sub_t0
            print(f" Xong trong {sub_elapsed:.2f}s!")

    total_elapsed = time.time() - t0
    df_runs = pd.DataFrame(all_results)

    # Xuất toàn bộ dữ liệu 1.000 runs
    runs_file = os.path.join(RESULTS_DIR, f"monte_carlo_{n_runs}_runs.csv")
    df_runs.to_csv(runs_file, index=False, encoding="utf-8-sig")

    # Tính toán bảng phân phối thống kê & Value at Risk (VaR)
    summary_rows = []
    for (scen, strat), grp in df_runs.groupby(["scenario", "strategy"]):
        summary_rows.append({
            "Kịch bản": scen,
            "Chiến lược": strat,
            "Số lần chạy (N)": len(grp),
            "Tỷ lệ TL TB (%)": round(grp["liquidation_rate_pct"].mean(), 2),
            "Tỷ lệ TL Trung vị (%)": round(grp["liquidation_rate_pct"].median(), 2),
            "Độ lệch chuẩn TL (%)": round(grp["liquidation_rate_pct"].std(), 2),
            "Tỷ lệ TL 95% (VaR 95)": round(grp["liquidation_rate_pct"].quantile(0.95), 2),
            "Tỷ lệ TL Max (%)": round(grp["liquidation_rate_pct"].max(), 2),
            "Utilization Max TB (%)": round(grp["max_utilization_pct"].mean(), 2),
            "Lãi vay Max TB (% APR)": round(grp["max_borrow_apr_pct"].mean(), 2),
            "Rút tiền kẹt TB (USDC)": round(grp["max_pending_withdrawals_usdc"].mean(), 2),
            "Lợi nhuận Liquidator TB ($)": round(grp["liquidator_profit_usd"].mean(), 2)
        })

    df_summary = pd.DataFrame(summary_rows)
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
    run_monte_carlo(n_runs=1000, scenarios=["S1", "S5"], strategies=["fixed", "adaptive"], num_borrowers=50)
