// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./MockUSDC.sol";
import "./MockPriceOracle.sol";
import "./InterestRateModel.sol";

/**
 * @title DeFiLendingPool
 * @notice Production-grade DeFi Lending Pool inspired by Aave V3 core architecture.
 * Implements:
 * - Overcollateralized lending (ETH collateral, USDC borrow/supply)
 * - Two-slope Kink dynamic interest rate model with timestamp-based continuous compounding
 * - Real-time Health Factor calculation and decimal normalization
 * - Partial liquidation (50% Close Factor, 5% Bonus)
 * - Bad debt tracking and socialization (Haircut on lenders)
 * - Native ETH support with ReentrancyGuard
 */
contract DeFiLendingPool {
    // --- Constants & Precision ---
    uint256 public constant WAD = 1e18;
    uint256 public constant SECONDS_PER_YEAR = 31536000;
    uint256 public constant BPS_DIVISOR = 10000;

    // Protocol Risk Parameters (in Basis Points: 10000 = 100%)
    uint256 public constant LIQUIDATION_THRESHOLD = 8000; // 80.00% (LT)
    uint256 public constant MAX_LTV = 8000;               // 80.00% (Max initial borrow LTV)
    uint256 public constant LIQUIDATION_BONUS = 500;       // 5.00% bonus to liquidator
    uint256 public constant CLOSE_FACTOR = 5000;           // 50.00% max debt repaid per liquidation

    // --- External Dependencies ---
    MockUSDC public immutable usdc;
    MockPriceOracle public oracle;
    InterestRateModel public interestRateModel;
    address public owner;

    // --- State Accounting ---
    // Scaled indexes for continuous interest accrual (Starts at 1e18)
    uint256 public borrowIndex = WAD;
    uint256 public liquidityIndex = WAD;
    uint256 public lastUpdateTimestamp;

    // Protocol Aggregates
    uint256 public totalCollateralETH;   // in wei (18 decimals)
    uint256 public totalCashUSDC;        // in USDC units (6 decimals)
    uint256 public totalScaledDebt;      // in 18 decimals scaled units
    uint256 public totalScaledSupply;    // in 18 decimals scaled units
    uint256 public totalBadDebtUSDC;     // cumulative bad debt absorbed (6 decimals)

    // User State
    mapping(address => uint256) public userCollateralETH; // in wei
    mapping(address => uint256) public userScaledDebt;     // scaled debt
    mapping(address => uint256) public userScaledSupply;   // scaled supply

    // Reentrancy guard
    uint256 private _reentrancyStatus = 1;

    // --- Events ---
    event DepositCollateral(address indexed user, uint256 amountETH, uint256 newTotalCollateral);
    event WithdrawCollateral(address indexed user, uint256 amountETH, uint256 remainingCollateral);
    event SupplyUSDC(address indexed lender, uint256 amountUSDC, uint256 newSupplyBalance);
    event WithdrawUSDC(address indexed lender, uint256 amountUSDC, uint256 remainingSupply);
    event BorrowUSDC(address indexed borrower, uint256 amountUSDC, uint256 newDebtBalance);
    event RepayUSDC(address indexed borrower, address indexed repayer, uint256 amountUSDC, uint256 remainingDebt);
    event LiquidationCall(
        address indexed borrower,
        address indexed liquidator,
        uint256 debtRepaidUSDC,
        uint256 collateralSeizedETH,
        uint256 badDebtGeneratedUSDC
    );
    event BadDebtSocialized(uint256 badDebtAmountUSDC, uint256 newTotalBadDebt);
    event InterestAccrued(uint256 newBorrowIndex, uint256 newLiquidityIndex, uint256 borrowRate, uint256 supplyRate);

    // --- Modifiers ---
    modifier nonReentrant() {
        require(_reentrancyStatus == 1, "REENTRANCY_GUARD");
        _reentrancyStatus = 2;
        _;
        _reentrancyStatus = 1;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "NOT_OWNER");
        _;
    }

    constructor(
        address _usdcAddress,
        address _oracleAddress,
        address _interestRateModelAddress
    ) {
        owner = msg.sender;
        usdc = MockUSDC(_usdcAddress);
        oracle = MockPriceOracle(_oracleAddress);
        interestRateModel = InterestRateModel(_interestRateModelAddress);
        lastUpdateTimestamp = block.timestamp;
    }

    // =========================================================================
    // 1. INTEREST ACCRUAL ENGINE
    // =========================================================================

    /**
     * @notice Accrues interest continuously based on elapsed time and current market utilization.
     */
    function accrueInterest() public {
        uint256 timeDelta = block.timestamp - lastUpdateTimestamp;
        if (timeDelta == 0) {
            return;
        }

        uint256 currentDebt = getTotalDebtUSDC();
        (uint256 borrowRatePerYear, uint256 supplyRatePerYear) = interestRateModel.calculateInterestRates(
            totalCashUSDC,
            currentDebt
        );

        if (currentDebt > 0) {
            // newBorrowIndex = borrowIndex * (1 + borrowRatePerYear * timeDelta / SECONDS_PER_YEAR)
            uint256 borrowFactor = (borrowRatePerYear * timeDelta) / SECONDS_PER_YEAR;
            borrowIndex += (borrowIndex * borrowFactor) / WAD;
        }

        uint256 currentSupply = getTotalSuppliedUSDC();
        if (currentSupply > 0) {
            // newLiquidityIndex = liquidityIndex * (1 + supplyRatePerYear * timeDelta / SECONDS_PER_YEAR)
            uint256 supplyFactor = (supplyRatePerYear * timeDelta) / SECONDS_PER_YEAR;
            liquidityIndex += (liquidityIndex * supplyFactor) / WAD;
        }

        lastUpdateTimestamp = block.timestamp;
        emit InterestAccrued(borrowIndex, liquidityIndex, borrowRatePerYear, supplyRatePerYear);
    }

    // =========================================================================
    // 2. COLLATERAL (ETH) OPERATIONS
    // =========================================================================

    /**
     * @notice Deposit native ETH as collateral.
     */
    function depositCollateral() external payable nonReentrant {
        require(msg.value > 0, "INVALID_DEPOSIT_AMOUNT");
        accrueInterest();

        userCollateralETH[msg.sender] += msg.value;
        totalCollateralETH += msg.value;

        emit DepositCollateral(msg.sender, msg.value, userCollateralETH[msg.sender]);
    }

    /**
     * @notice Withdraw ETH collateral, ensuring Health Factor remains >= 1.0 after withdrawal.
     */
    function withdrawCollateral(uint256 amountETH) external nonReentrant {
        require(amountETH > 0, "INVALID_WITHDRAW_AMOUNT");
        require(userCollateralETH[msg.sender] >= amountETH, "INSUFFICIENT_COLLATERAL");
        accrueInterest();

        userCollateralETH[msg.sender] -= amountETH;
        totalCollateralETH -= amountETH;

        // Health factor check if borrower has active debt
        uint256 userDebt = getUserDebtUSDC(msg.sender);
        if (userDebt > 0) {
            uint256 hf = getHealthFactor(msg.sender);
            require(hf >= WAD, "HEALTH_FACTOR_BELOW_ONE");
        }

        (bool success, ) = msg.sender.call{value: amountETH}("");
        require(success, "ETH_TRANSFER_FAILED");

        emit WithdrawCollateral(msg.sender, amountETH, userCollateralETH[msg.sender]);
    }

    // =========================================================================
    // 3. LENDER (USDC) OPERATIONS
    // =========================================================================

    /**
     * @notice Supply USDC liquidity to the lending pool to earn interest.
     */
    function supplyUSDC(uint256 amountUSDC) external nonReentrant {
        require(amountUSDC > 0, "INVALID_SUPPLY_AMOUNT");
        accrueInterest();

        require(usdc.transferFrom(msg.sender, address(this), amountUSDC), "USDC_TRANSFER_FAILED");

        // scaledAmount = amount * WAD / liquidityIndex
        uint256 scaledAmount = (amountUSDC * WAD) / liquidityIndex;
        userScaledSupply[msg.sender] += scaledAmount;
        totalScaledSupply += scaledAmount;
        totalCashUSDC += amountUSDC;

        emit SupplyUSDC(msg.sender, amountUSDC, getUserSuppliedUSDC(msg.sender));
    }

    /**
     * @notice Withdraw supplied USDC from the pool.
     */
    function withdrawUSDC(uint256 amountUSDC) external nonReentrant {
        require(amountUSDC > 0, "INVALID_WITHDRAW_AMOUNT");
        accrueInterest();

        uint256 userSupply = getUserSuppliedUSDC(msg.sender);
        require(userSupply >= amountUSDC, "INSUFFICIENT_SUPPLY_BALANCE");
        require(totalCashUSDC >= amountUSDC, "INSUFFICIENT_POOL_CASH");

        uint256 scaledAmount = (amountUSDC * WAD) / liquidityIndex;
        if (scaledAmount > userScaledSupply[msg.sender]) {
            scaledAmount = userScaledSupply[msg.sender];
        }

        userScaledSupply[msg.sender] -= scaledAmount;
        totalScaledSupply -= scaledAmount;
        totalCashUSDC -= amountUSDC;

        require(usdc.transfer(msg.sender, amountUSDC), "USDC_TRANSFER_FAILED");

        emit WithdrawUSDC(msg.sender, amountUSDC, getUserSuppliedUSDC(msg.sender));
    }

    // =========================================================================
    // 4. BORROWER (USDC) OPERATIONS
    // =========================================================================

    /**
     * @notice Borrow USDC against ETH collateral.
     */
    function borrowUSDC(uint256 amountUSDC) external nonReentrant {
        require(amountUSDC > 0, "INVALID_BORROW_AMOUNT");
        require(totalCashUSDC >= amountUSDC, "INSUFFICIENT_POOL_CASH");
        accrueInterest();

        uint256 scaledAmount = (amountUSDC * WAD) / borrowIndex;
        userScaledDebt[msg.sender] += scaledAmount;
        totalScaledDebt += scaledAmount;
        totalCashUSDC -= amountUSDC;

        // Verify position health against MAX_LTV
        uint256 ethPrice = oracle.getEthPrice(); // 8 decimals
        uint256 collateralUSD = (userCollateralETH[msg.sender] * ethPrice) / 1e18; // 8 decimals
        uint256 maxBorrowUSD = (collateralUSD * MAX_LTV) / BPS_DIVISOR; // 8 decimals

        uint256 newTotalDebtUSD = (getUserDebtUSDC(msg.sender) * 10**8) / 10**6; // Convert 6 decimals USDC to 8 decimals USD
        require(newTotalDebtUSD <= maxBorrowUSD, "EXCEEDS_MAX_LTV");

        require(usdc.transfer(msg.sender, amountUSDC), "USDC_TRANSFER_FAILED");

        emit BorrowUSDC(msg.sender, amountUSDC, getUserDebtUSDC(msg.sender));
    }

    /**
     * @notice Repay borrowed USDC.
     */
    function repayUSDC(uint256 amountUSDC) external nonReentrant {
        require(amountUSDC > 0, "INVALID_REPAY_AMOUNT");
        accrueInterest();

        uint256 currentDebt = getUserDebtUSDC(msg.sender);
        require(currentDebt > 0, "NO_ACTIVE_DEBT");

        uint256 repayAmount = amountUSDC > currentDebt ? currentDebt : amountUSDC;
        require(usdc.transferFrom(msg.sender, address(this), repayAmount), "USDC_TRANSFER_FAILED");

        uint256 scaledAmount = (repayAmount * WAD) / borrowIndex;
        if (scaledAmount > userScaledDebt[msg.sender]) {
            scaledAmount = userScaledDebt[msg.sender];
        }

        userScaledDebt[msg.sender] -= scaledAmount;
        totalScaledDebt -= scaledAmount;
        totalCashUSDC += repayAmount;

        emit RepayUSDC(msg.sender, msg.sender, repayAmount, getUserDebtUSDC(msg.sender));
    }

    // =========================================================================
    // 5. LIQUIDATION ENGINE & BAD DEBT SOCIALIZATION
    // =========================================================================

    /**
     * @notice Liquidates an undercollateralized position (HF < 1.0).
     * @dev Implements 50% Close Factor and 5% Liquidation Bonus.
     * If collateral is insufficient, socializes the remaining bad debt across lenders.
     * @param borrower The address of the borrower to liquidate
     * @param debtToCover The desired amount of debt in USDC to repay
     */
    function liquidate(address borrower, uint256 debtToCover) external nonReentrant {
        require(borrower != msg.sender, "CANNOT_LIQUIDATE_SELF");
        require(debtToCover > 0, "INVALID_DEBT_TO_COVER");
        accrueInterest();

        uint256 hf = getHealthFactor(borrower);
        require(hf < WAD, "HEALTH_FACTOR_SAFE");

        uint256 totalDebt = getUserDebtUSDC(borrower);
        require(totalDebt > 0, "NO_DEBT_TO_LIQUIDATE");

        // 1. Enforce Close Factor (max 50% debt repaid per liquidation)
        uint256 maxDebtRepay = (totalDebt * CLOSE_FACTOR) / BPS_DIVISOR;
        uint256 actualDebtRepay = debtToCover > maxDebtRepay ? maxDebtRepay : debtToCover;

        // 2. Calculate ETH collateral to seize with 5% liquidation bonus
        // ETH to seize = (debtRepayUSD * (1 + bonus)) / ethPrice
        // debtRepay is 6 decimals, Price is 8 decimals, ETH is 18 decimals
        uint256 ethPrice = oracle.getEthPrice(); // 8 decimals
        uint256 debtUSD = (actualDebtRepay * 10**8) / 10**6; // 8 decimals
        uint256 collateralValueUSDToSeize = (debtUSD * (BPS_DIVISOR + LIQUIDATION_BONUS)) / BPS_DIVISOR; // 8 decimals
        uint256 ethToSeize = (collateralValueUSDToSeize * 1e18) / ethPrice; // 18 decimals (wei)

        uint256 userCollateral = userCollateralETH[borrower];
        uint256 badDebtGenerated = 0;

        if (ethToSeize > userCollateral) {
            // Position is insolvent (Collateral exhausted) -> Record Bad Debt
            uint256 recoveredCollateralUSD = (userCollateral * ethPrice) / 1e18; // 8 decimals
            uint256 recoveredUSDC = (recoveredCollateralUSD * 10**6) / 10**8;   // 6 decimals

            if (actualDebtRepay > recoveredUSDC) {
                badDebtGenerated = actualDebtRepay - recoveredUSDC;
                totalBadDebtUSDC += badDebtGenerated;
                emit BadDebtSocialized(badDebtGenerated, totalBadDebtUSDC);

                // Socialize loss: deduct from total supply
                if (totalCashUSDC >= badDebtGenerated) {
                    totalCashUSDC -= badDebtGenerated;
                }
            }
            ethToSeize = userCollateral;
        }

        // 3. Update borrower balances
        uint256 scaledDebtRepaid = (actualDebtRepay * WAD) / borrowIndex;
        if (scaledDebtRepaid > userScaledDebt[borrower]) {
            scaledDebtRepaid = userScaledDebt[borrower];
        }
        userScaledDebt[borrower] -= scaledDebtRepaid;
        totalScaledDebt -= scaledDebtRepaid;

        userCollateralETH[borrower] -= ethToSeize;
        totalCollateralETH -= ethToSeize;

        // 4. Settle funds with liquidator
        totalCashUSDC += actualDebtRepay;
        require(usdc.transferFrom(msg.sender, address(this), actualDebtRepay), "USDC_TRANSFER_FAILED");

        (bool success, ) = msg.sender.call{value: ethToSeize}("");
        require(success, "ETH_TRANSFER_TO_LIQUIDATOR_FAILED");

        emit LiquidationCall(borrower, msg.sender, actualDebtRepay, ethToSeize, badDebtGenerated);
    }

    // =========================================================================
    // 6. VIEW & DIAGNOSTIC FUNCTIONS
    // =========================================================================

    /**
     * @notice Calculates the current Health Factor for a user (18 decimals, 1e18 = 1.0).
     */
    function getHealthFactor(address user) public view returns (uint256) {
        uint256 userDebt = getUserDebtUSDC(user);
        if (userDebt == 0) {
            return type(uint256).max;
        }

        uint256 ethPrice = oracle.getEthPrice(); // 8 decimals
        uint256 collateralUSD = (userCollateralETH[user] * ethPrice) / 1e18; // 8 decimals
        uint256 liquidationValueUSD = (collateralUSD * LIQUIDATION_THRESHOLD) / BPS_DIVISOR; // 8 decimals

        uint256 debtUSD = (userDebt * 10**8) / 10**6; // 8 decimals
        if (debtUSD == 0) {
            return type(uint256).max;
        }

        // HF = (liquidationValueUSD * 1e18) / debtUSD
        return (liquidationValueUSD * WAD) / debtUSD;
    }

    function getUserDebtUSDC(address user) public view returns (uint256) {
        if (userScaledDebt[user] == 0) return 0;
        return (userScaledDebt[user] * borrowIndex) / WAD;
    }

    function getUserSuppliedUSDC(address user) public view returns (uint256) {
        if (userScaledSupply[user] == 0) return 0;
        return (userScaledSupply[user] * liquidityIndex) / WAD;
    }

    function getTotalDebtUSDC() public view returns (uint256) {
        if (totalScaledDebt == 0) return 0;
        return (totalScaledDebt * borrowIndex) / WAD;
    }

    function getTotalSuppliedUSDC() public view returns (uint256) {
        if (totalScaledSupply == 0) return 0;
        return (totalScaledSupply * liquidityIndex) / WAD;
    }

    /**
     * @notice Returns comprehensive account metrics for UI or automated tests.
     */
    function getUserAccountData(address user)
        external
        view
        returns (
            uint256 totalCollateralETHAmount,
            uint256 totalCollateralUSD,
            uint256 totalDebtUSDCAmount,
            uint256 totalDebtUSD,
            uint256 availableBorrowUSD,
            uint256 healthFactor,
            bool isLiquidatable
        )
    {
        totalCollateralETHAmount = userCollateralETH[user];
        uint256 ethPrice = oracle.getEthPrice();
        totalCollateralUSD = (totalCollateralETHAmount * ethPrice) / 1e18;

        totalDebtUSDCAmount = getUserDebtUSDC(user);
        totalDebtUSD = (totalDebtUSDCAmount * 10**8) / 10**6;

        uint256 maxBorrowUSD = (totalCollateralUSD * MAX_LTV) / BPS_DIVISOR;
        availableBorrowUSD = maxBorrowUSD > totalDebtUSD ? maxBorrowUSD - totalDebtUSD : 0;

        healthFactor = getHealthFactor(user);
        isLiquidatable = healthFactor < WAD;
    }

    /**
     * @notice Returns complete pool telemetry for dashboard visualization.
     */
    function getPoolData()
        external
        view
        returns (
            uint256 collateralETH,
            uint256 cashUSDC,
            uint256 debtUSDC,
            uint256 suppliedUSDC,
            uint256 utilizationRate,
            uint256 currentBorrowRatePerYear,
            uint256 currentSupplyRatePerYear,
            uint256 totalBadDebt
        )
    {
        collateralETH = totalCollateralETH;
        cashUSDC = totalCashUSDC;
        debtUSDC = getTotalDebtUSDC();
        suppliedUSDC = getTotalSuppliedUSDC();

        (currentBorrowRatePerYear, currentSupplyRatePerYear) = interestRateModel.calculateInterestRates(
            cashUSDC,
            debtUSDC
        );
        utilizationRate = interestRateModel.calculateUtilizationRate(cashUSDC, debtUSDC);
        totalBadDebt = totalBadDebtUSDC;
    }

    // =========================================================================
    // 7. ADMIN CONFIGURATION
    // =========================================================================

    function setOracle(address _newOracle) external onlyOwner {
        require(_newOracle != address(0), "INVALID_ORACLE");
        oracle = MockPriceOracle(_newOracle);
    }

    function setInterestRateModel(address _newModel) external onlyOwner {
        require(_newModel != address(0), "INVALID_MODEL");
        interestRateModel = InterestRateModel(_newModel);
    }

    // Allow contract to receive ETH
    receive() external payable {}
}
