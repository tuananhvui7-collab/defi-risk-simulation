// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title InterestRateModel
 * @notice Two-slope (Kink) interest rate strategy based on Aave V3 core mechanics.
 * Parameters:
 * - Base Rate: 0.00%
 * - Slope 1: 4.00%
 * - Slope 2: 75.00%
 * - Optimal Utilization (U_opt): 80.00%
 * - Reserve Factor: 10.00%
 *
 * Rates are expressed in RAY (1e27) or WAD (1e18) per second for continuous compounding.
 */
contract InterestRateModel {
    uint256 public constant SECONDS_PER_YEAR = 31536000;
    uint256 public constant WAD = 1e18;

    // Rates in WAD per year (1e18 = 100% APR)
    uint256 public immutable baseVariableBorrowRate; // 0%
    uint256 public immutable variableRateSlope1;       // 4% (0.04 * 1e18)
    uint256 public immutable variableRateSlope2;       // 75% (0.75 * 1e18)
    uint256 public immutable optimalUtilizationRate;   // 80% (0.80 * 1e18)
    uint256 public immutable reserveFactor;            // 10% (0.10 * 1e18)

    constructor(
        uint256 _baseRate,
        uint256 _slope1,
        uint256 _slope2,
        uint256 _uOpt,
        uint256 _reserveFactor
    ) {
        baseVariableBorrowRate = _baseRate;
        variableRateSlope1 = _slope1;
        variableRateSlope2 = _slope2;
        optimalUtilizationRate = _uOpt;
        reserveFactor = _reserveFactor;
    }

    /// @notice Default constructor with standard parameters from project spec
    function createDefaultModel() external pure returns (InterestRateModel) {
        return new InterestRateModel(
            0,                     // 0% Base
            0.04 * 1e18,           // 4% Slope 1
            0.75 * 1e18,           // 75% Slope 2
            0.80 * 1e18,           // 80% U_opt
            0.10 * 1e18            // 10% Reserve Factor
        );
    }

    /**
     * @notice Calculates the current utilization rate U = totalDebt / (totalCash + totalDebt)
     * @return utilization Utilization rate in WAD (1e18 = 100%)
     */
    function calculateUtilizationRate(
        uint256 totalCash,
        uint256 totalDebt
    ) public pure returns (uint256) {
        if (totalDebt == 0) {
            return 0;
        }
        uint256 totalLiquidity = totalCash + totalDebt;
        return (totalDebt * WAD) / totalLiquidity;
    }

    /**
     * @notice Calculates the annual borrow rate and supply rate based on current utilization.
     * @param totalCash Available cash in pool
     * @param totalDebt Total outstanding borrowed debt
     * @return borrowRatePerYear Annual borrow rate (WAD)
     * @return supplyRatePerYear Annual supply rate (WAD)
     */
    function calculateInterestRates(
        uint256 totalCash,
        uint256 totalDebt
    ) external view returns (uint256 borrowRatePerYear, uint256 supplyRatePerYear) {
        uint256 utilization = calculateUtilizationRate(totalCash, totalDebt);

        if (utilization <= optimalUtilizationRate) {
            // R_borrow = Base + (U / U_opt) * Slope1
            borrowRatePerYear = baseVariableBorrowRate + (utilization * variableRateSlope1) / optimalUtilizationRate;
        } else {
            // R_borrow = Base + Slope1 + ((U - U_opt) / (1 - U_opt)) * Slope2
            uint256 excessUtilization = utilization - optimalUtilizationRate;
            uint256 excessCoverage = WAD - optimalUtilizationRate;
            borrowRatePerYear = baseVariableBorrowRate + variableRateSlope1 + (excessUtilization * variableRateSlope2) / excessCoverage;
        }

        // R_supply = U * R_borrow * (1 - Reserve_Factor)
        uint256 grossSupplyRate = (utilization * borrowRatePerYear) / WAD;
        supplyRatePerYear = (grossSupplyRate * (WAD - reserveFactor)) / WAD;
    }
}
