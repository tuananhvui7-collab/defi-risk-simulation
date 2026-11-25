"""
contract/feed_oracle_real_data.py — Nạp Dữ Liệu Giá ETH Thật từ Binance vào Smart Contract
Dành cho: Chạy thực tế trên Ethereum Sepolia Testnet.

Chức năng:
1. Đọc dữ liệu nến 1h lịch sử thật từ file: data/eth_usdt_168h_may2021.csv (hoặc active.csv).
2. Chuẩn hóa giá sang định dạng Chainlink 8 chữ số thập phân (e.g. $3,465.98 -> 346598000000).
3. Gửi giao dịch cập nhật giá thực tế (setEthPrice) vào Smart Contract MockPriceOracle trên Sepolia.
4. Có thể bật chế độ Chainlink Live Oracle trực tiếp từ mạng Sepolia: setUseChainlinkLive(true).
"""

import os
import sys
import time
import pandas as pd

# Đường dẫn file dữ liệu
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "eth_usdt_168h_may2021.csv")


def load_real_eth_prices(csv_path: str = DATA_PATH) -> list:
    """Đọc và chuẩn hóa chuỗi giá ETH thật từ Binance."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Không tìm thấy file dữ liệu: {csv_path}")

    df = pd.read_csv(csv_path)
    prices = []
    for idx, row in df.iterrows():
        close_p = float(row["close"])
        # Chainlink chuẩn 8 decimals: nhân 10^8
        price_8dec = int(round(close_p * 10**8))
        prices.append({
            "step": int(row["step"]),
            "timestamp": row.get("timestamp", ""),
            "price_usd": close_p,
            "price_chainlink_8dec": price_8dec
        })
    return prices


def print_oracle_feeder_guide():
    """In hướng dẫn nạp dữ liệu thật lên Sepolia Testnet."""
    prices = load_real_eth_prices()
    p0 = prices[0]
    p_min = min(prices, key=lambda x: x["price_usd"])

    print("==================================================================")
    print("📡 DEFI LENDING ORACLE REAL DATA FEEDER (BINANCE VISION -> SEPOLIA)")
    print("==================================================================")
    print(f"Tổng số nến 1h thực tế sẵn sàng nạp: {len(prices)} bước (168 giờ)")
    print(f"Giá bắt đầu (Giờ 0): ${p0['price_usd']:,.2f} -> Value on contract: {p0['price_chainlink_8dec']}")
    print(f"Giá đáy sụp đổ (Giờ {p_min['step']}): ${p_min['price_usd']:,.2f} -> Value on contract: {p_min['price_chainlink_8dec']}")
    print("------------------------------------------------------------------")
    print("💡 Hai phương án cập nhật dữ liệu thật trên Sepolia Testnet:")
    print("   1. DÙNG CHAINLINK LIVE FEED (Khuyến nghị khi demo thực tế):")
    print("      Gọi hàm trên contract MockPriceOracle:")
    print("      -> setUseChainlinkLive(true)")
    print("      Hợp đồng sẽ tự động đọc trực tiếp giá ETH thật từ mạng lưới Chainlink:")
    print("      Aggregator Address: 0x694AA1769357215DE4FAC081bf1f309aDC325306")
    print("")
    print("   2. NẠP CHUỖI NẾN SỤP ĐỔ 168H LỊCH SỬ TỪ BINANCE:")
    print("      Gọi hàm setEthPrice(price_chainlink_8dec) theo từng giờ.")
    print("      Ví dụ giờ sụp đổ:")
    print(f"      contract.setEthPrice({p_min['price_chainlink_8dec']})")
    print("==================================================================")


if __name__ == "__main__":
    print_oracle_feeder_guide()
