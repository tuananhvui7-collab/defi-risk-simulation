"""
tests/test_abm.py — Unit tests cho Mô hình Đa tác nhân Mesa (ABM)
Kiểm tra tính toàn vẹn của Market, Protocol, Agents và Model.
"""

import pytest
import pandas as pd
from abm.market import MarketEnvironment
from abm.protocol import ProtocolPool, KinkInterestRateModel
from abm.model import DeFiLendingMesaModel
from abm.runner import run_single_experiment, EXPERIMENTS, run_s5_ablation_study


def test_market_environment_initialization():
    m = MarketEnvironment(scenario_id="S0", base_price=2000.0)
    assert len(m.prices) == 168
    assert len(m.gas_fees) == 168
    assert m.prices[0] > 0
    assert m.prices.min() >= 1900.0
    assert m.prices.max() <= 2100.0
    assert (m.prices == MarketEnvironment(scenario_id="S0", base_price=2000.0).prices).all()

    # S2 and S3 isolate their shocks on the exact S0 stable price path.
    for scenario in ("S2", "S3"):
        isolated = MarketEnvironment(scenario_id=scenario, base_price=2000.0, seed=42)
        assert (isolated.prices == m.prices).all()

    # S1 price shock: price drops significantly
    m1 = MarketEnvironment(scenario_id="S1", base_price=2000.0)
    assert m1.prices[48] < m1.prices[24]
    assert pytest.approx(m1.prices[48] / m1.prices[24], 0.05) == 0.57
    assert m1.prices.min() < m.prices.min() * 0.75

    # S4 changes operating costs only and shares S1's price-shock path.
    m4 = MarketEnvironment(scenario_id="S4", base_price=2000.0, seed=42)
    assert (m4.prices == m1.prices).all()
    assert m4.gas_fees[0] == 100.0
    assert m4.slippage_s[0] == 5.0
    assert m4.slippage_v[0] == 100_000_000.0


def test_kink_interest_rate_model():
    ir = KinkInterestRateModel(base_rate=0.0, slope1=0.04, slope2=0.75, u_opt=0.80, reserve_factor=0.10)
    
    # 1. Zero debt
    u, r_b, r_s = ir.compute_rates(total_cash=1000.0, total_debt=0.0)
    assert u == 0.0
    assert r_b == 0.0
    assert r_s == 0.0

    # 2. Optimal utilization U = 80% (Debt 800, Cash 200)
    u_opt, r_b_opt, r_s_opt = ir.compute_rates(total_cash=200.0, total_debt=800.0)
    assert pytest.approx(u_opt, 0.001) == 0.80
    assert pytest.approx(r_b_opt, 0.001) == 0.04 # Base (0) + Slope1 (0.04)
    # Supply rate = U * R_b * (1 - RF) = 0.8 * 0.04 * 0.9 = 0.0288
    assert pytest.approx(r_s_opt, 0.001) == 0.0288

    # 3. Kink high utilization U = 90% (Debt 900, Cash 100)
    u_high, r_b_high, r_s_high = ir.compute_rates(total_cash=100.0, total_debt=900.0)
    assert pytest.approx(u_high, 0.001) == 0.90
    # R_borrow = 0.04 + (0.10 / 0.20) * 0.75 = 0.04 + 0.375 = 0.415
    assert pytest.approx(r_b_high, 0.001) == 0.415


def test_mesa_model_step_and_collector():
    model = DeFiLendingMesaModel(
        scenario_id="S0",
        strategy="fixed",
        num_borrowers=20,
        num_lenders=10,
        num_liquidators=3,
        seed=42
    )
    assert len(model.borrowers) == 20
    assert len(model.lenders) == 10
    assert len(model.liquidators) == 3
    assert model.current_step == 0

    # Chạy 5 bước
    for _ in range(5):
        model.step()

    assert model.current_step == 5
    df = model.datacollector.get_model_vars_dataframe()
    assert len(df) == 6 # t=0 plus 5 steps
    assert "eth_price" in df.columns
    assert "utilization_rate" in df.columns


def test_runner_single_experiment():
    cfg = EXPERIMENTS[0] # E1
    summary, df = run_single_experiment(cfg, num_borrowers=20, seed=42)
    assert summary["Mã thực nghiệm"] == "E1"
    assert len(df) == 169 # t=0 to 168
    assert "experiment_id" in df.columns
    assert summary["n_ever_eligible"] >= summary["Số Borrower bị TL"]
    assert 0.0 <= summary["liquidation_coverage_ratio"] <= 1.0
    assert "unrealized_bad_debt_peak_usdc" in summary
    assert "withdrawal_fulfillment_rate" in summary
    assert "avg_all_wait_h" in summary


def test_s3_exogenous_borrow_demand_does_not_inflate_borrower_principal():
    model = DeFiLendingMesaModel(
        scenario_id="S3", strategy="fixed", num_borrowers=10,
        num_lenders=5, num_liquidators=2, seed=42
    )
    starting_debts = [b.debt_usdc for b in model.borrowers]
    for _ in range(36):
        model.step()

    assert model.pool.exogenous_debt_usdc > 0
    assert model.pool.utilization_rate > 0.80
    # Existing borrowers accrue hourly interest only; external demand is not
    # allocated to their accounts as additional principal.
    assert all(b.debt_usdc < initial * 1.02 for b, initial in zip(model.borrowers, starting_debts))


def test_withdrawal_metrics_include_pending_requests_at_horizon():
    pool = ProtocolPool()
    pool.total_cash_usdc = 0.0
    pool.total_supply_usdc = 100.0
    pool.queue_withdrawal(lender_id=1, amount=40.0, current_step=10)

    assert pool.total_withdrawal_requested_usdc == 40.0
    assert pool.total_withdrawal_fulfilled_usdc == 0.0
    assert pool.withdrawal_fulfillment_rate == 0.0
    assert pool.average_fulfilled_withdrawal_delay() == 0.0
    assert pool.average_all_queued_withdrawal_wait(168) == 158.0

    pool.total_cash_usdc = 40.0
    pool.process_withdrawal_queue(current_step=168, lenders_dict={})
    assert pool.withdrawal_fulfillment_rate == 1.0
    assert pool.average_fulfilled_withdrawal_delay() == 158.0
    assert pool.average_all_queued_withdrawal_wait(168) == 158.0


def test_risk_metrics_track_ever_eligible_and_unliquidated_debt():
    model = DeFiLendingMesaModel(
        scenario_id="S0", strategy="fixed", num_borrowers=5,
        num_lenders=2, num_liquidators=1, seed=42
    )
    model._mark_ever_undercollateralized(eth_price=1.0)
    assert model._count_ever_eligible() == 5
    model.market.prices[0] = 1.0
    metrics = model.final_risk_metrics(final_step=0)
    assert metrics["n_ever_eligible"] == 5
    assert metrics["unliquidated_positions_end"] == 5
    assert metrics["unliquidated_debt_at_risk_usdc"] > 0
    assert metrics["unrealized_bad_debt_usdc"] > 0
    assert metrics["total_bad_debt_exposure_usdc"] >= metrics["realized_bad_debt_usdc"]


def test_s5_ablation_study_has_five_independent_strategy_configs():
    summary, timeseries = run_s5_ablation_study(num_borrowers=4, seed=42, verbose=False, save=False)
    assert summary["Mã thực nghiệm"].tolist() == ["A1", "A2", "A3", "A4", "A5"]
    assert len(timeseries["ablation_id"].unique()) == 5
    assert summary.loc[summary["Mã thực nghiệm"] == "A2", "borrower_strategy"].iloc[0] == "adaptive"
    assert summary.loc[summary["Mã thực nghiệm"] == "A2", "lender_strategy"].iloc[0] == "fixed"
    assert summary.loc[summary["Mã thực nghiệm"] == "A3", "liquidator_strategy"].iloc[0] == "adaptive"
