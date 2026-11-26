"""Health-factor unit tests for the current Mesa borrower model."""

import math

from abm.model import DeFiLendingMesaModel


def make_model():
    return DeFiLendingMesaModel(
        scenario_id="S0", num_borrowers=1, num_lenders=1,
        num_liquidators=1, seed=42
    )


def test_hf_safe():
    model = make_model()
    borrower = model.borrowers[0]
    borrower.collateral_eth = 5.0
    borrower.debt_usdc = 5000.0
    assert borrower.health_factor(2000.0, model.pool.liquidation_threshold) == 1.6


def test_hf_undercollateralized():
    model = make_model()
    borrower = model.borrowers[0]
    borrower.collateral_eth = 5.0
    borrower.debt_usdc = 9000.0
    hf = borrower.health_factor(2000.0, model.pool.liquidation_threshold)
    assert hf < 1.0
    assert math.isclose(hf, 8 / 9)


def test_hf_severe_shortfall():
    model = make_model()
    borrower = model.borrowers[0]
    borrower.collateral_eth = 1.0
    borrower.debt_usdc = 2000.0
    assert borrower.health_factor(1200.0, model.pool.liquidation_threshold) == 0.48


def test_no_debt_has_infinite_health_factor():
    model = make_model()
    borrower = model.borrowers[0]
    borrower.debt_usdc = 0.0
    assert borrower.health_factor(2000.0, model.pool.liquidation_threshold) == float("inf")
