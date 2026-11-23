"""
tests/test_abm.py — Unit tests cho Mô hình Đa tác nhân Mesa (ABM)
Kiểm tra tính toàn vẹn của Market, Protocol, Agents và Model.
"""

import pytest
import pandas as pd
from abm.market import MarketEnvironment
from abm.protocol import ProtocolPool, KinkInterestRateModel
from abm.model import DeFiLendingMesaModel
from abm.runner import run_single_experiment, EXPERIMENTS


def test_market_environment_initialization():
    m = MarketEnvironment(scenario_id="S0", base_price=2000.0)
    assert len(m.prices) == 168
    assert len(m.gas_fees) == 168
    assert m.prices[0] > 0

    # S1 price shock: price drops significantly
    m1 = MarketEnvironment(scenario_id="S1", base_price=2000.0)
    assert m1.prices[48] < m1.prices[24]
    assert pytest.approx(m1.prices[48] / m1.prices[24], 0.05) == 0.57


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
