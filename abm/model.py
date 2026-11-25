"""
abm/model.py — Mô hình Đa tác nhân DeFi Lending (Mesa Model)
Quản lý vòng lặp 168 bước, điều phối lịch trình hành động của 3 nhóm tác nhân,
thu thập chuỗi dữ liệu phục vụ kiểm chứng các giả thuyết H1 đến H6.
"""

import os
import sys
import math

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import mesa
import pandas as pd
import numpy as np

from abm.market import MarketEnvironment
from abm.protocol import ProtocolPool, KinkInterestRateModel
from abm.agents import BorrowerAgent, LenderAgent, LiquidatorAgent


class DeFiLendingMesaModel(mesa.Model):
    """
    Mô hình Đa tác nhân chuẩn Mesa 3.x cho Giao thức Cho vay DeFi.
    """

    def __init__(
        self,
        scenario_id: str = "S0",
        strategy: str = "fixed", # 'fixed' hoặc 'adaptive'
        num_borrowers: int = 100,
        num_lenders: int = 50,
        num_liquidators: int = 10,
        initial_u0: float = 0.60,
        liquidation_threshold: float = 0.80,
        liquidation_bonus: float = 0.05,
        close_factor: float = 0.50,
        min_liquidity_reserve_pct: float = 0.0,
        h_fixed: float = 1.10,
        seed: int = 42,
        historical_csv: str = "eth_usdt_168h_active.csv"
    ):
        super().__init__(seed=seed)
        self.scenario_id = scenario_id
        self.strategy = strategy.lower()
        self.num_borrowers = num_borrowers
        self.num_lenders = num_lenders
        self.num_liquidators = num_liquidators
        self.current_step = 0
        self.max_steps = 168
        self.price_history = []
        self.bad_debt_events = []
        self.event_logs = []

        # 1. Khởi tạo Môi trường thị trường
        self.market = MarketEnvironment(
            scenario_id=scenario_id,
            base_price=2000.0,
            historical_csv=historical_csv,
            seed=seed
        )

        # 2. Khởi tạo Bể cho vay
        ir_model = KinkInterestRateModel(
            base_rate=0.00,
            slope1=0.04,
            slope2=0.75,
            u_opt=0.80,
            reserve_factor=0.10
        )
        self.pool = ProtocolPool(
            close_factor=close_factor,
            liquidation_threshold=liquidation_threshold,
            liquidation_bonus=liquidation_bonus,
            min_liquidity_reserve_pct=min_liquidity_reserve_pct,
            ir_model=ir_model
        )

        p0 = self.market.get_market_state(0)["eth_price"]
        self.price_history.append(p0)

        # 3. Tạo Tác nhân Borrower (Phân phối Lognormal trung bình 5.000 USD nợ, LTV ban đầu ~ 0.60)
        # lognormal: mu, sigma sao cho mean = 5000
        # mean = exp(mu + sigma^2/2) -> với sigma = 0.5 -> mu = ln(5000) - 0.125 = 8.392
        self.borrowers = []
        rng = np.random.default_rng(seed)
        debts = rng.lognormal(mean=8.392, sigma=0.5, size=num_borrowers)
        ra_borrowers = rng.beta(2, 2, size=num_borrowers)
        ltvs = np.clip(rng.normal(0.60, 0.05, size=num_borrowers), 0.45, 0.75)

        total_borrowed = 0.0
        total_col_eth = 0.0

        for i in range(num_borrowers):
            d = float(debts[i])
            ltv = float(ltvs[i])
            col_eth = d / (ltv * p0)
            ra = float(ra_borrowers[i])

            b = BorrowerAgent(
                model=self,
                collateral_eth=col_eth,
                debt_usdc=d,
                risk_appetite=ra,
                strategy=self.strategy,
                h_fixed=h_fixed
            )
            self.borrowers.append(b)
            total_borrowed += d
            total_col_eth += col_eth

        self.pool.total_debt_usdc = total_borrowed
        self.pool.total_collateral_eth = total_col_eth

        # 4. Tạo Tác nhân Lender (Tổng cung S0 = TotalDebt / U0)
        total_supply_needed = total_borrowed / initial_u0
        lender_deposit_each = total_supply_needed / num_lenders
        ra_lenders = rng.beta(2, 2, size=num_lenders)

        self.lenders = []
        self.lenders_dict = {}

        for i in range(num_lenders):
            ra = float(ra_lenders[i])
            l = LenderAgent(
                model=self,
                deposited_usdc=lender_deposit_each,
                risk_appetite=ra,
                strategy=self.strategy
            )
            self.lenders.append(l)
            self.lenders_dict[l.unique_id] = l

        self.pool.total_supply_usdc = total_supply_needed
        self.pool.total_cash_usdc = total_supply_needed - total_borrowed # 1 - U0 = 40%
        self.initial_total_supply = float(total_supply_needed)

        # 5. Tạo Tác nhân Liquidator (10 liquidator, tổng vốn 500.000 USD)
        self.liquidators = []
        ra_liquidators = rng.beta(2, 2, size=num_liquidators)
        capital_each = 500_000.0 / num_liquidators

        for i in range(num_liquidators):
            ra = float(ra_liquidators[i])
            liq = LiquidatorAgent(
                model=self,
                capital_usdc=capital_each,
                risk_appetite=ra,
                strategy=self.strategy
            )
            self.liquidators.append(liq)

        # 6. Thiết lập DataCollector để thu thập dữ liệu chuỗi thời gian
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "step": lambda m: m.current_step,
                "eth_price": lambda m: m.market.get_market_state(m.current_step)["eth_price"],
                "gas_fee_usd": lambda m: m.market.get_market_state(m.current_step)["gas_fee_usd"],
                "utilization_rate": lambda m: m.pool.utilization_rate,
                "borrow_rate_apr": lambda m: m.pool.ir_model.compute_rates(m.pool.total_cash_usdc, m.pool.total_debt_usdc)[1],
                "supply_rate_apr": lambda m: m.pool.ir_model.compute_rates(m.pool.total_cash_usdc, m.pool.total_debt_usdc)[2],
                "total_debt_usdc": lambda m: m.pool.total_debt_usdc,
                "total_cash_usdc": lambda m: m.pool.total_cash_usdc,
                "total_supply_usdc": lambda m: m.pool.total_supply_usdc,
                "total_bad_debt_usdc": lambda m: m.pool.total_bad_debt_usdc,
                "total_collateral_eth": lambda m: m.pool.total_collateral_eth,
                "n_undercollateralized": self._count_undercollateralized,
                "n_liquidated_total": self._count_liquidated_borrowers,
                "withdrawal_queue_len": lambda m: len(m.pool.withdrawal_queue),
                "pending_withdrawals_usdc": lambda m: m.pool.total_pending_withdrawals,
                "completed_withdrawals_count": lambda m: m.pool.completed_withdrawals_count,
                "avg_withdrawal_delay_hours": self._calc_avg_withdrawal_delay,
                "total_liquidator_profit": lambda m: sum(liq.total_profit_usd for liq in m.liquidators),
            }
        )

        # Thu thập điểm xuất phát t=0
        self.datacollector.collect(self)

    def _count_undercollateralized(self) -> int:
        p = self.market.get_market_state(self.current_step)["eth_price"]
        lt = self.pool.liquidation_threshold
        return sum(1 for b in self.borrowers if b.debt_usdc > 0 and b.health_factor(p, lt) < 1.0)

    def _count_liquidated_borrowers(self) -> int:
        return sum(1 for b in self.borrowers if b.times_liquidated > 0)

    def _calc_avg_withdrawal_delay(self) -> float:
        if self.pool.completed_withdrawals_count == 0:
            return 0.0
        return self.pool.total_withdrawal_delay_steps / self.pool.completed_withdrawals_count

    def step(self):
        """Vòng lặp 1 bước thời gian (1 giờ)."""
        if self.current_step >= self.max_steps:
            self.running = False
            return

        m_state = self.market.get_market_state(self.current_step)
        eth_price = m_state["eth_price"]
        prev_price = self.price_history[-1] if self.price_history else eth_price
        self.price_history.append(eth_price)

        # Log biến động giá mạnh
        price_change_pct = ((eth_price - prev_price) / prev_price) * 100.0 if prev_price > 0 else 0.0
        if abs(price_change_pct) >= 2.5:
            direction = "sụt giảm" if price_change_pct < 0 else "hồi phục"
            self.event_logs.append(
                f"⏱️ [Giờ {self.current_step:03d}] Giá ETH {direction} {price_change_pct:+.1f}% -> ${eth_price:,.2f}"
            )

        # 1. Bể cho vay cộng dồn lãi suất nợ và lãi gửi, đồng thời cộng dồn nợ cho từng Borrower
        u, r_borrow, r_supply = self.pool.accrue_interest_step()
        dt_year = 1.0 / 8760.0
        borrow_rate_step = r_borrow * dt_year
        for b in self.borrowers:
            if b.debt_usdc > 0:
                b.debt_usdc += b.debt_usdc * borrow_rate_step

        # 2. Xử lý các cú sốc kịch bản ngoại sinh
        # Kịch bản S2: Lender rút 50% tổng cung USDC ban đầu trong 12 bước từ bước 24
        if self.scenario_id in ["S2", "S5"]:
            if 24 <= self.current_step < 36:
                # Mỗi bước rút (50% / 12) = ~4.1667% tổng cung USDC ban đầu
                shock_withdrawal = (self.initial_total_supply * 0.50) / 12.0
                self.pool.queue_withdrawal(lender_id=9999, amount=shock_withdrawal, current_step=self.current_step)

        # Kịch bản S3: Utilization mục tiêu 0.90 đạt trong 12 bước từ bước 24 (Vượt điểm gãy 80%)
        if self.scenario_id == "S3":
            if 24 <= self.current_step < 36:
                # Đẩy utilization lên 90% bằng cách tăng nhu cầu vay ngoại sinh gán trực tiếp cho Borrowers
                target_u = 0.90
                current_u = self.pool.utilization_rate
                if current_u < target_u and self.pool.total_cash_usdc > 0:
                    needed_borrow = (target_u * (self.pool.total_cash_usdc + self.pool.total_debt_usdc)) - self.pool.total_debt_usdc
                    step_borrow = max(0.0, needed_borrow / (36 - self.current_step))
                    actual_step_borrow = min(step_borrow, self.pool.total_cash_usdc)
                    if actual_step_borrow > 0:
                        active_borrowers = [b for b in self.borrowers if b.debt_usdc > 0 and b.collateral_eth > 0]
                        if active_borrowers:
                            total_active_debt = sum(b.debt_usdc for b in active_borrowers)
                            for b in active_borrowers:
                                share = (b.debt_usdc / total_active_debt) if total_active_debt > 0 else (1.0 / len(active_borrowers))
                                b.debt_usdc += actual_step_borrow * share
                        self.pool.total_debt_usdc += actual_step_borrow
                        self.pool.total_cash_usdc = max(0.0, self.pool.total_cash_usdc - actual_step_borrow)

        # 3. Giai đoạn 1: Hành động của Borrowers (Kiểm tra vị thế, tự vệ hoặc vay thêm)
        for b in self.borrowers:
            b.step()

        # 4. Giai đoạn 2: Hành động của Lenders (Kiểm tra sức khỏe bể, nạp/rút tiền)
        for l in self.lenders:
            l.step()

        # 5. Giai đoạn 3: Hành động của Liquidators (Xáo trộn thứ tự theo seed, quét và thanh lý)
        shuffled_liquidators = list(self.liquidators)
        self.random.shuffle(shuffled_liquidators)
        for liq in shuffled_liquidators:
            liq.step()

        # 6. Giai đoạn 4: Bể xử lý hàng chờ rút tiền với cash mới
        self.pool.process_withdrawal_queue(self.current_step, self.lenders_dict)
        if self.pool.total_pending_withdrawals > 0 and (self.current_step % 12 == 0 or self.current_step == 25):
            self.event_logs.append(
                f"⏳ [Giờ {self.current_step:03d}] Bể cạn thanh khoản! Hàng chờ rút kẹt ${self.pool.total_pending_withdrawals:,.0f} USDC (Utilization: {self.pool.utilization_rate*100:.1f}%)"
            )

        # 7. Thu thập dữ liệu cuối bước
        self.datacollector.collect(self)
        self.current_step += 1

    def run_simulation(self, steps: int = 168) -> pd.DataFrame:
        """Chạy toàn bộ 168 bước và trả về DataFrame kết quả."""
        for _ in range(steps):
            self.step()
        return self.datacollector.get_model_vars_dataframe()
