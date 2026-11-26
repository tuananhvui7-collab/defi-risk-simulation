"""Build the verified-results report from the latest generated CSV outputs."""

import os
import sys

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

RESULTS = os.path.join(PROJECT_ROOT, "results")
METRICS = {
    "liquidation_rate_pct": "Tỷ lệ thanh lý (%)",
    "liquidation_coverage_ratio": "Liquidation Coverage Ratio",
    "total_bad_debt_exposure_usdc": "Tổng Bad Debt Exposure (USDC)",
    "pending_withdrawals_usdc": "Tiền rút còn kẹt cuối phiên (USDC)",
    "withdrawal_fulfillment_rate": "Withdrawal Fulfillment Rate",
}


def fmt(value, column=""):
    if pd.isna(value):
        return ""
    if isinstance(value, (int,)):
        return str(value)
    if isinstance(value, (float,)) or hasattr(value, "item"):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        if not pd.notna(number):
            return ""
        if "ratio" in column.lower() or "fulfillment_rate" in column.lower():
            return f"{number:.6f}"
        if column.startswith("n_") or column in {"unliquidated_positions_end", "Số lần chạy (N)"}:
            return f"{number:.0f}"
        return f"{number:,.2f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(frame: pd.DataFrame) -> str:
    headers = [str(c) for c in frame.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in frame.itertuples(index=False, name=None):
        cells = [fmt(value, headers[i]) for i, value in enumerate(row)]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def build_report() -> str:
    matrix = pd.read_csv(os.path.join(RESULTS, "experiments_E1_E12_summary.csv"), encoding="utf-8-sig")
    ablation = pd.read_csv(os.path.join(RESULTS, "ablation_S5_summary.csv"), encoding="utf-8-sig")
    s4_control = pd.read_csv(os.path.join(RESULTS, "s4_liquidator_adaptive_only.csv"), encoding="utf-8-sig")
    mc_runs = pd.read_csv(os.path.join(RESULTS, "monte_carlo_1000_runs.csv"), encoding="utf-8-sig")
    mc = pd.read_csv(os.path.join(RESULTS, "monte_carlo_1000_summary.csv"), encoding="utf-8-sig")

    assert len(matrix) == 12, f"Expected 12 matrix rows, got {len(matrix)}"
    assert len(ablation) == 5, f"Expected 5 ablation rows, got {len(ablation)}"
    assert len(mc_runs) == 6000, f"Expected 6000 Monte Carlo runs, got {len(mc_runs)}"
    counts = mc_runs.groupby(["scenario", "strategy"]).size()
    assert len(counts) == 6 and (counts == 1000).all(), f"Unexpected Monte Carlo groups: {counts.to_dict()}"
    assert mc_runs["seed"].min() == 42 and mc_runs["seed"].max() == 1041

    matrix_by_id = matrix.set_index("Mã thực nghiệm")
    ablation_by_id = ablation.set_index("Mã thực nghiệm")
    mc_by_group = mc.set_index(["Kịch bản", "Chiến lược"])

    e1 = matrix_by_id.loc["E1"]
    e3 = matrix_by_id.loc["E3"]
    e4 = matrix_by_id.loc["E4"]
    e5 = matrix_by_id.loc["E5"]
    e6 = matrix_by_id.loc["E6"]
    e9 = matrix_by_id.loc["E9"]
    e10 = matrix_by_id.loc["E10"]
    e11 = matrix_by_id.loc["E11"]
    e12 = matrix_by_id.loc["E12"]
    a1 = ablation_by_id.loc["A1"]
    a3 = ablation_by_id.loc["A3"]
    s4_liq = s4_control.iloc[0]

    adaptive_single_pending = sum(float(matrix_by_id.loc[exp, "Rút tiền bị kẹt (USDC)"]) for exp in ("E4", "E6", "E10"))
    adaptive_single_exposure = sum(float(matrix_by_id.loc[exp, "total_bad_debt_exposure_usdc"]) for exp in ("E4", "E6", "E10"))
    e12_pending = float(e12["Rút tiền bị kẹt (USDC)"])
    e12_exposure = float(e12["total_bad_debt_exposure_usdc"])

    e3_liq_rate = float(e3["Tỷ lệ thanh lý (%)"])
    e9_liq_rate = float(e9["Tỷ lệ thanh lý (%)"])
    e3_profit = float(e3["Lợi nhuận Liquidator ($)"])
    e9_profit = float(e9["Lợi nhuận Liquidator ($)"])
    if e9_liq_rate < e3_liq_rate and e9_profit < e3_profit:
        h2_verdict = "được ủng hộ"
    elif e9_liq_rate > e3_liq_rate and e9_profit > e3_profit:
        h2_verdict = "không được ủng hộ"
    else:
        h2_verdict = "có kết quả hỗn hợp"
    control_rate = float(s4_liq["Tỷ lệ thanh lý (%)"])
    control_profit = float(s4_liq["Lợi nhuận Liquidator ($)"])
    h5_control_verdict = (
        "ủng hộ vai trò Liquidator thích nghi"
        if control_rate > e9_liq_rate or control_profit > e9_profit
        else "không cho thấy cải thiện so với Fixed"
    )

    mc_long_rows = []
    for _, row in mc.iterrows():
        scenario, strategy = row["Kịch bản"], row["Chiến lược"]
        for metric, label in METRICS.items():
            mc_long_rows.append({
                "Kịch bản": scenario,
                "Chiến lược": strategy,
                "Chỉ số": label,
                "N": int(row["Số lần chạy (N)"]),
                "Mean": row[f"{metric}_mean"],
                "Median": row[f"{metric}_median"],
                "Std mẫu": row[f"{metric}_std"],
                "VaR95 / phân vị 95%": row[f"{metric}_var95"],
            })
    mc_table = pd.DataFrame(mc_long_rows)

    report = [
        "# Báo cáo dữ liệu mô phỏng đã kiểm chứng",
        "",
        "Báo cáo này được dựng trực tiếp từ các CSV vừa tạo bởi mã mô phỏng trong repository. Các kết luận dưới đây mô tả kết quả của mô hình và cấu hình đã chạy; chúng không phải khẳng định về toàn bộ thị trường DeFi ngoài đời.",
        "",
        "## Cấu hình và kiểm tra dữ liệu",
        "",
        "- Ma trận E1–E12: 12 dòng, 100 borrower/run, 168 bước, seed 42.",
        "- S5 Ablation: 5 cấu hình, 100 borrower/run, 168 bước, cùng seed 42.",
        "- Monte Carlo: 6.000 run; S0/S1/S5 × Fixed/Adaptive, mỗi nhóm đúng 1.000 run, 50 borrower/run; seed 42–1041. Các chiến lược cùng dùng cùng dãy seed để tạo đối sánh theo seed.",
        "- VaR95 trong bảng là phân vị thực nghiệm 95% của giá trị run-level. Độ lệch chuẩn là độ lệch chuẩn mẫu (`ddof=1`). Với Liquidation Coverage Ratio, mô hình trả 1.0 khi không có borrower từng HF < 1.0.",
        "- Bad Debt Exposure cuối phiên = Realized Bad Debt + Unrealized Bad Debt cuối phiên. Các cột peak trong bảng E/Ablation là mức đỉnh được theo dõi theo thời gian; bảng Monte Carlo dùng exposure cuối phiên.",
        "- Số tiền rút bị kẹt là số dư còn trong queue ở cuối phiên; Fulfillment Rate = USDC đã giải ngân / USDC được yêu cầu.",
        "",
        "## Bảng 1 — Ma trận E1–E12 (seed 42)",
        "",
        markdown_table(matrix),
        "",
        "## Bảng 2 — S5 Ablation Study (seed 42)",
        "",
        markdown_table(ablation),
        "",
        "## Bảng 2b — Đối chứng S4 chỉ Liquidator Adaptive (seed 42)",
        "",
        markdown_table(s4_control),
        "",
        "## Bảng 3 — Monte Carlo (1.000 run mỗi kịch bản/chiến lược)",
        "",
        markdown_table(mc_table),
        "",
        "## Đánh giá giả thuyết H1–H6 theo kết quả vừa chạy",
        "",
        f"1. **H1 — Giá ETH giảm làm tăng thanh lý: được ủng hộ trong mô hình.** E1/S0 Fixed = {e1['Tỷ lệ thanh lý (%)']:.2f}%, E3/S1 Fixed = {e3['Tỷ lệ thanh lý (%)']:.2f}%. Monte Carlo Fixed cũng tăng từ S0 mean {mc_by_group.loc[('S0', 'Fixed'), 'liquidation_rate_pct_mean']:.2f}% lên S1 mean {mc_by_group.loc[('S1', 'Fixed'), 'liquidation_rate_pct_mean']:.2f}%. Đây là đối chứng rõ giữa hai đường giá đã tách.",
        f"2. **H2 — Sốc chi phí làm giảm thanh lý/lợi nhuận: {h2_verdict}.** Đối chứng đúng là E9 (S4 Fixed: gas $100, trượt giá 5x) với E3 (S1 Fixed); hai kịch bản dùng cùng đường giá sập -43%. Tỷ lệ thanh lý E9 {e9_liq_rate:.2f}% so với E3 {e3_liq_rate:.2f}%; lợi nhuận Liquidator lần lượt ${e9_profit:,.2f} và ${e3_profit:,.2f}. Đây là so sánh seed 42, cùng cấu hình ngoài chi phí vận hành.",
        f"3. **H3 — Sốc rút vốn gây tắc nghẽn: được quan sát trên đường giá ổn định chung S0/S2.** E5 Fixed kẹt ${e5['Rút tiền bị kẹt (USDC)']:,.2f}; E6 Adaptive kẹt ${e6['Rút tiền bị kẹt (USDC)']:,.2f}, Fulfillment Rate {e6['withdrawal_fulfillment_rate']:.2%}. S2 dùng cùng đường giá S0 nên đối chứng không kèm cú sập tháng 5/2021.",
        f"4. **H4 — Borrower Adaptive giảm thanh lý trong S1: được ủng hộ.** E4 Adaptive = {e4['Tỷ lệ thanh lý (%)']:.2f}% so với E3 Fixed = {e3['Tỷ lệ thanh lý (%)']:.2f}% (giảm {e3['Tỷ lệ thanh lý (%)'] - e4['Tỷ lệ thanh lý (%)']:.2f} điểm phần trăm). Monte Carlo S1 mean cũng thấp hơn ở Adaptive ({mc_by_group.loc[('S1', 'Adaptive'), 'liquidation_rate_pct_mean']:.2f}%) so với Fixed ({mc_by_group.loc[('S1', 'Fixed'), 'liquidation_rate_pct_mean']:.2f}%).",
        f"5. **H5 — Liquidator Adaptive duy trì thanh lý tốt hơn khi có sốc chi phí: {h5_control_verdict} trong đối chứng S4, cùng với hai so sánh bổ sung.** E10 toàn bộ nhóm Adaptive đạt {e10['Tỷ lệ thanh lý (%)']:.2f}% và lợi nhuận ${e10['Lợi nhuận Liquidator ($)']:,.2f}, so với E9 Fixed {e9['Tỷ lệ thanh lý (%)']:.2f}% và ${e9['Lợi nhuận Liquidator ($)']:,.2f}. Trong S5, A3 chỉ bật Liquidator Adaptive đạt {a3['Tỷ lệ thanh lý (%)']:.2f}% và ${a3['Lợi nhuận Liquidator ($)']:,.2f}, so với A1 {a1['Tỷ lệ thanh lý (%)']:.2f}% và ${a1['Lợi nhuận Liquidator ($)']:,.2f}. Đối chứng S4 chỉ bật Liquidator Adaptive cho {control_rate:.2f}% và ${control_profit:,.2f} so với E9; kết quả này cô lập tác nhân trong cùng S4 (seed 42).",
        f"6. **H6 — Tương tác cú sốc kết hợp: có bằng chứng một-run về queue và bad debt exposure Adaptive vượt tổng các thành phần đơn lẻ; chưa đủ để khẳng định tổng quát.** E12 pending ${e12_pending:,.2f} vượt tổng E4+E6+E10 ${adaptive_single_pending:,.2f}; exposure ${e12_exposure:,.2f} vượt tổng exposure E4+E6+E10 ${adaptive_single_exposure:,.2f}. Tuy nhiên, E12 utilization max {e12['Utilization max (%)']:.2f}% bằng mức trần và không cao hơn E6; bằng chứng cộng dồn này đến từ một seed, còn Monte Carlo không chạy S2/S4 để ước lượng tương tác.",
        "",
        "## Giới hạn diễn giải",
        "",
        "- Monte Carlo 6.000 run được giữ nguyên theo yêu cầu; các thay đổi đường giá S2/S3/S4 chỉ được áp dụng cho ma trận E1–E12 và đối chứng seed 42, không diễn giải lại kết quả Monte Carlo cho ba kịch bản này.",
        "- Các so sánh E1–E12/A1–A5 chỉ dùng seed 42; không có kiểm định ý nghĩa thống kê cho các bảng này.",
        "- VaR95 được dùng theo yêu cầu dưới dạng phân vị 95% của từng chỉ số. Với fulfillment rate, đây là phân vị cao của tỷ lệ hoàn tất, không phải thước đo tổn thất phía xấu.",
        "- Dữ liệu run-level Monte Carlo đầy đủ nằm tại `results/monte_carlo_1000_runs.csv`; các bảng nguồn: `results/experiments_E1_E12_summary.csv`, `results/ablation_S5_summary.csv`, `results/monte_carlo_1000_summary.csv`.",
    ]
    return "\n".join(report) + "\n"


if __name__ == "__main__":
    output_path = os.path.join(RESULTS, "report_data_verified.md")
    with open(output_path, "w", encoding="utf-8") as report_file:
        report_file.write(build_report())
    print(f"Wrote verified report: {output_path}")
