# DeFi Liquidation Risk Simulator (DeFi Risk Lab)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tuananh21065-hub/defi-risk/blob/main/defi_risk_lab_colab.ipynb)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Mesa ABM](https://img.shields.io/badge/ABM-Mesa%203.3+-orange.svg)](https://mesa.readthedocs.io/)
[![Solidity](https://img.shields.io/badge/Solidity-%5E0.8.20-lightgrey.svg)](https://soliditylang.org/)
[![Tests](https://img.shields.io/badge/tests-23%2F23%20passed-brightgreen.svg)](tests/)

> **Đề tài:** Nghiên cứu khả năng chống chịu rủi ro của giao thức cho vay DeFi dưới tác động của biến động thị trường và hành vi tương tác giữa các tác nhân.  
> **Bài tập lớn môn Blockchain** — Kết hợp **Mô hình đa tác nhân (Mesa ABM)**, **Dữ liệu nến 1h Binance Vision** và **Smart Contract trên Ethereum Sepolia Testnet** (mô phỏng Aave V3 core).

---

## 🎯 Câu hỏi nghiên cứu (Research Questions)

- **RQ1 (Điều kiện thị trường & Chi phí vận hành):** Biến động giá ETH, độ biến động theo giờ, chi phí gas và trượt giá DEX ảnh hưởng như thế nào đến khả năng thanh lý và mức độ an toàn của giao thức?
- **RQ2 (Hành vi thích nghi & Tương tác tác nhân):** Hành vi thích nghi (Adaptive) của Borrower, Lender và Liquidator tương tác với nhau ra sao khi nhiều cú sốc xảy ra đồng thời (giá, thanh khoản, lãi suất, chi phí vận hành), và làm gia tăng hay giảm nhẹ rủi ro hệ thống so với hành vi cố định (Fixed)?

---

## 📁 Cấu trúc Dự án

```
defi-risk-simulation/
├── abm/                          # Mô hình Đa tác nhân (Mesa ABM Framework)
│   ├── market.py                 # Lớp Môi trường: Chuỗi giá 168h, gas shock, trượt giá DEX phi tuyến
│   ├── protocol.py               # Lớp Giao thức: Bể cho vay, Lãi suất Kink, Hàng chờ rút, Nợ xấu
│   ├── agents.py                 # Tác nhân Mesa: BorrowerAgent, LenderAgent, LiquidatorAgent (Fixed vs Adaptive)
│   ├── model.py                  # DeFiLendingMesaModel (168 bước, DataCollector)
│   ├── runner.py                 # Trình điều phối chạy Ma trận 12 Thực nghiệm E1–E12 (Seed 42)
│   ├── README.md                 # Hướng dẫn chi tiết kiến trúc ABM & kết quả thực nghiệm
│   └── __init__.py
├── contract/                     # Smart Contract Solidity (Chuẩn Aave V3 Core)
│   ├── MockUSDC.sol              # Token USDC 6 decimals, faucet mint 10.000 USDC
│   ├── MockPriceOracle.sol       # Oracle giá ETH chuẩn Chainlink (8 decimals, hàm setEthPrice)
│   ├── InterestRateModel.sol     # Mô hình lãi suất Kink (U_opt=80%, Slope1=4%, Slope2=75%)
│   ├── DeFiLendingPool.sol       # Hợp đồng cho vay cốt lõi (Module hóa)
│   ├── DeFiLendingPoolFlat.sol   # FILE GỘP DUY NHẤT — COPY 1-CLICK VÀO REMIX IDE
│   ├── deploy.js                 # Script deploy tự động lên Sepolia Testnet
│   ├── README.md                 # Hướng dẫn chi tiết test trên Remix IDE & Sepolia
│   └── build/                    # ABI và Bytecode đã compile sẵn bằng solc 0.8.20+
├── data/                         # Dữ liệu nến 1h từ Binance Vision
│   ├── fetch_binance_data.py     # Script tự động tải và chuẩn hóa nến 1h từ Binance API
│   ├── eth_usdt_168h_may2021.csv # Đợt sụp đổ tháng 5/2021 (-50.12%, biến động 3.05%/h)
│   ├── eth_usdt_168h_ftx2022.csv # Khủng hoảng FTX tháng 11/2022 (-34.11%)
│   ├── eth_usdt_168h_mar2020.csv # Thứ Năm Đen Tối 2020 (-55.51%, Qin et al. 2021)
│   └── eth_usdt_168h_active.csv  # File nến active đang dùng cho mô phỏng
├── config/
│   ├── parameters.py             # Bảng tham số mô phỏng v0.1 (PAPER, ASSUMPTION, PLACEHOLDER)
│   └── __init__.py
├── results/                      # Dữ liệu kết quả thực nghiệm xuất ra CSV
│   ├── experiments_E1_E12_summary.csv    # Bảng tổng kết 12 thực nghiệm
│   ├── experiments_E1_E12_timeseries.csv # Chuỗi thời gian 168 giờ
│   └── results.csv               # Kết quả legacy benchmark
├── tests/
│   ├── test_abm.py               # Test mô hình Mesa ABM, protocol pool, market & runner
│   ├── test_benchmark.py         # Bộ kiểm thử chuẩn hóa dùng chung Python & Smart Contract
│   ├── test_model.py             # Test tính Health Factor, ràng buộc số dư
│   └── test_liquidation.py       # Test quy tắc thanh lý, gas, bad debt (23 tests passed)
├── app.py                        # Streamlit Dashboard (Trực quan hóa E1–E12 & Interactive Simulator)
├── main.py                       # Entry point chạy toàn bộ kịch bản và thực nghiệm
├── model_spec.md                 # Đặc tả toán học, quy tắc tác nhân và cơ chế giao thức
├── scope.md                      # Phạm vi dự án cập nhật (MUST / SHOULD / NOT NOW)
└── examples.md                   # Ví dụ tính tay và test vectors chuẩn
```

---

## ⚙️ Hướng dẫn Cài đặt & Chạy Chi tiết

### 1. Cài đặt Môi trường & Thư viện
Yêu cầu Python 3.10 trở lên:
```bash
pip install streamlit pandas numpy scipy matplotlib seaborn pytest ipywidgets mesa
```

---

### 2. Tải Dữ liệu Lịch sử Thực tế từ Binance Vision (Cách A - Khuyến nghị)
Chạy script để tải 168 nến 1h của cặp ETHUSDT trong các tuần sụp đổ lịch sử của DeFi:
```bash
python data/fetch_binance_data.py
```
*Script sẽ tự động tải 3 đợt khủng hoảng lớn nhất (May 2021, FTX 2022, Black Thursday 2020) và kích hoạt đợt tháng 5/2021 làm dữ liệu mặc định.*

---

### 3. Chạy Toàn bộ Ma trận Thực nghiệm E1–E12 (Mesa ABM)
Chạy 12 thực nghiệm đối chứng trên cùng đường giá (Seed 42) và xuất kết quả ra CSV:
```bash
python -X utf8 main.py
```
*Hoặc chỉ chạy riêng module ABM:*
```bash
python abm/runner.py
```
Kết quả được lưu tại:
- `results/experiments_E1_E12_summary.csv` (Bảng số liệu tổng hợp cho Chương 6).
- `results/experiments_E1_E12_timeseries.csv` (Dữ liệu 168 giờ để vẽ biểu đồ).

---

### 4. Khởi chạy Giao diện Trực quan hóa (Streamlit Dashboard)
```bash
python -m streamlit run app.py
```
Mở trình duyệt tại: **`http://localhost:8501`**
Dashboard bao gồm 3 phân hệ:
1. **📊 Ma trận 12 Thực nghiệm (E1–E12):** Bảng tổng kết và biểu đồ so sánh đối chứng Fixed vs Adaptive cho từng kịch bản S0–S5.
2. **🎮 Giả lập Tương tác 168 Giờ (Live ABM):** Tự do chọn kịch bản, số lượng Borrower, seed và theo dõi biến động thời gian thực.
3. **📜 Smart Contract Sepolia & Benchmark:** Xem thông tin hợp đồng và bảng kiểm thử chuẩn hóa.

---

### 5. Chạy Kiểm thử Toàn bộ Hệ thống (Unit Tests)
```bash
pytest tests/ -v
```
*(Hiện có **23/23 tests** kiểm tra toàn diện logic toán học, Mesa ABM, ràng buộc số dư và bộ kiểm thử benchmark).*

---

### 6. Kiểm thử Smart Contract trên Remix IDE hoặc Sepolia Testnet

Hợp đồng được lưu trữ sẵn trong thư mục **[contract/](contract/)**:

- **Cách 1: Test trực quan trên Remix IDE (Chỉ mất 2 phút):**
  1. Mở [remix.ethereum.org](https://remix.ethereum.org).
  2. Tạo file `DeFiLendingPool.sol` và dán toàn bộ nội dung từ **[`contract/DeFiLendingPoolFlat.sol`](contract/DeFiLendingPoolFlat.sol)**.
  3. Chọn Compiler `0.8.20+` và bấm **Compile**.
  4. Deploy lần lượt `MockUSDC`, `MockPriceOracle`, `InterestRateModel` và `DeFiLendingPool` để test trực quan các nút nạp ETH, vay USDC, đổi giá Oracle và thanh lý.
  *(Xem hướng dẫn chi tiết tại [`contract/README.md`](contract/README.md)).*

- **Cách 2: Deploy lên Ethereum Sepolia Testnet:**
  Tạo file `.env` với khóa cá nhân ví Sepolia:
  ```env
  SEPOLIA_RPC_URL="https://rpc.sepolia.org"
  PRIVATE_KEY="0xYOUR_PRIVATE_KEY"
  ```
  Chạy lệnh deploy:
  ```bash
  node contract/deploy.js
  ```

---

## 📊 Bảng Kết quả Ma trận Thực nghiệm E1–E12 (Phục vụ Chương 6 Báo cáo)

| Mã TN | Kịch bản | Chiến lược | Tỷ lệ TL (%) | Số Borrower bị TL | Utilization max (%) | Lãi vay max (% APR) | Rút tiền bị kẹt (USDC) | Trễ rút TB (giờ) | Lợi nhuận Liquidator ($) | Mục đích kiểm chứng |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **E1** | **S0** (Cơ sở) | **Fixed** | **64.0%** | 64 | 60.00% | 3.00% | 0.00 | 0.00 | $4,997.28 | Đường cơ sở so sánh |
| **E2** | **S0** (Cơ sở) | **Adaptive** | **49.0%** | 49 | 67.56% | 3.38% | 0.00 | 0.00 | $3,826.23 | Đường cơ sở so sánh |
| **E3** | **S1** (Sốc giá -43%) | **Fixed** | **64.0%** | 64 | 60.00% | 3.00% | 0.00 | 0.00 | $4,892.59 | **Kiểm tra H1, H4** |
| **E4** | **S1** (Sốc giá -43%) | **Adaptive** | **50.0%** | 50 | 67.51% | 3.38% | 0.00 | 0.00 | $3,725.10 | **Kiểm tra H1, H4** (Adaptive giảm 14% tỷ lệ TL) |
| **E5** | **S2** (Sốc thanh khoản) | **Fixed** | 64.0% | 64 | 98.35% | 72.82% | 0.00 | 0.00 | $4,997.28 | **Kiểm tra H3** |
| **E6** | **S2** (Sốc thanh khoản) | **Adaptive** | 49.0% | 49 | **100.00%** | **79.00%** | **472,926.45** | **15.87 giờ** | $3,826.23 | **Kiểm tra H3** (Bank-run gây kẹt rút 472k USDC) |
| **E7** | **S3** (Sốc lãi suất) | **Fixed** | 64.0% | 64 | 90.01% | 41.52% | 0.00 | 0.00 | $4,997.28 | Chi phí vay & áp lực thanh khoản |
| **E8** | **S3** (Sốc lãi suất) | **Adaptive** | 49.0% | 49 | **100.00%** | **79.00%** | **351,109.41** | **18.86 giờ** | $3,826.23 | Chi phí vay & áp lực thanh khoản |
| **E9** | **S4** (Sốc chi phí) | **Fixed** | **2.0%** | 2 | 60.00% | 3.00% | 0.00 | 0.00 | **$21.34** | **Kiểm tra H2, H5** (Gas 100$ dập tắt thanh lý) |
| **E10** | **S4** (Sốc chi phí) | **Adaptive** | **11.0%** | 11 | 67.47% | 3.37% | 0.00 | 0.00 | **$298.09** | **Kiểm tra H2, H5** (Adaptive tìm kiếm được vị thế có lãi) |
| **E11** | **S5** (Sốc kết hợp) | **Fixed** | 2.0% | 2 | 80.15% | 4.56% | 0.00 | 0.00 | $21.34 | **Kiểm tra H5, H6** |
| **E12** | **S5** (Sốc kết hợp) | **Adaptive** | 11.0% | 11 | **100.00%** | **79.00%** | **589,918.05** | **4.83 giờ** | $288.56 | **Kiểm tra H5, H6** (Rủi ro hệ thống đạt đỉnh) |

---

## 🔢 Tham số Mô hình Cốt lõi (v0.1)

| Tham số | Ký hiệu | Giá trị chuẩn | Các mức quét thực nghiệm | Nhãn & Nguồn |
|---|---|---|---|---|
| Liquidation Threshold | $LT$ | 0.80 | 0.70; 0.75; 0.80; 0.85 | `PLACEHOLDER` (Qin ví dụ; Aave V3) |
| Liquidation Bonus | $Bonus$ | 0.05 (5%) | 0.05; 0.08; 0.10; 0.15 | `PAPER` (Qin: Aave 5-15%, Compound 8%) |
| Close Factor | $CF$ | 0.50 (50%) | Cố định 0.50 | `PAPER` (Chaudhary & Pinna; Qin) |
| Lãi suất Kink | $U_{opt}$ | 0.80 (80%) | 0.45; 0.80; 0.90 | `PLACEHOLDER` (Base 0%, Slope1 4%, Slope2 75%) |
| Thời gian mô phỏng | $T$ | 168 bước | 168 giờ (7 ngày) | `ASSUMPTION` (ABM cần chân trời dài) |
| Số lần Monte Carlo | $N$ | 100 / 1.000 | 100 (dev) / 1.000 (chính thức) | `PAPER` (Chaudhary & Pinna) |
| Phí Gas | $gas$ | $10 / $100 | $10 (thấp) vs $100 (nghẽn mạng) | `PAPER` (Qin) |
| Hàm trượt giá DEX | $\sigma(x)$ | $\gamma + s(x/V)^\omega$ | $\gamma=0.003, s=1.0, V=10^9$ USD | `PAPER` (Chaudhary & Pinna) |
| Giá ETH ban đầu $P_0$ | $P_0$ | $3,465.98 | Chuẩn hóa $2,000 cho benchmark | `PAPER` (Binance Vision 17/05/2021) |
| Biến động theo giờ | $\sigma_{1h}$ | 0.0305 | 3.05%/giờ ($\sigma_{ann} = 285.2\%$) | `PAPER` (Binance Vision 17/05/2021) |

---

## 📚 Tài liệu Tham khảo

1. **Qin, K. et al. (2021).** An Empirical Study of DeFi Liquidations: Incentives, Risks, and Instabilities. *ACM IMC 2021*.
2. **Chaudhary, A., Pinna, D. (2022).** A multi-asset, agent-based approach applied to DeFi lending protocol modelling. *arXiv:2211.08870*.
3. **Sasi-Brodesky, A., Nassr, I. K. (2023).** DeFi liquidations: Volatility and liquidity. *OECD Working Paper No. 48*.
4. **Bertucci, C. et al. (2026).** Agents' Behavior and Interest Rate Model Optimization in DeFi Lending. *Mathematical Finance*.
5. **Aave V3 Technical Documentation:** Risk Parameters, Interest Rate Strategy & Liquidations.
