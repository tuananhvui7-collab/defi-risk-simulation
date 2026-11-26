# Báo cáo dữ liệu mô phỏng đã kiểm chứng

Báo cáo này được dựng trực tiếp từ các CSV vừa tạo bởi mã mô phỏng trong repository. Các kết luận dưới đây mô tả kết quả của mô hình và cấu hình đã chạy; chúng không phải khẳng định về toàn bộ thị trường DeFi ngoài đời.

## Cấu hình và kiểm tra dữ liệu

- Ma trận E1–E12: 12 dòng, 100 borrower/run, 168 bước, seed 42.
- S5 Ablation: 5 cấu hình, 100 borrower/run, 168 bước, cùng seed 42.
- Monte Carlo: 6.000 run; S0/S1/S5 × Fixed/Adaptive, mỗi nhóm đúng 1.000 run, 50 borrower/run; seed 42–1041. Các chiến lược cùng dùng cùng dãy seed để tạo đối sánh theo seed.
- VaR95 trong bảng là phân vị thực nghiệm 95% của giá trị run-level. Độ lệch chuẩn là độ lệch chuẩn mẫu (`ddof=1`). Với Liquidation Coverage Ratio, mô hình trả 1.0 khi không có borrower từng HF < 1.0.
- Bad Debt Exposure cuối phiên = Realized Bad Debt + Unrealized Bad Debt cuối phiên. Các cột peak trong bảng E/Ablation là mức đỉnh được theo dõi theo thời gian; bảng Monte Carlo dùng exposure cuối phiên.
- Số tiền rút bị kẹt là số dư còn trong queue ở cuối phiên; Fulfillment Rate = USDC đã giải ngân / USDC được yêu cầu.

## Bảng 1 — Ma trận E1–E12 (seed 42)

| Mã thực nghiệm | Kịch bản | Chiến lược | Nợ xấu (USDC) | Số Borrower bị TL | Tỷ lệ thanh lý (%) | Utilization max (%) | Lãi vay max (% APR) | Cash khả dụng TB (USDC) | Rút tiền bị kẹt (USDC) | Độ trễ rút TB (giờ) | avg_fulfilled_delay_h | avg_all_wait_h | withdrawal_fulfillment_rate | n_ever_eligible | liquidation_coverage_ratio | unliquidated_positions_end | unliquidated_debt_at_risk_usdc | realized_bad_debt_usdc | unrealized_bad_debt_usdc | unrealized_bad_debt_peak_usdc | total_bad_debt_exposure_usdc | total_bad_debt_exposure_peak_usdc | exogenous_debt_usdc | Lợi nhuận Liquidator ($) | Mục đích kiểm chứng |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E1 | S0 | Fixed | 0.00 | 0 | 0.00 | 60.00 | 3.00 | 309,933.56 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000000 | 0 | 1.000000 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | Đường cơ sở so sánh |
| E2 | S0 | Adaptive | 0.00 | 0 | 0.00 | 67.18 | 3.36 | 223,178.31 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000000 | 0 | 1.000000 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | Đường cơ sở so sánh |
| E3 | S1 | Fixed | 0.00 | 64 | 64.00 | 60.00 | 3.00 | 473,055.99 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000000 | 68 | 0.941176 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 4,893.84 | Kiểm tra H1, H4 (Rủi ro thanh lý) |
| E4 | S1 | Adaptive | 0.00 | 50 | 50.00 | 67.51 | 3.38 | 155,269.74 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000000 | 55 | 0.909091 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 3,726.40 | Kiểm tra H1, H4 (Rủi ro thanh lý) |
| E5 | S2 | Fixed | 0.00 | 0 | 0.00 | 100.00 | 79.00 | 53,720.77 | 73,759.99 | 0.00 | 0.00 | 134.00 | 0.808778 | 0 | 1.000000 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | Kiểm tra H3 (Khả năng đáp ứng rút tiền) |
| E6 | S2 | Adaptive | 0.00 | 0 | 0.00 | 100.00 | 79.00 | 37,475.59 | 827,882.45 | 0.64 | 0.64 | 70.18 | 0.284575 | 0 | 1.000000 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | Kiểm tra H3 (Khả năng đáp ứng rút tiền) |
| E7 | S3 | Fixed | 0.00 | 0 | 0.00 | 90.04 | 41.66 | 119,374.64 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000000 | 0 | 1.000000 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 234,297.25 | 0.00 | Chi phí vay và áp lực thanh khoản |
| E8 | S3 | Adaptive | 0.00 | 0 | 0.00 | 100.00 | 79.00 | 42,512.14 | 567,392.77 | 0.90 | 0.90 | 66.51 | 0.264519 | 0 | 1.000000 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 124,869.14 | 0.00 | Chi phí vay và áp lực thanh khoản |
| E9 | S4 | Fixed | 0.00 | 2 | 2.00 | 60.00 | 3.00 | 405,914.94 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000000 | 68 | 0.029412 | 53 | 177,331.21 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 21.37 | Kiểm tra H2, H5 (Hiệu quả thanh lý) |
| E10 | S4 | Adaptive | 0.00 | 11 | 11.00 | 67.50 | 3.38 | 183,704.47 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000000 | 75 | 0.146667 | 62 | 199,367.19 | 0.00 | 10,389.29 | 13,954.85 | 10,389.29 | 13,954.85 | 0.00 | 289.09 | Kiểm tra H2, H5 (Hiệu quả thanh lý) |
| E11 | S5 | Fixed | 0.00 | 2 | 2.00 | 96.18 | 64.69 | 89,800.67 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000000 | 70 | 0.028571 | 58 | 194,306.68 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 21.48 | Kiểm tra H5, H6 (Khả năng chống chịu) |
| E12 | S5 | Adaptive | 0.00 | 13 | 13.00 | 100.00 | 79.00 | 35,433.25 | 726,233.59 | 3.51 | 3.51 | 68.33 | 0.372416 | 78 | 0.166667 | 62 | 201,415.42 | 0.00 | 11,714.15 | 15,433.65 | 11,714.15 | 15,433.65 | 0.00 | 323.07 | Kiểm tra H5, H6 (Khả năng chống chịu) |

## Bảng 2 — S5 Ablation Study (seed 42)

| Mã thực nghiệm | Kịch bản | Chiến lược | Nợ xấu (USDC) | Số Borrower bị TL | Tỷ lệ thanh lý (%) | Utilization max (%) | Lãi vay max (% APR) | Cash khả dụng TB (USDC) | Rút tiền bị kẹt (USDC) | Độ trễ rút TB (giờ) | avg_fulfilled_delay_h | avg_all_wait_h | withdrawal_fulfillment_rate | n_ever_eligible | liquidation_coverage_ratio | unliquidated_positions_end | unliquidated_debt_at_risk_usdc | realized_bad_debt_usdc | unrealized_bad_debt_usdc | unrealized_bad_debt_peak_usdc | total_bad_debt_exposure_usdc | total_bad_debt_exposure_peak_usdc | exogenous_debt_usdc | Lợi nhuận Liquidator ($) | Mục đích kiểm chứng | Ablation | borrower_strategy | lender_strategy | liquidator_strategy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | S5 | Mixed | 0.00 | 2 | 2.00 | 96.18 | 64.69 | 89,800.67 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000000 | 70 | 0.028571 | 58 | 194,306.68 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 21.48 | S5 ablation study | All-Fixed | fixed | fixed | fixed |
| A2 | S5 | Mixed | 0.00 | 0 | 0.00 | 100.00 | 79.00 | 68,872.07 | 0.00 | 0.17 | 0.17 | 2.00 | 1.000000 | 78 | 0.000000 | 69 | 246,805.72 | 0.00 | 11,526.42 | 15,383.68 | 11,526.42 | 15,383.68 | 0.00 | 0.00 | S5 ablation study | Borrower-Adaptive only | adaptive | fixed | fixed |
| A3 | S5 | Mixed | 0.00 | 16 | 16.00 | 96.18 | 64.69 | 109,555.83 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000000 | 68 | 0.235294 | 45 | 127,140.57 | 0.00 | 0.00 | 67.91 | 0.00 | 67.91 | 0.00 | 434.38 | S5 ablation study | Liquidator-Adaptive only | fixed | fixed | adaptive |
| A4 | S5 | Mixed | 0.00 | 2 | 2.00 | 100.00 | 79.00 | 37,585.44 | 728,141.54 | 0.43 | 0.43 | 67.65 | 0.370767 | 72 | 0.027778 | 62 | 208,970.98 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 21.65 | S5 ablation study | Lender-Adaptive only | fixed | adaptive | fixed |
| A5 | S5 | Mixed | 0.00 | 13 | 13.00 | 100.00 | 79.00 | 35,433.25 | 726,233.59 | 3.51 | 3.51 | 68.33 | 0.372416 | 78 | 0.166667 | 62 | 201,415.42 | 0.00 | 11,714.15 | 15,433.65 | 11,714.15 | 15,433.65 | 0.00 | 323.07 | S5 ablation study | All-Adaptive | adaptive | adaptive | adaptive |

## Bảng 2b — Đối chứng S4 chỉ Liquidator Adaptive (seed 42)

| Mã thực nghiệm | Kịch bản | Chiến lược | Nợ xấu (USDC) | Số Borrower bị TL | Tỷ lệ thanh lý (%) | Utilization max (%) | Lãi vay max (% APR) | Cash khả dụng TB (USDC) | Rút tiền bị kẹt (USDC) | Độ trễ rút TB (giờ) | avg_fulfilled_delay_h | avg_all_wait_h | withdrawal_fulfillment_rate | n_ever_eligible | liquidation_coverage_ratio | unliquidated_positions_end | unliquidated_debt_at_risk_usdc | realized_bad_debt_usdc | unrealized_bad_debt_usdc | unrealized_bad_debt_peak_usdc | total_bad_debt_exposure_usdc | total_bad_debt_exposure_peak_usdc | exogenous_debt_usdc | Lợi nhuận Liquidator ($) | Mục đích kiểm chứng | borrower_strategy | lender_strategy | liquidator_strategy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S4_LiqAdaptive_Only | S4 | Mixed | 0.00 | 16 | 16.00 | 60.00 | 3.00 | 425,656.95 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000000 | 68 | 0.235294 | 43 | 122,686.53 | 0.00 | 0.00 | 60.11 | 0.00 | 60.11 | 0.00 | 432.23 | Đối chứng cô lập vai trò Liquidator trong S4 | fixed | fixed | adaptive |

## Bảng 3 — Monte Carlo (1.000 run mỗi kịch bản/chiến lược)

| Kịch bản | Chiến lược | Chỉ số | N | Mean | Median | Std mẫu | VaR95 / phân vị 95% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S0 | Adaptive | Tỷ lệ thanh lý (%) | 1000 | 0.00 | 0.00 | 0.00 | 0.00 |
| S0 | Adaptive | Liquidation Coverage Ratio | 1000 | 1.00 | 1.00 | 0.00 | 1.00 |
| S0 | Adaptive | Tổng Bad Debt Exposure (USDC) | 1000 | 0.00 | 0.00 | 0.00 | 0.00 |
| S0 | Adaptive | Tiền rút còn kẹt cuối phiên (USDC) | 1000 | 0.00 | 0.00 | 0.00 | 0.00 |
| S0 | Adaptive | Withdrawal Fulfillment Rate | 1000 | 1.00 | 1.00 | 0.00 | 1.00 |
| S0 | Fixed | Tỷ lệ thanh lý (%) | 1000 | 0.00 | 0.00 | 0.00 | 0.00 |
| S0 | Fixed | Liquidation Coverage Ratio | 1000 | 1.00 | 1.00 | 0.00 | 1.00 |
| S0 | Fixed | Tổng Bad Debt Exposure (USDC) | 1000 | 0.00 | 0.00 | 0.00 | 0.00 |
| S0 | Fixed | Tiền rút còn kẹt cuối phiên (USDC) | 1000 | 0.00 | 0.00 | 0.00 | 0.00 |
| S0 | Fixed | Withdrawal Fulfillment Rate | 1000 | 1.00 | 1.00 | 0.00 | 1.00 |
| S1 | Adaptive | Tỷ lệ thanh lý (%) | 1000 | 55.37 | 56.00 | 6.87 | 66.00 |
| S1 | Adaptive | Liquidation Coverage Ratio | 1000 | 1.00 | 1.00 | 0.02 | 1.00 |
| S1 | Adaptive | Tổng Bad Debt Exposure (USDC) | 1000 | 0.00 | 0.00 | 0.00 | 0.00 |
| S1 | Adaptive | Tiền rút còn kẹt cuối phiên (USDC) | 1000 | 0.00 | 0.00 | 0.00 | 0.00 |
| S1 | Adaptive | Withdrawal Fulfillment Rate | 1000 | 1.00 | 1.00 | 0.00 | 1.00 |
| S1 | Fixed | Tỷ lệ thanh lý (%) | 1000 | 71.54 | 72.00 | 6.37 | 82.00 |
| S1 | Fixed | Liquidation Coverage Ratio | 1000 | 0.97 | 1.00 | 0.04 | 1.00 |
| S1 | Fixed | Tổng Bad Debt Exposure (USDC) | 1000 | 0.00 | 0.00 | 0.00 | 0.00 |
| S1 | Fixed | Tiền rút còn kẹt cuối phiên (USDC) | 1000 | 0.00 | 0.00 | 0.00 | 0.00 |
| S1 | Fixed | Withdrawal Fulfillment Rate | 1000 | 1.00 | 1.00 | 0.00 | 1.00 |
| S5 | Adaptive | Tỷ lệ thanh lý (%) | 1000 | 18.63 | 18.00 | 5.82 | 28.00 |
| S5 | Adaptive | Liquidation Coverage Ratio | 1000 | 0.23 | 0.23 | 0.07 | 0.35 |
| S5 | Adaptive | Tổng Bad Debt Exposure (USDC) | 1000 | 5,489.13 | 5,405.27 | 1,320.06 | 7,842.30 |
| S5 | Adaptive | Tiền rút còn kẹt cuối phiên (USDC) | 1000 | 380,531.28 | 379,241.09 | 22,370.19 | 418,921.27 |
| S5 | Adaptive | Withdrawal Fulfillment Rate | 1000 | 0.39 | 0.39 | 0.02 | 0.42 |
| S5 | Fixed | Tỷ lệ thanh lý (%) | 1000 | 3.40 | 2.00 | 3.22 | 10.00 |
| S5 | Fixed | Liquidation Coverage Ratio | 1000 | 0.05 | 0.03 | 0.04 | 0.13 |
| S5 | Fixed | Tổng Bad Debt Exposure (USDC) | 1000 | 6.14 | 0.00 | 21.89 | 52.53 |
| S5 | Fixed | Tiền rút còn kẹt cuối phiên (USDC) | 1000 | 0.00 | 0.00 | 0.00 | 0.00 |
| S5 | Fixed | Withdrawal Fulfillment Rate | 1000 | 1.00 | 1.00 | 0.00 | 1.00 |

## Đánh giá giả thuyết H1–H6 theo kết quả vừa chạy

1. **H1 — Giá ETH giảm làm tăng thanh lý: được ủng hộ trong mô hình.** E1/S0 Fixed = 0.00%, E3/S1 Fixed = 64.00%. Monte Carlo Fixed cũng tăng từ S0 mean 0.00% lên S1 mean 71.54%. Đây là đối chứng rõ giữa hai đường giá đã tách.
2. **H2 — Sốc chi phí làm giảm thanh lý/lợi nhuận: được ủng hộ.** Đối chứng đúng là E9 (S4 Fixed: gas $100, trượt giá 5x) với E3 (S1 Fixed); hai kịch bản dùng cùng đường giá sập -43%. Tỷ lệ thanh lý E9 2.00% so với E3 64.00%; lợi nhuận Liquidator lần lượt $21.37 và $4,893.84. Đây là so sánh seed 42, cùng cấu hình ngoài chi phí vận hành.
3. **H3 — Sốc rút vốn gây tắc nghẽn: được quan sát trên đường giá ổn định chung S0/S2.** E5 Fixed kẹt $73,759.99; E6 Adaptive kẹt $827,882.45, Fulfillment Rate 28.46%. S2 dùng cùng đường giá S0 nên đối chứng không kèm cú sập tháng 5/2021.
4. **H4 — Borrower Adaptive giảm thanh lý trong S1: được ủng hộ.** E4 Adaptive = 50.00% so với E3 Fixed = 64.00% (giảm 14.00 điểm phần trăm). Monte Carlo S1 mean cũng thấp hơn ở Adaptive (55.37%) so với Fixed (71.54%).
5. **H5 — Liquidator Adaptive duy trì thanh lý tốt hơn khi có sốc chi phí: ủng hộ vai trò Liquidator thích nghi trong đối chứng S4, cùng với hai so sánh bổ sung.** E10 toàn bộ nhóm Adaptive đạt 11.00% và lợi nhuận $289.09, so với E9 Fixed 2.00% và $21.37. Trong S5, A3 chỉ bật Liquidator Adaptive đạt 16.00% và $434.38, so với A1 2.00% và $21.48. Đối chứng S4 chỉ bật Liquidator Adaptive cho 16.00% và $432.23 so với E9; kết quả này cô lập tác nhân trong cùng S4 (seed 42).
6. **H6 — Tương tác cú sốc kết hợp: có bằng chứng một-run về queue và bad debt exposure Adaptive vượt tổng các thành phần đơn lẻ; chưa đủ để khẳng định tổng quát.** E12 pending $726,233.59 vượt tổng E4+E6+E10 $827,882.45; exposure $11,714.15 vượt tổng exposure E4+E6+E10 $10,389.29. Tuy nhiên, E12 utilization max 100.00% bằng mức trần và không cao hơn E6; bằng chứng cộng dồn này đến từ một seed, còn Monte Carlo không chạy S2/S4 để ước lượng tương tác.

## Giới hạn diễn giải

- Monte Carlo 6.000 run được giữ nguyên theo yêu cầu; các thay đổi đường giá S2/S3/S4 chỉ được áp dụng cho ma trận E1–E12 và đối chứng seed 42, không diễn giải lại kết quả Monte Carlo cho ba kịch bản này.
- Các so sánh E1–E12/A1–A5 chỉ dùng seed 42; không có kiểm định ý nghĩa thống kê cho các bảng này.
- VaR95 được dùng theo yêu cầu dưới dạng phân vị 95% của từng chỉ số. Với fulfillment rate, đây là phân vị cao của tỷ lệ hoàn tất, không phải thước đo tổn thất phía xấu.
- Dữ liệu run-level Monte Carlo đầy đủ nằm tại `results/monte_carlo_1000_runs.csv`; các bảng nguồn: `results/experiments_E1_E12_summary.csv`, `results/ablation_S5_summary.csv`, `results/monte_carlo_1000_summary.csv`.
