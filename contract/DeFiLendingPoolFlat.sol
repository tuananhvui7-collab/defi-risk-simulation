// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * ==============================================================================
 * FLATTENED DEFI LENDING PROTOCOL — SẴN SÀNG CHO REMIX IDE (remix.ethereum.org)
 * ==============================================================================
 * Bài tập lớn Blockchain: Nghiên cứu khả năng chống chịu rủi ro DeFi Lending.
 * 
 * Hướng dẫn nhanh trên Remix IDE:
 * 1. Mở https://remix.ethereum.org
 * 2. Tạo file mới: DeFiLendingPool.sol trong thư mục contracts/
 * 3. Copy toàn bộ nội dung file này paste vào Remix.
 * 4. Tab 'Solidity Compiler': Chọn version 0.8.20 (hoặc 0.8.24) -> Bấm 'Compile'.
 * 5. Tab 'Deploy & Run Transactions':
 *    - Bước 1: Deploy contract `MockUSDC`.
 *    - Bước 2: Deploy contract `MockPriceOracle` (mặc định giá ETH = 2.000 USD).
 *    - Bước 3: Deploy contract `InterestRateModel` (nhập tham số:
 *              _baseRate = 0,
 *              _slope1 = 40000000000000000 (4%),
 *              _slope2 = 750000000000000000 (75%),
 *              _uOpt = 800000000000000000 (80%),
 *              _reserveFactor = 100000000000000000 (10%)).
 *    - Bước 4: Deploy `DeFiLendingPool` với 3 địa chỉ vừa deploy ở trên!
 * 6. Tương tác và kiểm thử trực tiếp!
 * ==============================================================================
 */

// ==============================================================================
// 1. MOCK USDC TOKEN (6 DECIMALS)
// ==============================================================================

contract MockUSDC {
    string public name = "USD Coin";
    string public symbol = "USDC";
    uint8 public decimals = 6;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor() {
        _mint(msg.sender, 10_000_000 * 10**decimals);
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "ERC20: transfer exceeds balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount, "ERC20: transfer exceeds balance");
        if (allowance[from][msg.sender] != type(uint256).max) {
            require(allowance[from][msg.sender] >= amount, "ERC20: insufficient allowance");
            allowance[from][msg.sender] -= amount;
        }
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
        return true;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    function faucet() external {
        _mint(msg.sender, 10_000 * 10**decimals);
    }

    function _mint(address to, uint256 amount) internal {
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }
}

// ==============================================================================
// 2. MOCK PRICE ORACLE (8 DECIMALS - CHAINLINK STYLE)
// ==============================================================================

contract MockPriceOracle {
    address public owner;
    mapping(address => uint256) public assetPrices;
    address public constant ETH_ADDRESS = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;

    event AssetPriceUpdated(address indexed asset, uint256 oldPrice, uint256 newPrice, uint256 timestamp);

    modifier onlyOwner() {
        require(msg.sender == owner, "Oracle: not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        assetPrices[ETH_ADDRESS] = 2000 * 10**8; // $2,000.00
    }

    function setAssetPrice(address asset, uint256 price) external onlyOwner {
        require(price > 0, "Oracle: price > 0");
        uint256 oldPrice = assetPrices[asset];
        assetPrices[asset] = price;
        emit AssetPriceUpdated(asset, oldPrice, price, block.timestamp);
    }

    function setEthPrice(uint256 price) external onlyOwner {
        require(price > 0, "Oracle: price > 0");
        uint256 oldPrice = assetPrices[ETH_ADDRESS];
        assetPrices[ETH_ADDRESS] = price;
        emit AssetPriceUpdated(ETH_ADDRESS, oldPrice, price, block.timestamp);
    }

    function getAssetPrice(address asset) external view returns (uint256) {
        uint256 price = assetPrices[asset];
        require(price > 0, "Oracle: price not set");
        return price;
    }

    function getEthPrice() external view returns (uint256) {
        return assetPrices[ETH_ADDRESS];
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Oracle: zero address");
        owner = newOwner;
    }
}

// ==============================================================================
// 3. TWO-SLOPE (KINK) INTEREST RATE MODEL
// ==============================================================================

contract InterestRateModel {
    uint256 public constant SECONDS_PER_YEAR = 31536000;
    uint256 public constant WAD = 1e18;

    uint256 public immutable baseVariableBorrowRate; // Base rate (e.g. 0)
    uint256 public immutable variableRateSlope1;       // Slope1 (e.g. 0.04 * 1e18)
    uint256 public immutable variableRateSlope2;       // Slope2 (e.g. 0.75 * 1e18)
    uint256 public immutable optimalUtilizationRate;   // U_opt (e.g. 0.80 * 1e18)
    uint256 public immutable reserveFactor;            // Reserve Factor (e.g. 0.10 * 1e18)

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

    function calculateInterestRates(
        uint256 totalCash,
        uint256 totalDebt
    ) external view returns (uint256 borrowRatePerYear, uint256 supplyRatePerYear) {
        uint256 utilization = calculateUtilizationRate(totalCash, totalDebt);

        if (utilization <= optimalUtilizationRate) {
            borrowRatePerYear = baseVariableBorrowRate + (utilization * variableRateSlope1) / optimalUtilizationRate;
        } else {
            uint256 excessUtilization = utilization - optimalUtilizationRate;
            uint256 excessCoverage = WAD - optimalUtilizationRate;
            borrowRatePerYear = baseVariableBorrowRate + variableRateSlope1 + (excessUtilization * variableRateSlope2) / excessCoverage;
        }

        uint256 grossSupplyRate = (utilization * borrowRatePerYear) / WAD;
        supplyRatePerYear = (grossSupplyRate * (WAD - reserveFactor)) / WAD;
    }
}

// ==============================================================================
// 4. DEFI LENDING POOL (CORE PROTOCOL)
// ==============================================================================

contract DeFiLendingPool {
    uint256 public constant WAD = 1e18;
    uint256 public constant SECONDS_PER_YEAR = 31536000;
    uint256 public constant BPS_DIVISOR = 10000;

    // Protocol Risk Parameters
    uint256 public constant LIQUIDATION_THRESHOLD = 8000; // 80.00% LT
    uint256 public constant MAX_LTV = 8000;               // 80.00% Max LTV
    uint256 public constant LIQUIDATION_BONUS = 500;       // 5.00% Bonus
    uint256 public constant CLOSE_FACTOR = 5000;           // 50.00% Close Factor

    MockUSDC public immutable usdc;
    MockPriceOracle public oracle;
    InterestRateModel public interestRateModel;
    address public owner;

    // Dynamic Compound Indexes (Starts at 1e18)
    uint256 public borrowIndex = WAD;
    uint256 public liquidityIndex = WAD;
    uint256 public lastUpdateTimestamp;

    // Aggregates
    uint256 public totalCollateralETH;   // in wei
    uint256 public totalCashUSDC;        // in USDC (6 decimals)
    uint256 public totalScaledDebt;      // in WAD (18 decimals)
    uint256 public totalScaledSupply;    // in WAD (18 decimals)
    uint256 public totalBadDebtUSDC;     // in USDC (6 decimals)

    // User Position Mappings
    mapping(address => uint256) public userCollateralETH; // in wei
    mapping(address => uint256) public userScaledDebt;     // scaled debt
    mapping(address => uint256) public userScaledSupply;   // scaled supply

    uint256 private _reentrancyStatus = 1;

    // Events
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

    modifier nonReentrant() {
        require(_reentrancyStatus == 1, "REENTRANCY");
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

    function accrueInterest() public {
        uint256 timeDelta = block.timestamp - lastUpdateTimestamp;
        if (timeDelta == 0) return;

        uint256 currentDebt = getTotalDebtUSDC();
        (uint256 borrowRatePerYear, uint256 supplyRatePerYear) = interestRateModel.calculateInterestRates(
            totalCashUSDC,
            currentDebt
        );

        if (currentDebt > 0) {
            uint256 borrowFactor = (borrowRatePerYear * timeDelta) / SECONDS_PER_YEAR;
            borrowIndex += (borrowIndex * borrowFactor) / WAD;
        }

        uint256 currentSupply = getTotalSuppliedUSDC();
        if (currentSupply > 0) {
            uint256 supplyFactor = (supplyRatePerYear * timeDelta) / SECONDS_PER_YEAR;
            liquidityIndex += (liquidityIndex * supplyFactor) / WAD;
        }

        lastUpdateTimestamp = block.timestamp;
        emit InterestAccrued(borrowIndex, liquidityIndex, borrowRatePerYear, supplyRatePerYear);
    }

    function depositCollateral() external payable nonReentrant {
        require(msg.value > 0, "INVALID_AMOUNT");
        accrueInterest();

        userCollateralETH[msg.sender] += msg.value;
        totalCollateralETH += msg.value;

        emit DepositCollateral(msg.sender, msg.value, userCollateralETH[msg.sender]);
    }

    function withdrawCollateral(uint256 amountETH) external nonReentrant {
        require(amountETH > 0, "INVALID_AMOUNT");
        require(userCollateralETH[msg.sender] >= amountETH, "INSUFFICIENT_COLLATERAL");
        accrueInterest();

        userCollateralETH[msg.sender] -= amountETH;
        totalCollateralETH -= amountETH;

        if (getUserDebtUSDC(msg.sender) > 0) {
            require(getHealthFactor(msg.sender) >= WAD, "HEALTH_FACTOR_BELOW_ONE");
        }

        (bool success, ) = msg.sender.call{value: amountETH}("");
        require(success, "ETH_TRANSFER_FAILED");

        emit WithdrawCollateral(msg.sender, amountETH, userCollateralETH[msg.sender]);
    }

    function supplyUSDC(uint256 amountUSDC) external nonReentrant {
        require(amountUSDC > 0, "INVALID_AMOUNT");
        accrueInterest();

        require(usdc.transferFrom(msg.sender, address(this), amountUSDC), "USDC_TRANSFER_FAILED");

        uint256 scaledAmount = (amountUSDC * WAD) / liquidityIndex;
        userScaledSupply[msg.sender] += scaledAmount;
        totalScaledSupply += scaledAmount;
        totalCashUSDC += amountUSDC;

        emit SupplyUSDC(msg.sender, amountUSDC, getUserSuppliedUSDC(msg.sender));
    }

    function withdrawUSDC(uint256 amountUSDC) external nonReentrant {
        require(amountUSDC > 0, "INVALID_AMOUNT");
        accrueInterest();

        require(getUserSuppliedUSDC(msg.sender) >= amountUSDC, "INSUFFICIENT_SUPPLY");
        require(totalCashUSDC >= amountUSDC, "INSUFFICIENT_CASH");

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

    function borrowUSDC(uint256 amountUSDC) external nonReentrant {
        require(amountUSDC > 0, "INVALID_AMOUNT");
        require(totalCashUSDC >= amountUSDC, "INSUFFICIENT_CASH");
        accrueInterest();

        uint256 scaledAmount = (amountUSDC * WAD) / borrowIndex;
        userScaledDebt[msg.sender] += scaledAmount;
        totalScaledDebt += scaledAmount;
        totalCashUSDC -= amountUSDC;

        uint256 ethPrice = oracle.getEthPrice();
        uint256 collateralUSD = (userCollateralETH[msg.sender] * ethPrice) / 1e18;
        uint256 maxBorrowUSD = (collateralUSD * MAX_LTV) / BPS_DIVISOR;

        uint256 newTotalDebtUSD = (getUserDebtUSDC(msg.sender) * 10**8) / 10**6;
        require(newTotalDebtUSD <= maxBorrowUSD, "EXCEEDS_MAX_LTV");

        require(usdc.transfer(msg.sender, amountUSDC), "USDC_TRANSFER_FAILED");

        emit BorrowUSDC(msg.sender, amountUSDC, getUserDebtUSDC(msg.sender));
    }

    function repayUSDC(uint256 amountUSDC) external nonReentrant {
        require(amountUSDC > 0, "INVALID_AMOUNT");
        accrueInterest();

        uint256 currentDebt = getUserDebtUSDC(msg.sender);
        require(currentDebt > 0, "NO_DEBT");

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

    function liquidate(address borrower, uint256 debtToCover) external nonReentrant {
        require(borrower != msg.sender, "CANNOT_LIQUIDATE_SELF");
        require(debtToCover > 0, "INVALID_AMOUNT");
        accrueInterest();

        require(getHealthFactor(borrower) < WAD, "HEALTH_FACTOR_SAFE");

        uint256 totalDebt = getUserDebtUSDC(borrower);
        require(totalDebt > 0, "NO_DEBT");

        uint256 maxDebtRepay = (totalDebt * CLOSE_FACTOR) / BPS_DIVISOR;
        uint256 actualDebtRepay = debtToCover > maxDebtRepay ? maxDebtRepay : debtToCover;

        uint256 ethPrice = oracle.getEthPrice();
        uint256 debtUSD = (actualDebtRepay * 10**8) / 10**6;
        uint256 collateralValueUSDToSeize = (debtUSD * (BPS_DIVISOR + LIQUIDATION_BONUS)) / BPS_DIVISOR;
        uint256 ethToSeize = (collateralValueUSDToSeize * 1e18) / ethPrice;

        uint256 userCollateral = userCollateralETH[borrower];
        uint256 badDebtGenerated = 0;

        if (ethToSeize > userCollateral) {
            uint256 recoveredCollateralUSD = (userCollateral * ethPrice) / 1e18;
            uint256 recoveredUSDC = (recoveredCollateralUSD * 10**6) / 10**8;

            if (actualDebtRepay > recoveredUSDC) {
                badDebtGenerated = actualDebtRepay - recoveredUSDC;
                totalBadDebtUSDC += badDebtGenerated;
                emit BadDebtSocialized(badDebtGenerated, totalBadDebtUSDC);

                if (totalCashUSDC >= badDebtGenerated) {
                    totalCashUSDC -= badDebtGenerated;
                }
            }
            ethToSeize = userCollateral;
        }

        uint256 scaledDebtRepaid = (actualDebtRepay * WAD) / borrowIndex;
        if (scaledDebtRepaid > userScaledDebt[borrower]) {
            scaledDebtRepaid = userScaledDebt[borrower];
        }
        userScaledDebt[borrower] -= scaledDebtRepaid;
        totalScaledDebt -= scaledDebtRepaid;

        userCollateralETH[borrower] -= ethToSeize;
        totalCollateralETH -= ethToSeize;

        totalCashUSDC += actualDebtRepay;
        require(usdc.transferFrom(msg.sender, address(this), actualDebtRepay), "USDC_TRANSFER_FAILED");

        (bool success, ) = msg.sender.call{value: ethToSeize}("");
        require(success, "ETH_TRANSFER_FAILED");

        emit LiquidationCall(borrower, msg.sender, actualDebtRepay, ethToSeize, badDebtGenerated);
    }

    function getHealthFactor(address user) public view returns (uint256) {
        uint256 userDebt = getUserDebtUSDC(user);
        if (userDebt == 0) return type(uint256).max;

        uint256 ethPrice = oracle.getEthPrice();
        uint256 collateralUSD = (userCollateralETH[user] * ethPrice) / 1e18;
        uint256 liquidationValueUSD = (collateralUSD * LIQUIDATION_THRESHOLD) / BPS_DIVISOR;

        uint256 debtUSD = (userDebt * 10**8) / 10**6;
        if (debtUSD == 0) return type(uint256).max;

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

    function setOracle(address _newOracle) external onlyOwner {
        require(_newOracle != address(0), "INVALID_ORACLE");
        oracle = MockPriceOracle(_newOracle);
    }

    function setInterestRateModel(address _newModel) external onlyOwner {
        require(_newModel != address(0), "INVALID_MODEL");
        interestRateModel = InterestRateModel(_newModel);
    }

    receive() external payable {}
}
