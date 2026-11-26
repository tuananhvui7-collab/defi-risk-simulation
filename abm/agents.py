"""
abm/agents.py — Định nghĩa 3 Tác nhân Đa tác nhân (Mesa Agent)
BorrowerAgent, LenderAgent, LiquidatorAgent với chiến lược Cố định (Fixed) và Thích nghi (Adaptive).
"""

import math
import mesa
import numpy as np


class BorrowerAgent(mesa.Agent):
    """
    Tác nhân Người vay (Borrower):
    - Thế chấp ETH, vay USDC từ bể.
    - Duy trì vị thế an toàn qua chỉ số Health Factor (HF).
    """

    def __init__(
        self,
        model: mesa.Model,
        collateral_eth: float,
        debt_usdc: float,
        risk_appetite: float, # RA ~ Beta(2, 2) in [0, 1]
        strategy: str = "fixed", # 'fixed' hoặc 'adaptive'
        h_fixed: float = 1.10
    ):
        super().__init__(model)
        self.collateral_eth = collateral_eth
        self.debt_usdc = debt_usdc
        self.risk_appetite = risk_appetite
        self.strategy = strategy.lower()
        self.h_fixed = h_fixed

        # Quỹ tiền mặt dự phòng tự vệ khẩn cấp (Emergency Cash Cushion)
        # Fixed: cố định 25% dư nợ ban đầu
        # Adaptive: dự phòng tỷ lệ nghịch với RA (người thận trọng RA thấp giữ nhiều tiền mặt hơn)
        if self.strategy == "fixed":
            self.emergency_cash = debt_usdc * 0.25
        else:
            self.emergency_cash = debt_usdc * (0.15 + 0.25 * (1.0 - risk_appetite))

        self.times_liquidated = 0
        self.is_liquidated = False
        self.shortfall = 0.0
        self.ever_undercollateralized = False

    def health_factor(self, eth_price: float, lt: float) -> float:
        if self.debt_usdc <= 0:
            return float("inf")
        col_val = self.collateral_eth * eth_price
        return (col_val * lt) / self.debt_usdc

    def step(self):
        if self.debt_usdc <= 0 or self.collateral_eth <= 0:
            return

        pool = self.model.pool
        m_state = self.model.market.get_market_state(self.model.current_step)
        eth_price = m_state["eth_price"]
        gas_fee = m_state["gas_fee_usd"]
        lt = pool.liquidation_threshold

        hf = self.health_factor(eth_price, lt)

        # -------------------------------------------------------------
        # 1. CHIẾN LƯỢC CỐ ĐỊNH (FIXED)
        # -------------------------------------------------------------
        if self.strategy == "fixed":
            # Nếu HF < h_fixed: tự vệ bằng cách trả nợ từ quỹ dự phòng (tối đa 25% dư nợ)
            if hf < self.h_fixed and self.emergency_cash > 0:
                desired_repay = self.debt_usdc * 0.25
                actual_repay = min(desired_repay, self.emergency_cash)
                self.emergency_cash -= actual_repay

                self.debt_usdc -= actual_repay
                pool.total_debt_usdc = max(0.0, pool.total_debt_usdc - actual_repay)
                pool.total_cash_usdc += actual_repay

        # -------------------------------------------------------------
        # 2. CHIẾN LƯỢC THÍCH NGHI (ADAPTIVE)
        # -------------------------------------------------------------
        else:
            h_min = 1.30 - 0.25 * self.risk_appetite
            h_target = 1.60 - 0.25 * self.risk_appetite

            history_prices = self.model.price_history
            recent_drop = 0.0
            if len(history_prices) >= 3:
                recent_drop = (history_prices[-1] - history_prices[-3]) / history_prices[-3]

            needs_defense = (hf < h_min) or (recent_drop < -0.05 and hf < 1.40)

            if needs_defense and self.emergency_cash > 0:
                expected_penalty = pool.close_factor * self.debt_usdc * pool.liquidation_bonus
                if expected_penalty > gas_fee:
                    target_debt = (self.collateral_eth * eth_price * lt) / h_target
                    if self.debt_usdc > target_debt:
                        desired_repay = self.debt_usdc - target_debt
                        actual_repay = min(desired_repay, self.emergency_cash)
                        self.emergency_cash -= actual_repay

                        self.debt_usdc -= actual_repay
                        pool.total_debt_usdc = max(0.0, pool.total_debt_usdc - actual_repay)
                        pool.total_cash_usdc += actual_repay

            elif hf > 2.20 and recent_drop >= 0.0:
                if self.model.random.random() < (0.10 * self.risk_appetite):
                    add_borrow = self.debt_usdc * 0.15
                    if pool.total_cash_usdc >= add_borrow:
                        self.debt_usdc += add_borrow
                        pool.total_debt_usdc += add_borrow
                        pool.total_cash_usdc -= add_borrow


class LenderAgent(mesa.Agent):
    """
    Tác nhân Người gửi tiền (Lender):
    - Cung cấp thanh khoản USDC vào bể để hưởng lãi suất.
    - Ra quyết định rút vốn khi nhận thấy rủi ro (Utilization cao, phát sinh nợ xấu).
    """

    def __init__(
        self,
        model: mesa.Model,
        deposited_usdc: float,
        risk_appetite: float,
        strategy: str = "fixed",
        r_benchmark: float = 0.02 # 2% APY benchmark rate
    ):
        super().__init__(model)
        self.deposited_usdc = deposited_usdc
        self.risk_appetite = risk_appetite
        self.strategy = strategy.lower()
        self.r_benchmark = r_benchmark

        self.pending_withdrawal = 0.0
        self.realized_loss = 0.0

    def step(self):
        if self.deposited_usdc <= 0 or self.strategy == "fixed":
            # Chiến lược Fixed: thụ động nắm giữ tiền gửi suốt 168 bước
            return

        pool = self.model.pool
        u = pool.utilization_rate
        has_bad_debt = pool.total_bad_debt_usdc > 0
        _, _, r_supply = pool.ir_model.compute_rates(pool.total_cash_usdc, pool.total_debt_usdc)

        # Tính xác suất tháo chạy rút vốn (Run on pool)
        # RA thấp (thận trọng) sẽ nhạy cảm và rút vốn nhanh hơn
        run_prob = 0.0

        if u > pool.ir_model.u_opt:
            run_prob += (u - pool.ir_model.u_opt) * (2.0 - self.risk_appetite)
        if has_bad_debt:
            run_prob += 0.30 * (1.5 - self.risk_appetite)
        if r_supply < self.r_benchmark:
            run_prob += 0.05

        if self.model.random.random() < min(run_prob, 0.80):
            # Quyết định rút 30% - 60% tiền gửi
            withdraw_pct = 0.30 + 0.30 * (1.0 - self.risk_appetite)
            withdraw_amt = self.deposited_usdc * withdraw_pct

            fulfilled = pool.queue_withdrawal(self.unique_id, withdraw_amt, self.model.current_step)
            self.deposited_usdc -= withdraw_amt
            self.pending_withdrawal += (withdraw_amt - fulfilled)


class LiquidatorAgent(mesa.Agent):
    """
    Tác nhân Người thanh lý (Liquidator):
    - Giám sát các vị thế có HF < 1.0.
    - Thanh lý vị thế, trả nợ USDC và thu hồi ETH thế chấp kèm Bonus.
    - Bán ETH ra sàn DEX với hàm trượt giá phi tuyến để chốt lời ròng.
    """

    def __init__(
        self,
        model: mesa.Model,
        capital_usdc: float,
        risk_appetite: float,
        strategy: str = "fixed"
    ):
        super().__init__(model)
        self.capital_usdc = capital_usdc
        self.risk_appetite = risk_appetite
        self.strategy = strategy.lower()

        self.total_profit_usd = 0.0
        self.liquidations_count = 0

    def step(self):
        if self.capital_usdc <= 0:
            return

        pool = self.model.pool
        m_state = self.model.market.get_market_state(self.model.current_step)
        eth_price = m_state["eth_price"]
        gas_fee = m_state["gas_fee_usd"]
        lt = pool.liquidation_threshold

        # Tìm các Borrower có HF < 1.0 chưa bị thanh lý hết
        eligible_borrowers = [
            b for b in self.model.borrowers
            if b.debt_usdc > 0 and b.collateral_eth > 0 and b.health_factor(eth_price, lt) < 1.0
        ]

        if not eligible_borrowers:
            return

        # -------------------------------------------------------------
        # 1. CHIẾN LƯỢC CỐ ĐỊNH (FIXED)
        # -------------------------------------------------------------
        if self.strategy == "fixed":
            # Chọn vị thế vi phạm đầu tiên
            target = eligible_borrowers[0]
            max_repay = target.debt_usdc * pool.close_factor
            actual_repay = min(max_repay, self.capital_usdc)

            if actual_repay <= 0:
                return

            # Ước tính lợi nhuận gộp với gas tĩnh
            bonus_val = actual_repay * pool.liquidation_bonus
            if bonus_val > gas_fee:
                self._execute_liquidation(target, actual_repay, eth_price, gas_fee, pool)

        # -------------------------------------------------------------
        # 2. CHIẾN LƯỢC THÍCH NGHI (ADAPTIVE)
        # -------------------------------------------------------------
        else:
            # Quét toàn bộ vị thế đủ điều kiện, tính lợi nhuận ròng sau trượt giá DEX
            candidates = []
            for b in eligible_borrowers:
                max_repay = b.debt_usdc * pool.close_factor
                repay = min(max_repay, self.capital_usdc)
                if repay <= 0:
                    continue

                # Lượng ETH nhận được
                eth_bonus_val = repay * (1.0 + pool.liquidation_bonus)
                eth_seized = min(b.collateral_eth, eth_bonus_val / eth_price)

                # Giá trị bán trên DEX sau trượt giá
                trade_size_usd = eth_seized * eth_price
                slippage = self.model.market.compute_slippage(trade_size_usd, self.model.current_step)
                net_sale_usd = trade_size_usd * (1.0 - slippage)

                expected_net_profit = (net_sale_usd - repay) - gas_fee
                if expected_net_profit > 0:
                    candidates.append((expected_net_profit, b, repay))

            if candidates:
                # Sắp xếp chọn vị thế có lợi nhuận ròng cao nhất
                candidates.sort(key=lambda x: x[0], reverse=True)
                best_profit, target, actual_repay = candidates[0]
                self._execute_liquidation(target, actual_repay, eth_price, gas_fee, pool)

    def _execute_liquidation(
        self,
        borrower: BorrowerAgent,
        repay_amount: float,
        eth_price: float,
        gas_fee: float,
        pool
    ):
        """Thực thi nghiệp vụ thanh lý và bù trừ tài chính."""
        eth_seize_val = repay_amount * (1.0 + pool.liquidation_bonus)
        ideal_eth_seized = eth_seize_val / eth_price

        bad_debt = 0.0
        if ideal_eth_seized >= borrower.collateral_eth:
            # Thế chấp cạn kiệt -> Phát sinh nợ xấu
            actual_eth_seized = borrower.collateral_eth
            recovered_usd = actual_eth_seized * eth_price
            if repay_amount > recovered_usd:
                bad_debt = repay_amount - recovered_usd
        else:
            actual_eth_seized = ideal_eth_seized

        # Bán ETH trên sàn DEX
        trade_usd = actual_eth_seized * eth_price
        slippage = self.model.market.compute_slippage(trade_usd, self.model.current_step)
        dex_revenue = trade_usd * (1.0 - slippage)

        net_profit = (dex_revenue - repay_amount) - gas_fee
        self.capital_usdc += net_profit
        self.total_profit_usd += net_profit
        self.liquidations_count += 1

        # Cập nhật Borrower
        borrower.debt_usdc = max(0.0, borrower.debt_usdc - repay_amount)
        borrower.collateral_eth = max(0.0, borrower.collateral_eth - actual_eth_seized)
        borrower.times_liquidated += 1
        if borrower.collateral_eth <= 0:
            borrower.is_liquidated = True

        # Cập nhật Pool
        pool.total_debt_usdc = max(0.0, pool.total_debt_usdc - repay_amount)
        pool.total_collateral_eth = max(0.0, pool.total_collateral_eth - actual_eth_seized)
        pool.total_cash_usdc += repay_amount

        # Xã hội hóa nợ xấu nếu có
        if bad_debt > 0:
            pool.socialize_bad_debt(bad_debt, self.model.lenders_dict)
            self.model.bad_debt_events.append({
                "step": self.model.current_step,
                "amount": bad_debt
            })
            if hasattr(self.model, "event_logs"):
                self.model.event_logs.append(
                    f"💥 [Giờ {self.model.current_step:03d}] VỠ NỢ! Phát sinh ${bad_debt:,.1f} USDC nợ xấu (Khấu trừ vốn Lender)"
                )
        else:
            if hasattr(self.model, "event_logs"):
                self.model.event_logs.append(
                    f"⚡ [Giờ {self.model.current_step:03d}] Liquidator thanh lý Borrower #{borrower.unique_id}: Trả ${repay_amount:,.0f} nợ, tịch thu {actual_eth_seized:.2f} ETH (Lãi ròng: +${net_profit:,.1f})"
                )
