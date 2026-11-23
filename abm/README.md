# Hướng dẫn Mô hình Đa tác nhân (Mesa ABM) — DeFi Risk Lab

> **Đề tài:** Nghiên cứu khả năng chống chịu rủi ro của giao thức cho vay DeFi dưới tác động của biến động thị trường và hành vi tương tác giữa các tác nhân.  
> **Thư viện:** [Mesa 3.3+](https://mesa.readthedocs.io/) (Python Agent-Based Modeling Framework)  
> **Dữ liệu thị trường:** 168 nến 1h ETHUSDT lịch sử từ Binance Vision (`data/eth_usdt_168h_active.csv`)

---

## 1. Kiến trúc Hệ thống ABM 4 Lớp

Mô hình được tổ chức bài bản theo kiến trúc 4 lớp tương ứng với **Mục 3.5 của Báo cáo nghiên cứu**:

```
                              ┌─────────────────────────────────────────────────────────────┐
                              │     LỚP 4: ĐIỀU PHỐI MÔ PHỎNG & ĐO LƯỜNG (MODEL & RUNNER)   │
                              │  - DeFiLendingMesaModel (Vòng lặp 168 bước, DataCollector) │
                              │  - Runner: Chạy Ma trận 12 Thực nghiệm E1–E12 (Seed = 42)   │
                              └──────────────────────────────┬──────────────────────────────┘
                                                             │
                              ┌──────────────────────────────┴──────────────────────────────┐
                              │            LỚP 3: HÀNH VI ĐA TÁC NHÂN (AGENTS.PY)           │
                              │  - BorrowerAgent: Quản lý nợ/thế chấp, tự vệ khẩn cấp       │
                              │  - LenderAgent: Cung cấp thanh khoản, tháo chạy vốn         │
                              │  - LiquidatorAgent: Quét vị thế, thanh lý tối ưu sau trượt giá│
                              │  - Khẩu vị rủi ro: RA ~ Beta(2, 2) ∈ [0, 1]                 │
                              └──────────────────────────────┬──────────────────────────────┘
                                                             │
                              ┌──────────────────────────────┴──────────────────────────────┐
                              │          LỚP 2: QUY TẮC BỂ VAY & GIAO THỨC (PROTOCOL.PY)    │
                              │  - ProtocolPool: Quản lý Cash, Debt, Supply, Collateral     │
                              │  - KinkInterestRateModel: Lãi suất 2 đoạn (U_opt=80%)       │
                              │  - WithdrawalQueue: Hàng chờ rút tiền khi thanh khoản cạn   │
                              │  - BadDebtManager: Xã hội hóa nợ xấu loại I (Haircut)       │
                              └──────────────────────────────┬──────────────────────────────┘
                                                             │
                              ┌──────────────────────────────┴──────────────────────────────┐
                              │           LỚP 1: MÔI TRƯỜNG THỊ TRƯỜNG (MARKET.PY)          │
                              │  - Chuỗi giá ETH 168 giờ từ Binance Vision (May 2021)       │
                              │  - Mô hình chi phí Gas ($10 bình thường vs $100 nghẽn mạng) │
                              │  - Hàm trượt giá DEX phi tuyến: sigma = gamma + s*(x/V)^w   │
                              └─────────────────────────────────────────────────────────────┘
```

---

## 2. Quy tắc Hành vi Tác nhân (Cố định vs Thích nghi)

Mọi tác nhân đều có một chỉ số **Khẩu vị rủi ro (Risk Appetite - $RA$)** được lấy mẫu độc lập từ phân phối $\text{Beta}(2, 2)$ trên đoạn $[0, 1]$:
- $RA \approx 0$: Tác nhân cực kỳ thận trọng, nhạy cảm với rủi ro.
- $RA \approx 1$: Tác nhân liều lĩnh, chấp nhận rủi ro cao.

### 2.1. Tác nhân Người vay (`BorrowerAgent`)
- **Vị thế ban đầu:** Dư nợ ban đầu phân phối Lognormal (kỳ vọng 5.000 USD), $LTV$ ban đầu trung bình $0.60$ ($HF_{init} \approx 1.33$).
- **Quỹ tiền mặt tự vệ khẩn cấp:**
  - *Fixed:* Giữ tối đa 25% dư nợ ban đầu làm quỹ dự phòng.
  - *Adaptive:* Giữ lượng tiền mặt tỷ lệ nghịch với $RA$: $Debt \times (0.15 + 0.25 \times (1 - RA))$.
- **Chiến lược Cố định (Fixed):**
  - Không vay thêm. Nếu $HF < h_{fixed}$ (1.10), trả 25% dư nợ từ quỹ dự phòng. Khi quỹ cạn kiệt, vị thế chịu hoàn toàn biến động thị trường.
- **Chiến lược Thích nghi (Adaptive):**
  - Thiết lập ngưỡng an toàn động:
    $$h_{min}(RA) = 1.30 - 0.25 \times RA$$
    $$h_{target}(RA) = 1.60 - 0.25 \times RA$$
  - Theo dõi đà giá ETH trong 3 bước gần nhất. Nếu $HF < h_{min}$ hoặc giá giảm nhanh:
    - So sánh chi phí phạt thanh lý ($CloseFactor \times Debt \times Bonus$) với phí gas.
    - Nếu có lợi: Tự vệ đưa $HF$ về $h_{target}$ bằng cách trả nợ từ quỹ dự phòng.
  - Khi vị thế siêu an toàn ($HF > 2.20$) và thị trường ổn định: có xác suất vay thêm vốn (tỷ lệ thuận với $RA$).

### 2.2. Tác nhân Người gửi tiền (`LenderAgent`)
- Cung cấp thanh khoản USDC vào bể để hưởng lãi suất gửi $R_{supply}$.
- **Chiến lược Cố định (Fixed):** Nắm giữ thụ động trong suốt 168 bước, không nạp thêm và không rút vốn.
- **Chiến lược Thích nghi (Adaptive):**
  - Theo dõi tỷ lệ sử dụng vốn $U$, sự xuất hiện của nợ xấu trong bể, và lãi suất gửi thực tế $R_{supply}$.
  - Tính xác suất tháo chạy rút vốn (Bank-run):
    - Tăng mạnh khi $U > U_{opt}$ (lo sợ đóng băng thanh khoản).
    - Tăng khi xuất hiện nợ xấu (lo sợ bị phân bổ lỗ - Haircut).
    - Tác nhân $RA$ thấp (thận trọng) sẽ kích hoạt rút vốn sớm hơn.
  - Khi kích hoạt, gửi yêu cầu rút 30% – 60% số dư tiền gửi vào bể.

### 2.3. Tác nhân Người thanh lý (`LiquidatorAgent`)
- Nắm giữ nguồn vốn thanh khoản USDC để giải chấp các vị thế có $HF < 1.0$.
- **Chiến lược Cố định (Fixed):**
  - Quét tuần tự danh sách người vay.
  - Chọn vị thế vi phạm đầu tiên, trả tối đa 50% nợ (`Close Factor`).
  - Thực thi nếu lợi nhuận gộp từ thưởng 5% ETH lớn hơn phí gas tĩnh ($10).
- **Chiến lược Thích nghi (Adaptive):**
  - Quét toàn bộ vị thế vi phạm trên thị trường.
  - Với mỗi vị thế, tính toán lợi nhuận ròng thực tế sau khi trừ phí gas hiện tại và **trượt giá bán ETH trên sàn DEX**:
    $$\Pi_{net} = \left(CollateralSeized \times P_{sell} - RepaidDebt\right) - GasFee$$
    $$P_{sell} = P_{ETH} \times \left(1 - \sigma\left(TradeSize\right)\right)$$
  - Sắp xếp và ưu tiên thực thi các vị thế mang lại lợi nhuận ròng cao nhất.
  - Tạm hoãn thanh lý nếu trượt giá DEX hoặc gas làm $\Pi_{net} \le 0$.

---

## 3. Các Cơ chế Kinh tế Học Giao thức Cốt lõi

### 3.1. Mô hình Lãi suất Điểm gãy (Kink Model)
Tỷ lệ sử dụng vốn:
$$U = \frac{Debt}{Cash + Debt}$$
- Khi $U \le U_{opt}$ ($80\%$):
  $$R_{borrow} = Base (0\%) + \frac{U}{U_{opt}} \times Slope_1 (4\%)$$
- Khi $U > U_{opt}$:
  $$R_{borrow} = Base + Slope_1 + \frac{U - U_{opt}}{1 - U_{opt}} \times Slope_2 (75\%)$$
- Lãi suất người gửi:
  $$R_{supply} = U \times R_{borrow} \times (1 - ReserveFactor (10\%))$$
- **Cộng dồn liên tục theo giờ:** Mỗi bước 1 giờ, nợ và tiền gửi được tích lũy lãi kép: $\Delta t = \frac{1}{8760}$ năm.

### 3.2. Hàng chờ Rút tiền (Withdrawal Queue)
- Khi Lender yêu cầu rút $W$:
  - Nếu $W \le Cash_{khả dụng}$: Chi trả ngay lập tức.
  - Nếu $W > Cash_{khả dụng}$: Chi trả tối đa phần cash có sẵn, phần thiếu hụt được xếp vào hàng chờ (FIFO).
  - Khi có dòng tiền mới (người vay trả nợ, người thanh lý trả nợ, hoặc lender mới nạp tiền), hàng chờ được tự động thanh toán tuần tự.
- Chỉ số ghi nhận: Quy mô tiền rút bị kẹt (`pending_withdrawals_usdc`) và độ trễ chờ rút trung bình (`avg_withdrawal_delay_hours`).

### 3.3. Xã hội hóa Nợ xấu (Bad Debt Socialization)
- Khi thanh lý vị thế mà toàn bộ ETH thế chấp bị tịch thu vẫn không đủ bù đắp khoản nợ đã trả:
  $$BadDebt = RepayAmount - (Collateral_{rem} \times P_{ETH})$$
- Nợ xấu được ghi nhận vào `totalBadDebtUSDC` và khấu trừ trực tiếp vào số dư của các Lender theo tỷ lệ tiền gửi (Haircut).

### 3.4. Hàm Trượt giá Sàn DEX Phi tuyến (Chaudhary & Pinna 2022)
$$\sigma(x) = \gamma + s \times \left(\frac{x}{V}\right)^\omega$$
- $\gamma = 0.003$ (Phí swap cơ sở 0.3%).
- $\omega = 1.0$ (Bậc tuyến tính quy mô).
- Điều kiện bình thường (S0–S3): $s = 1.0, V = 1.000.000.000$ USD.
- Điều kiện sốc chi phí vận hành (S4, S5): $s = 5.0, V = 100.000.000$ USD (thị trường cạn kiệt thanh khoản, trượt giá tăng vọt).

---

## 4. Ma trận 12 Thực nghiệm (E1–E12) & Kết quả Kiểm chứng H1–H6

Ma trận thực nghiệm đối chứng chạy trên **cùng đường giá 168 giờ (Binance Vision May 2021)** với **`seed = 42`**:

| Mã TN | Kịch bản | Chiến lược | Tỷ lệ TL (%) | Số vị thế bị TL | Utilization max (%) | Lãi vay max (% APR) | Rút tiền bị kẹt (USDC) | Trễ rút TB (giờ) | Lợi nhuận Liquidator ($) | Giả thuyết kiểm chứng |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **E1** | **S0** (Cơ sở) | **Fixed** | **64.0%** | 64 | 60.00% | 3.00% | 0.00 | 0.00 | $4,997.28 | Đường cơ sở so sánh |
| **E2** | **S0** (Cơ sở) | **Adaptive** | **49.0%** | 49 | 67.56% | 3.38% | 0.00 | 0.00 | $3,826.23 | Đường cơ sở so sánh |
| **E3** | **S1** (Sốc giá -43%) | **Fixed** | **64.0%** | 64 | 60.00% | 3.00% | 0.00 | 0.00 | $4,892.59 | **Kiểm tra H1, H4** |
| **E4** | **S1** (Sốc giá -43%) | **Adaptive** | **50.0%** | 50 | 67.51% | 3.38% | 0.00 | 0.00 | $3,725.10 | **Kiểm tra H1, H4** (Adaptive giảm 14% tỷ lệ TL) |
| **E5** | **S2** (Sốc thanh khoản) | **Fixed** | 64.0% | 64 | 98.35% | 72.82% | 0.00 | 0.00 | $4,997.28 | **Kiểm tra H3** |
| **E6** | **S2** (Sốc thanh khoản) | **Adaptive** | 49.0% | 49 | **100.00%** | **79.00%** | **472,926.45** | **15.87 giờ** | $3,826.23 | **Kiểm tra H3** (Bank-run gây kẹt 472k USDC) |
| **E7** | **S3** (Sốc lãi suất) | **Fixed** | 64.0% | 64 | 90.01% | 41.52% | 0.00 | 0.00 | $4,997.28 | Chi phí vay & áp lực thanh khoản |
| **E8** | **S3** (Sốc lãi suất) | **Adaptive** | 49.0% | 49 | **100.00%** | **79.00%** | **351,109.41** | **18.86 giờ** | $3,826.23 | Chi phí vay & áp lực thanh khoản |
| **E9** | **S4** (Sốc chi phí) | **Fixed** | **2.0%** | 2 | 60.00% | 3.00% | 0.00 | 0.00 | **$21.34** | **Kiểm tra H2, H5** (Gas 100$ dập tắt thanh lý) |
| **E10** | **S4** (Sốc chi phí) | **Adaptive** | **11.0%** | 11 | 67.47% | 3.37% | 0.00 | 0.00 | **$298.09** | **Kiểm tra H2, H5** (Adaptive tìm kiếm được vị thế có lãi) |
| **E11** | **S5** (Sốc kết hợp) | **Fixed** | 2.0% | 2 | 80.15% | 4.56% | 0.00 | 0.00 | $21.34 | **Kiểm tra H5, H6** |
| **E12** | **S5** (Sốc kết hợp) | **Adaptive** | 11.0% | 11 | **100.00%** | **79.00%** | **589,918.05** | **4.83 giờ** | $288.56 | **Kiểm tra H5, H6** (Rủi ro hệ thống đạt đỉnh) |

---

## 5. Hướng dẫn Chạy & API Mã Nguồn

### 5.1. Chạy Ma trận Thực nghiệm E1–E12 từ dòng lệnh
```bash
python abm/runner.py
```
Kết quả sẽ tự động được ghi vào:
- `results/experiments_E1_E12_summary.csv`: Bảng tổng kết 12 dòng phục vụ viết bảng biểu Chương 6.
- `results/experiments_E1_E12_timeseries.csv`: Dữ liệu chuỗi thời gian 168 bước từng giờ phục vụ vẽ đồ thị.

### 5.2. Chạy Tùy biến từ Python Script
```python
from abm.model import DeFiLendingMesaModel

# Khởi tạo mô hình kịch bản S1 (Sốc giá), chiến lược Adaptive
model = DeFiLendingMesaModel(
    scenario_id="S1",
    strategy="adaptive",
    num_borrowers=100,
    num_lenders=50,
    num_liquidators=10,
    seed=42
)

# Chạy mô phỏng 168 giờ
df_results = model.run_simulation(steps=168)

# Xem các cột dữ liệu
print(df_results[["step", "eth_price", "utilization_rate", "total_bad_debt_usdc", "n_liquidated_total"]].tail())
```

### 5.3. Chạy Kiểm thử Tự động cho ABM
```bash
pytest tests/test_abm.py -v
```
*(Kiểm tra toàn diện Môi trường, Mô hình Lãi suất Kink, Vòng lặp Mesa Model và DataCollector).*
