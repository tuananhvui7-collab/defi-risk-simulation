"""Liquidation behavior tests for the current Mesa agents."""

from abm.model import DeFiLendingMesaModel


def make_model():
    return DeFiLendingMesaModel(
        scenario_id="S0", strategy="fixed", num_borrowers=1,
        num_lenders=1, num_liquidators=1, seed=42
    )


def test_eligible_borrower_is_liquidated_and_pool_debt_falls():
    model = make_model()
    borrower = model.borrowers[0]
    borrower.collateral_eth = 5.0
    borrower.debt_usdc = 9000.0
    model.pool.total_debt_usdc = 9000.0
    starting_debt = borrower.debt_usdc

    model.liquidators[0].step()

    assert borrower.times_liquidated == 1
    assert borrower.debt_usdc < starting_debt
    assert model.pool.total_debt_usdc < starting_debt
    assert borrower.collateral_eth > 0


def test_safe_borrower_is_not_liquidated():
    model = make_model()
    borrower = model.borrowers[0]
    borrower.collateral_eth = 5.0
    borrower.debt_usdc = 5000.0
    model.pool.total_debt_usdc = 5000.0

    model.liquidators[0].step()

    assert borrower.times_liquidated == 0
    assert borrower.debt_usdc == 5000.0


def test_unprofitable_fixed_liquidation_is_skipped():
    model = make_model()
    borrower = model.borrowers[0]
    borrower.collateral_eth = 0.01
    borrower.debt_usdc = 18.0
    model.pool.total_debt_usdc = 18.0
    model.market.gas_fees[:] = 500.0

    model.liquidators[0].step()

    assert borrower.times_liquidated == 0
    assert borrower.debt_usdc == 18.0
