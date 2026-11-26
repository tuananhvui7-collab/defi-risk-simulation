"""Shared health-factor and parameter checks used by the ABM simulator."""

import pytest

from abm.model import DeFiLendingMesaModel
from config.parameters import (
    validate_parameters,
    LIQUIDATION_THRESHOLD,
    LIQUIDATION_BONUS,
    BORROWER_LTV,
)


def test_parameter_constraints():
    assert validate_parameters() == []
    assert LIQUIDATION_THRESHOLD.value * (1 + LIQUIDATION_BONUS.value) < 1.0
    assert BORROWER_LTV.value["mean"] < LIQUIDATION_THRESHOLD.value


@pytest.mark.parametrize(
    ("price", "expected_hf", "eligible"),
    [(2000.0, 1.6, False), (1500.0, 1.2, False), (1250.0, 1.0, False), (1000.0, 0.8, True)],
)
def test_benchmark_case_table(price, expected_hf, eligible):
    model = DeFiLendingMesaModel(
        scenario_id="S0", num_borrowers=1, num_lenders=1,
        num_liquidators=1, seed=42
    )
    borrower = model.borrowers[0]
    borrower.collateral_eth = 2.0
    borrower.debt_usdc = 2000.0
    hf = borrower.health_factor(price, 0.80)
    assert hf == pytest.approx(expected_hf)
    assert (hf < 1.0) is eligible
