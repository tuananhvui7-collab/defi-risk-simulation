"""
abm/protocol.py — Lớp Giao thức Cho vay (Protocol Engine)
Quản lý trạng thái Bể cho vay (LendingPool), Lãi suất có điểm gãy (Kink Model),
Hàng chờ rút tiền (Withdrawal Queue) và Xã hội hóa Nợ xấu (Bad Debt Socialization).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class WithdrawalRequest:
    lender_id: int
    amount_usdc: float
    requested_step: int


class KinkInterestRateModel:
    """
    Mô hình Lãi suất hai đoạn (Kink / Two-slope Model) chuẩn Aave V3.
    - Base Rate: 0.00%
    - Slope 1: 4.00% (0.04)
    - Slope 2: 75.00% (0.75)
    - Optimal Utilization (U_opt): 80.00% (0.80)
    - Reserve Factor: 10.00% (0.10)
    """

    def __init__(
        self,
        base_rate: float = 0.00,
        slope1: float = 0.04,
        slope2: float = 0.75,
        u_opt: float = 0.80,
        reserve_factor: float = 0.10
    ):
        self.base_rate = base_rate
        self.slope1 = slope1
        self.slope2 = slope2
        self.u_opt = u_opt
        self.reserve_factor = reserve_factor

    def compute_rates(self, total_cash: float, total_debt: float):
        """Tính toán lãi suất vay và gửi hàng năm (APR)."""
        if total_debt <= 0:
            return 0.0, 0.0, 0.0

        total_liquidity = total_cash + total_debt
        utilization = total_debt / total_liquidity if total_liquidity > 0 else 0.0

        if utilization <= self.u_opt:
            borrow_rate = self.base_rate + (utilization / self.u_opt) * self.slope1
        else:
            excess = utilization - self.u_opt
            excess_range = 1.0 - self.u_opt
            borrow_rate = self.base_rate + self.slope1 + (excess / excess_range) * self.slope2

        supply_rate = utilization * borrow_rate * (1.0 - self.reserve_factor)
        return utilization, borrow_rate, supply_rate


class ProtocolPool:
    """
    Quản lý tài sản và bù trừ tài chính của Lending Pool trong suốt 168 bước.
    """

    def __init__(
        self,
        close_factor: float = 0.50,
        liquidation_threshold: float = 0.80,
        liquidation_bonus: float = 0.05,
        min_liquidity_reserve_pct: float = 0.0,
        ir_model: Optional[KinkInterestRateModel] = None
    ):
        self.close_factor = close_factor
        self.liquidation_threshold = liquidation_threshold
        self.liquidation_bonus = liquidation_bonus
        self.min_liquidity_reserve_pct = min_liquidity_reserve_pct
        self.ir_model = ir_model or KinkInterestRateModel()

        # Tổng hợp số dư của giao thức
        self.total_collateral_eth = 0.0
        self.total_debt_usdc = 0.0
        # Debt demand without a modeled borrower/collateral position (e.g. S3).
        self.exogenous_debt_usdc = 0.0
        self.total_supply_usdc = 0.0
        self.total_cash_usdc = 0.0
        self.total_bad_debt_usdc = 0.0

        # Hàng chờ rút tiền
        self.withdrawal_queue: List[WithdrawalRequest] = []
        self.total_pending_withdrawals = 0.0
        self.completed_withdrawals_count = 0
        self.total_withdrawal_delay_steps = 0
        self.total_withdrawal_requested_usdc = 0.0
        self.total_withdrawal_fulfilled_usdc = 0.0
        self.queued_withdrawal_requests_count = 0
        self.completed_queued_withdrawals_count = 0
        self.total_queued_withdrawal_delay_steps = 0

    @property
    def utilization_rate(self) -> float:
        total = self.total_cash_usdc + self.total_debt_usdc
        return self.total_debt_usdc / total if total > 0 else 0.0

    def accrue_interest_step(self):
        """
        Cộng dồn lãi suất cho 1 bước thời gian (1 giờ = 1 / 8760 năm).
        """
        u, r_borrow, r_supply = self.ir_model.compute_rates(self.total_cash_usdc, self.total_debt_usdc)
        dt_year = 1.0 / 8760.0

        # Lãi nợ phát sinh
        debt_interest = self.total_debt_usdc * (r_borrow * dt_year)
        self.total_debt_usdc += debt_interest
        self.exogenous_debt_usdc += self.exogenous_debt_usdc * (r_borrow * dt_year)

        # Lãi tiền gửi phát sinh
        supply_interest = self.total_supply_usdc * (r_supply * dt_year)
        self.total_supply_usdc += supply_interest

        return u, r_borrow, r_supply

    def add_exogenous_borrow_demand(self, amount: float) -> float:
        """Move available cash into uncollateralized external debt demand."""
        actual = min(max(0.0, amount), max(0.0, self.total_cash_usdc))
        if actual:
            self.total_cash_usdc -= actual
            self.total_debt_usdc += actual
            self.exogenous_debt_usdc += actual
        return actual

    def queue_withdrawal(self, lender_id: int, amount: float, current_step: int) -> float:
        """
        Xử lý yêu cầu rút tiền của Lender:
        - Đáp ứng tối đa bằng cash khả dụng (sau khi trừ dự trữ tối thiểu).
        - Phần thiếu hụt xếp vào hàng chờ.
        """
        amount = max(0.0, float(amount))
        self.total_withdrawal_requested_usdc += amount
        min_reserve = self.total_supply_usdc * self.min_liquidity_reserve_pct
        available_cash = max(0.0, self.total_cash_usdc - min_reserve)

        if amount <= available_cash:
            # Đáp ứng đủ 100% ngay lập tức
            self.total_cash_usdc -= amount
            self.total_supply_usdc -= amount
            self.total_withdrawal_fulfilled_usdc += amount
            self.completed_withdrawals_count += 1
            return amount
        else:
            # Đáp ứng một phần
            fulfilled = available_cash
            unfulfilled = amount - fulfilled
            
            self.total_cash_usdc -= fulfilled
            self.total_supply_usdc -= fulfilled
            self.total_withdrawal_fulfilled_usdc += fulfilled

            # Đưa phần còn lại vào queue
            req = WithdrawalRequest(lender_id=lender_id, amount_usdc=unfulfilled, requested_step=current_step)
            self.withdrawal_queue.append(req)
            self.total_pending_withdrawals += unfulfilled
            self.queued_withdrawal_requests_count += 1
            return fulfilled

    def process_withdrawal_queue(self, current_step: int, lenders_dict: Dict[int, Any]):
        """
        Thanh toán hàng chờ rút tiền (FIFO) khi có dòng tiền nạp hoặc trả nợ mới.
        """
        min_reserve = self.total_supply_usdc * self.min_liquidity_reserve_pct
        available_cash = max(0.0, self.total_cash_usdc - min_reserve)

        while self.withdrawal_queue and available_cash > 0:
            req = self.withdrawal_queue[0]
            if req.amount_usdc <= available_cash:
                payout = req.amount_usdc
                self.total_cash_usdc -= payout
                self.total_supply_usdc -= payout
                available_cash -= payout
                self.total_pending_withdrawals = max(0.0, self.total_pending_withdrawals - payout)
                self.total_withdrawal_fulfilled_usdc += payout

                delay = current_step - req.requested_step
                self.total_withdrawal_delay_steps += delay
                self.total_queued_withdrawal_delay_steps += delay
                self.completed_queued_withdrawals_count += 1
                self.completed_withdrawals_count += 1

                # Cập nhật số dư lender
                if req.lender_id in lenders_dict:
                    lenders_dict[req.lender_id].pending_withdrawal -= payout

                self.withdrawal_queue.pop(0)
            else:
                payout = available_cash
                self.total_cash_usdc -= payout
                self.total_supply_usdc -= payout
                req.amount_usdc -= payout
                self.total_pending_withdrawals = max(0.0, self.total_pending_withdrawals - payout)
                self.total_withdrawal_fulfilled_usdc += payout
                available_cash = 0.0

                if req.lender_id in lenders_dict:
                    lenders_dict[req.lender_id].pending_withdrawal -= payout
                break

    @property
    def withdrawal_fulfillment_rate(self) -> float:
        if self.total_withdrawal_requested_usdc <= 0:
            return 1.0
        return min(1.0, self.total_withdrawal_fulfilled_usdc / self.total_withdrawal_requested_usdc)

    def average_fulfilled_withdrawal_delay(self) -> float:
        if self.completed_withdrawals_count == 0:
            return 0.0
        return self.total_withdrawal_delay_steps / self.completed_withdrawals_count

    def average_all_queued_withdrawal_wait(self, current_step: int) -> float:
        """Average wait for every request that entered the queue, including pending requests."""
        if self.queued_withdrawal_requests_count == 0:
            return 0.0
        pending_wait = sum(max(0, current_step - req.requested_step) for req in self.withdrawal_queue)
        total_wait = self.total_queued_withdrawal_delay_steps + pending_wait
        return total_wait / self.queued_withdrawal_requests_count

    def socialize_bad_debt(self, bad_debt_amount: float, lenders_dict: Dict[int, Any]):
        """
        Xã hội hóa nợ xấu loại I:
        Trừ trực tiếp vào số dư của các Lender theo tỷ lệ tiền gửi (Haircut).
        """
        if bad_debt_amount <= 0 or self.total_supply_usdc <= 0:
            return

        self.total_bad_debt_usdc += bad_debt_amount
        haircut_ratio = min(1.0, bad_debt_amount / self.total_supply_usdc)

        for lender in lenders_dict.values():
            loss = lender.deposited_usdc * haircut_ratio
            lender.deposited_usdc -= loss
            lender.realized_loss += loss

        self.total_supply_usdc = max(0.0, self.total_supply_usdc - bad_debt_amount)
        if self.total_cash_usdc >= bad_debt_amount:
            self.total_cash_usdc -= bad_debt_amount
        else:
            self.total_cash_usdc = 0.0
