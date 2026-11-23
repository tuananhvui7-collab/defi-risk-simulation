"""
data/fetch_binance_data.py — Tải và chuẩn hóa chuỗi dữ liệu 168 nến 1h của ETHUSDT từ Binance
Phục vụ đề tài: Nghiên cứu khả năng chống chịu rủi ro của giao thức cho vay DeFi.

Các giai đoạn lịch sử mẫu (Cú sốc cực đoan trong DeFi):
1. MAY_2021 (17/05/2021 - 23/05/2021): Đợt sụp đổ tháng 5/2021 (ETH giảm ~50% trong tuần, kích hoạt thanh lý kỷ lục trên Aave & Compound).
2. NOV_2022 (06/11/2022 - 12/11/2022): Cú sụp đổ FTX (ETH giảm ~34%, khủng hoảng thanh khoản liên thị trường).
3. MAR_2020 (12/03/2020 - 18/03/2020): Thứ Năm Đen Tối - Black Thursday (ETH giảm ~43% trong 1 ngày, theo nghiên cứu của Qin et al. 2021).
"""

import os
import json
import math
import datetime
import urllib.request
import pandas as pd
import numpy as np

# Thư mục lưu dữ liệu
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

PRESETS = {
    "MAY_2021": {
        "name": "Đợt sụp đổ tháng 5/2021 (Black Wednesday)",
        "start_utc": "2021-05-17 00:00:00",
        "description": "ETH sụt giảm từ ~3.465$ về ~1.728$ (-50.1%), gây ra đợt thanh lý kỷ lục trong lịch sử DeFi.",
        "filename": "eth_usdt_168h_may2021.csv"
    },
    "NOV_2022": {
        "name": "Khủng hoảng thanh khoản FTX (Tháng 11/2022)",
        "start_utc": "2022-11-06 00:00:00",
        "description": "ETH giảm từ ~1.629$ về ~1.073$ (-34.1%), thanh khoản cạn kiệt và xuất hiện rút vốn ồ ạt.",
        "filename": "eth_usdt_168h_ftx2022.csv"
    },
    "MAR_2020": {
        "name": "Thứ Năm Đen Tối (Black Thursday 2020 - Qin et al.)",
        "start_utc": "2020-03-12 00:00:00",
        "description": "ETH giảm 43% trong 1 ngày (13/3/2020) và giảm >55% cả tuần, cơ sở thực nghiệm cho bài báo của Qin et al.",
        "filename": "eth_usdt_168h_mar2020.csv"
    }
}


def fetch_binance_klines(symbol: str = "ETHUSDT", interval: str = "1h", start_time_ms: int = None, limit: int = 168):
    """
    Tải dữ liệu klines từ Binance Public API.
    Endpoint: https://api.binance.com/api/v3/klines
    """
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start_time_ms}&limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw_data = json.loads(resp.read().decode())
    
    records = []
    for step, item in enumerate(raw_data):
        # Format Binance: [OpenTime, Open, High, Low, Close, Volume, CloseTime, ...]
        open_time = datetime.datetime.fromtimestamp(item[0] / 1000, tz=datetime.timezone.utc)
        records.append({
            "step": step,
            "timestamp": open_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "timestamp_ms": item[0],
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
            "volume": float(item[5])
        })
    
    df = pd.DataFrame(records)
    return df


def process_and_compute_metrics(df: pd.DataFrame, base_price_norm: float = 2000.0) -> pd.DataFrame:
    """
    Tính toán các chỉ số thống kê thị trường:
    - Log return theo giờ: r_t = ln(P_t / P_{t-1})
    - Độ lệch chuẩn lợi suất theo giờ (Hourly Volatility: sigma_1h)
    - Độ biến động hàng năm hóa (Annualized Volatility: sigma_ann)
    - Chuỗi giá co giãn chuẩn hóa về mốc 2.000$ (phục vụ đối chiếu benchmark).
    """
    df["log_return"] = np.log(df["close"] / df["close"].shift(1)).fillna(0.0)
    
    # Chuỗi giá chuẩn hóa về mốc 2.000 USD (giữ nguyên tỷ lệ phần trăm thay đổi)
    p0 = df["close"].iloc[0]
    df["cumulative_return"] = df["close"] / p0
    df["price_norm_2000"] = base_price_norm * df["cumulative_return"]
    
    # Tính biến động
    hourly_vol = df["log_return"].std()
    annual_vol = hourly_vol * math.sqrt(8760)
    max_drop = (df["low"].min() - p0) / p0 * 100
    
    return df, hourly_vol, annual_vol, max_drop


def download_preset(preset_key: str = "MAY_2021", set_as_active: bool = True):
    preset = PRESETS.get(preset_key)
    if not preset:
        raise ValueError(f"Unknown preset {preset_key}. Available: {list(PRESETS.keys())}")
    
    start_dt = datetime.datetime.strptime(preset["start_utc"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
    start_ms = int(start_dt.timestamp() * 1000)
    
    print(f"📥 Đang tải 168 nến 1h cho kịch bản: {preset['name']}...")
    print(f"   Thời gian bắt đầu: {preset['start_utc']} UTC")
    
    df = fetch_binance_klines("ETHUSDT", "1h", start_ms, limit=168)
    df, hourly_vol, annual_vol, max_drop = process_and_compute_metrics(df)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    out_file = os.path.join(DATA_DIR, preset["filename"])
    df.to_csv(out_file, index=False)
    print(f"   ✅ Đã lưu {len(df)} dòng vào: {out_file}")
    print(f"   📊 Giá mở đầu P0: {df['close'].iloc[0]:.2f} USD")
    print(f"   📉 Giá thấp nhất:  {df['low'].min():.2f} USD (Mức giảm lớn nhất: {max_drop:.2f}%)")
    print(f"   📈 Biến động theo giờ (sigma_1h): {hourly_vol:.4f} ({hourly_vol*100:.2f}%/giờ)")
    print(f"   🌐 Biến động hàng năm hóa (sigma_ann): {annual_vol*100:.2f}%")
    
    if set_as_active:
        active_file = os.path.join(DATA_DIR, "eth_usdt_168h_active.csv")
        df.to_csv(active_file, index=False)
        print(f"   ⭐ Đã cập nhật làm chuỗi giá active tại: {active_file}")
        
        # Ghi metadata
        meta = {
            "preset_key": preset_key,
            "name": preset["name"],
            "description": preset["description"],
            "p0_actual": df["close"].iloc[0],
            "p_min_actual": df["low"].min(),
            "max_drop_pct": max_drop,
            "hourly_volatility": hourly_vol,
            "annualized_volatility": annual_vol,
            "num_steps": len(df)
        }
        with open(os.path.join(DATA_DIR, "active_meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=4, ensure_ascii=False)
            
    return df, hourly_vol


def download_all_presets():
    """Tải và lưu trữ cả 3 giai đoạn lịch sử để phục vụ so sánh đa kịch bản."""
    print("==================================================================")
    print("🚀 BẮT ĐẦU TẢI DỮ LIỆU LỊCH SỬ BINANCE VISION CHO DEFI RISK LAB")
    print("==================================================================")
    for key in PRESETS:
        download_preset(key, set_as_active=(key == "MAY_2021"))
        print("------------------------------------------------------------------")
    print("🎉 HOÀN THÀNH TẢI TOÀN BỘ 3 KỊCH BẢN THỰC TẾ!")


if __name__ == "__main__":
    download_all_presets()
