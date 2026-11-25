# Hướng dẫn Smart Contract — DeFi Lending Protocol (Sepolia & Remix IDE)

> **Đề tài:** Nghiên cứu khả năng chống chịu rủi ro của giao thức cho vay DeFi dưới tác động của biến động thị trường và hành vi tương tác giữa các tác nhân (Bài tập lớn Blockchain).  
> **Phiên bản:** 0.1 | **Solidity Version:** `^0.8.20`

---

## 1. Kiến trúc Hệ thống Hợp đồng Thông minh

Giao thức cho vay được thiết kế chuẩn mực theo kiến trúc cốt lõi của **Aave V3**, không bị tối giản hóa quá mức (non-simplistic), đảm bảo đầy đủ cơ chế tài chính thực tế:

```
                                  ┌────────────────────────┐
                                  │    MockPriceOracle     │
                                  │ (Chainlink style - 8dp)│
                                  └───────────┬────────────┘
                                              │ Price Feed
                                              ▼
┌────────────────────────┐         ┌────────────────────────┐         ┌────────────────────────┐
│        MockUSDC        │◄───────►│    DeFiLendingPool     │◄───────►│   InterestRateModel    │
│  (ERC20 Token - 6dp)   │         │  (Core Lending Logic)  │         │   (Kink 2-slope model) │
└────────────────────────┘         └───────────┬────────────┘         └────────────────────────┘
                                               │
                                 ┌─────────────┴─────────────┐
                                 │      NATIVE ETH POOL      │
                                 │ (Overcollateralized Vault)│
                                 └───────────────────────────┘
```

### Các tính năng cốt lõi:
1. **Quản lý Tài sản Đa tầng:**
   - **Tài sản thế chấp (Collateral):** Native ETH (`msg.value`, 18 decimals) được khóa riêng biệt, **tuyệt đối không cộng gộp vào tổng cung USDC của bể**.
   - **Tài sản cho vay (Debt & Liquidity):** USDC (ERC-20, 6 decimals) được cung cấp bởi Lender và vay bởi Borrower.
2. **Mô hình Lãi suất Điểm gãy (Two-slope Kink Model):**
   - $Base = 0\%$, $Slope_1 = 4\%$, $Slope_2 = 75\%$, $U_{opt} = 80\%$, $ReserveFactor = 10\%$.
   - Tính toán lãi suất vay ($R_{borrow}$) và lãi suất gửi ($R_{supply}$) động theo từng giây dựa trên mức độ sử dụng vốn ($U = Debt / (Cash + Debt)$).
   - Tích lũy lãi suất theo thời gian thực (Timestamp-based Index compounding) thông qua `borrowIndex` và `liquidityIndex` chuẩn Aave.
3. **Quản trị Rủi ro & Chuẩn hóa Thập phân:**
   - Chuẩn hóa: ETH (18 decimals), USDC (6 decimals), Giá Oracle (8 decimals), Health Factor (18 decimals).
   - Ngưỡng thanh lý ($LT$): **80%** (8000 bps).
   - Tỷ lệ vay tối đa ($LTV$): **80%** (8000 bps).
   - Thưởng thanh lý ($Bonus$): **5%** (500 bps).
   - Tỷ lệ thanh lý tối đa ($CloseFactor$): **50%** (5000 bps).
4. **Cơ chế Thanh lý & Xã hội hóa Nợ xấu (Bad Debt Socialization):**
   - Kiểm tra điều kiện $HF < 1.0 \times 10^{18}$.
   - Áp dụng Close Factor 50% để tránh thanh lý toàn bộ vị thế một lần.
   - Thưởng 5% ETH cho Liquidator.
   - Khi tài sản thế chấp bị cạn kiệt mà không đủ bù đắp khoản nợ đã trả, giao thức tự động ghi nhận **Nợ xấu loại I (Qin)** vào `totalBadDebtUSDC` và khấu trừ vào nguồn vốn thanh khoản để xã hội hóa tổn thất.
5. **Bảo mật:** Tích hợp `ReentrancyGuard`, checks-effects-interactions, chống tràn số học (Solidity 0.8+).

---

## 2. Hướng dẫn Test Nhanh trên Remix IDE (Chỉ mất 2 phút)

Bạn **không cần cài đặt môi trường phức tạp**, có thể dùng ngay file tổng hợp gộp sẵn: [`contract/DeFiLendingPoolFlat.sol`](DeFiLendingPoolFlat.sol).

### Bước 1: Mở Remix IDE & Tạo file
1. Mở trình duyệt truy cập: **[https://remix.ethereum.org](https://remix.ethereum.org)**.
2. Tại cây thư mục bên trái (`contracts/`), tạo file mới tên `DeFiLendingPool.sol`.
3. Mở file [contract/DeFiLendingPoolFlat.sol](DeFiLendingPoolFlat.sol) trong repo này, **Copy toàn bộ nội dung** và Paste vào Remix.

### Bước 2: Compile
1. Bấm vào tab **Solidity Compiler** (icon thứ 3 bên trái).
2. Chọn phiên bản `0.8.20` (hoặc mới hơn như `0.8.24`).
3. Bấm **Compile DeFiLendingPool.sol** (hiện tích xanh ✅).

### Bước 3: Deploy trên Remix VM
Chuyển sang tab **Deploy & Run Transactions** (chọn Environment: `Remix VM (Cancun / Shanghai)`):

1. **Deploy MockUSDC:**
   - Tại dropdown *Contract*, chọn `MockUSDC`.
   - Bấm **Deploy**. Lưu lại địa chỉ contract (VD: `0xUSDC...`).
2. **Deploy MockPriceOracle:**
   - Tại dropdown *Contract*, chọn `MockPriceOracle`.
   - Bấm **Deploy**. (Mặc định giá ETH được khởi tạo là `$2,000.00` = `200000000000`).
   - Lưu lại địa chỉ contract (VD: `0xOracle...`).
3. **Deploy InterestRateModel:**
   - Tại dropdown *Contract*, chọn `InterestRateModel`.
   - Nhập tham số:
     - `_baseRate`: `0`
     - `_slope1`: `40000000000000000` (4% = $0.04 \times 10^{18}$)
     - `_slope2`: `750000000000000000` (75% = $0.75 \times 10^{18}$)
     - `_uOpt`: `800000000000000000` (80% = $0.80 \times 10^{18}$)
     - `_reserveFactor`: `100000000000000000` (10% = $0.10 \times 10^{18}$)
   - Bấm **Deploy**. Lưu lại địa chỉ contract (VD: `0xIRModel...`).
4. **Deploy DeFiLendingPool:**
   - Tại dropdown *Contract*, chọn `DeFiLendingPool`.
   - Điền 3 địa chỉ tương ứng: `_usdcAddress`, `_oracleAddress`, `_interestRateModelAddress`.
   - Bấm **Deploy**!

---

## 3. Kịch bản Kiểm thử Chuẩn hóa (Benchmark Test Suite)

Tái hiện chính xác bảng kiểm thử mục 3.2 và 4.4 của thuyết minh:

### Kịch bản khởi tạo vị thế:
1. **Lender nạp thanh khoản:**
   - Chọn Account 1 (Deployer đang có 10,000,000 USDC).
   - Tại contract `MockUSDC`, gọi `approve(address_DeFiLendingPool, 10000000000)` (10,000 USDC = 10,000 * 10^6).
   - Tại contract `DeFiLendingPool`, gọi `supplyUSDC(10000000000)`.
2. **Borrower nạp thế chấp 2 ETH:**
   - Chuyển sang Account 2 (Borrower).
   - Ở ô **Value** phía trên, điền `2` và chọn đơn vị `Ether`.
   - Bấm gọi hàm `depositCollateral`.
3. **Borrower vay 2,000 USDC:**
   - Account 2 gọi `borrowUSDC(2000000000)` (2,000 USDC = 2,000 * 10^6).
   - Bấm `getHealthFactor(Account_2)` ➔ Kết quả: `1600000000000000000` (**HF = 1.60**). ✅ Khớp 100%!

### Kịch bản Sốc giá ETH & Kích hoạt Thanh lý:
Chuyển sang Account 1 (Admin của Oracle) để thay đổi giá ETH:

| Giá ETH | Thao tác Oracle (`setEthPrice`) | Kết quả `getHealthFactor` | Đánh giá trạng thái |
|---|---|---|---|
| **$2,000** | Giá ban đầu | `1.60 * 1e18` | An toàn ($LTV = 50\%$) |
| **$1,500** | Gọi `setEthPrice(150000000000)` | `1.20 * 1e18` | Cảnh báo ($LTV = 66.67\%$) |
| **$1,250** | Gọi `setEthPrice(125000000000)` | `1.00 * 1e18` | Chạm ngưỡng thanh lý ($HF = 1.0$) |
| **$1,000** | Gọi `setEthPrice(100000000000)` | `0.80 * 1e18` | Dưới ngưỡng ($HF = 0.80$). Đủ điều kiện thanh lý! |

### Thực thi Thanh lý:
1. Chuyển sang Account 3 (Liquidator).
2. Tại `MockUSDC`, gọi `faucet()` để nhận 10,000 USDC, sau đó gọi `approve(address_DeFiLendingPool, 5000000000)`.
3. Tại `DeFiLendingPool`, gọi `liquidate(Account_2, 1000000000)` (trả 1,000 USDC = 50% Close Factor).
4. **Kết quả:**
   - Dư nợ của Borrower giảm từ 2,000 USDC về 1,000 USDC.
   - Liquidator nhận được: $\frac{1.000 \times 1.05}{1.000} = 1.05 \text{ ETH}$ (lãi 5% thế chấp).
   - Health Factor mới của Borrower hồi phục về an toàn!

---

## 4. Triển khai lên Sepolia Testnet bằng Script & Nạp Dữ Liệu ETH Thật

Hợp đồng `MockPriceOracle` đã được nâng cấp để **hoạt động hoàn toàn bằng dữ liệu thực tế** (thay vì dữ liệu test giả định):
1. **Khởi tạo bằng Giá Binance Thật**: Giá ban đầu được đặt chính xác tại `$3,465.98` (giá nến thật của ETH tại thời điểm bắt đầu đợt sụp đổ tháng 5/2021).
2. **Chế độ Chainlink Live Oracle trên Sepolia**:
   - Gọi hàm `setUseChainlinkLive(true)` trên hợp đồng `MockPriceOracle`.
   - Hợp đồng sẽ tự động kéo giá thời gian thực trực tiếp từ mạng lưới phi tập trung Chainlink Sepolia:  
     `Aggregator: 0x694AA1769357215DE4FAC081bf1f309aDC325306`.
3. **Nạp 168 nến lịch sử Binance bằng Script**:
   - Chạy script: `python contract/feed_oracle_real_data.py` để nạp chuỗi nến biến động thực tế vào hợp đồng.
4. **Kiểm thử logic toán học**: Toàn bộ unit tests và test vectors được giữ cách ly hoàn toàn trong Python (`pytest tests/ -v`).

### Hướng dẫn Deploy lên Sepolia:
1. Tạo file `.env` ở thư mục gốc:
```env
SEPOLIA_RPC_URL="https://rpc.sepolia.org"
PRIVATE_KEY="0xYOUR_SEPOLIA_PRIVATE_KEY"
```
2. Chạy lệnh deploy:
```bash
node contract/deploy.js
```
Script sẽ tự động deploy lần lượt 4 hợp đồng, in ra địa chỉ và link Sepolia Etherscan sẵn sàng để bạn đưa vào **Chương 5 của Báo cáo bài tập lớn**.
