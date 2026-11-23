"""
abm/market.py — Lớp Môi trường Thị trường (Market Environment)
Quản lý chuỗi giá ETH 168 giờ, chi phí gas và hàm trượt giá DEX phi tuyến.
"""

import os
import math
import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


class MarketEnvironment:
    """
    Quản lý điều kiện thị trường cho 168 bước thời gian (1 bước = 1 giờ = 7 ngày).
    Tích hợp dữ liệu nến 1h Binance Vision thực tế và hàm trượt giá DEX theo Chaudhary & Pinna (2022).
    """

    def __init__(
        self,
        scenario_id: str = "S0",
        base_price: float = 2000.0,
        historical_csv: str = "eth_usdt_168h_active.csv",
        gamma: float = 0.003, # 0.3% phí swap cơ sở sàn DEX
        omega: float = 1.0,   # bậc hàm trượt giá
        seed: int = 42
    ):
        self.scenario_id = scenario_id
        self.base_price = base_price
        self.gamma = gamma
        self.omega = omega
        self.seed = seed

        # Đọc dữ liệu lịch sử nến 1h
        csv_path = os.path.join(DATA_DIR, historical_csv)
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            # Lấy chuỗi giá chuẩn hóa về mốc 2.000$ (giữ nguyên tỷ lệ % biến động)
            if "price_norm_2000" in df.columns:
                self.raw_prices = df["price_norm_2000"].values[:168]
            else:
                self.raw_prices = (df["close"].values[:168] / df["close"].iloc[0]) * base_price
        else:
            # Fallback nếu chưa có file: sinh chuỗi giá ngẫu nhiên hình học
            np.random.seed(seed)
            returns = np.random.normal(0.0, 0.03, 168)
            self.raw_prices = base_price * np.exp(np.cumsum(returns))

        # Thiết lập các kịch bản S0 - S5
        self.prices, self.gas_fees, self.slippage_s, self.slippage_v = self._build_scenario_curves()

    def _build_scenario_curves(self):
        """
        Tạo đường giá, phí gas và thông số trượt giá cho 168 bước theo kịch bản S0–S5.
        """
        prices = np.copy(self.raw_prices)
        gas_fees = np.full(168, 10.0)             # Mặc định 10 USD/tx
        slippage_s = np.full(168, 1.0)           # s = 1.0
        slippage_v = np.full(168, 1_000_000_000.0) # V = 1 tỷ USD

        # S0: Cơ sở (Baseline) - Giữ nguyên đường giá lịch sử

        # S1: Cú sốc giá - Giảm 43% trong 24 bước từ bước 24
        if self.scenario_id in ["S1", "S5"]:
            start_step = 24
            duration = 24
            target_drop = 0.43 # 43% drop
            p_start = prices[start_step]
            p_target = p_start * (1 - target_drop)
            
            for t in range(start_step, start_step + duration):
                alpha = (t - start_step + 1) / duration
                prices[t] = p_start * (1 - alpha * target_drop)
            # Sau cú sốc giữ ở mức thấp
            for t in range(start_step + duration, 168):
                prices[t] = min(prices[t], p_target)

        # S4: Cú sốc chi phí vận hành - Gas 100 USD, trượt giá s*5, V*0.1, ETH giảm 25%
        if self.scenario_id in ["S4", "S5"]:
            gas_fees[:] = 100.0 # Gas tăng vọt 100 USD/tx
            slippage_s[:] = 5.0 # Hệ số trượt giá tăng gấp 5
            slippage_v[:] = 100_000_000.0 # Độ sâu thị trường co hẹp về 100 triệu USD

            if self.scenario_id == "S4":
                # S4 có giá giảm 25% trong 24 bước từ bước 24
                start_step = 24
                duration = 24
                target_drop = 0.25
                p_start = prices[start_step]
                for t in range(start_step, start_step + duration):
                    alpha = (t - start_step + 1) / duration
                    prices[t] = p_start * (1 - alpha * target_drop)
                for t in range(start_step + duration, 168):
                    prices[t] = min(prices[t], p_start * (1 - target_drop))

        return prices, gas_fees, slippage_s, slippage_v

    def get_market_state(self, step: int):
        """Trả về thông số thị trường tại bước thời gian step (0 <= step < 168)."""
        idx = min(step, 167)
        return {
            "step": idx,
            "eth_price": float(self.prices[idx]),
            "gas_fee_usd": float(self.gas_fees[idx]),
            "slippage_s": float(self.slippage_s[idx]),
            "slippage_v": float(self.slippage_v[idx]),
            "gamma": self.gamma,
            "omega": self.omega
        }

    def compute_slippage(self, trade_size_usd: float, step: int) -> float:
        """
        Tính trượt giá khi Liquidator bán ra trade_size_usd tài sản thế chấp ETH:
        sigma = gamma + s * (x / V)**omega
        """
        if trade_size_usd <= 0:
            return 0.0
        m = self.get_market_state(step)
        ratio = trade_size_usd / m["slippage_v"]
        sigma = m["gamma"] + m["slippage_s"] * (ratio ** m["omega"])
        # Giới hạn trượt giá tối đa 50% để tránh giá trị âm phi lý
        return min(sigma, 0.50)
