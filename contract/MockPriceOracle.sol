// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AggregatorV3Interface
 * @notice Chuẩn giao diện Chainlink Data Feeds trên Ethereum / Sepolia
 */
interface AggregatorV3Interface {
    function decimals() external view returns (uint8);
    function description() external view returns (string memory);
    function version() external view returns (uint256);
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

/**
 * @title MockPriceOracle
 * @notice Oracle giá tài sản thực tế cho DeFi Lending Pool.
 * Hỗ trợ 2 chế độ:
 * 1. Chế độ Chainlink Live: Đọc trực tiếp giá ETH/USD theo thời gian thực trên mạng Sepolia Testnet
 *    (Địa chỉ Sepolia chính thức: 0x694AA1769357215DE4FAC081bf1f309aDC325306).
 * 2. Chế độ Dữ liệu Lịch sử Binance: Nạp trực tiếp chuỗi nến sụp đổ 168h thực tế từ Binance Vision.
 * 
 * Đơn vị giá: Chuẩn 8 chữ số thập phân (Chainlink Standard, 1 USD = 10^8).
 */
contract MockPriceOracle {
    address public owner;
    
    // Sepolia Chainlink ETH/USD aggregator address
    AggregatorV3Interface public chainlinkEthFeed;
    bool public useChainlinkLive;
    
    // Mapping: Địa chỉ tài sản => Giá theo chuẩn 8 decimals
    mapping(address => uint256) public assetPrices;
    
    // Địa chỉ quy ước cho Native ETH
    address public constant ETH_ADDRESS = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;

    event AssetPriceUpdated(address indexed asset, uint256 oldPrice, uint256 newPrice, uint256 timestamp);
    event ChainlinkLiveToggled(bool enabled, address indexed feedAddress);

    modifier onlyOwner() {
        require(msg.sender == owner, "Oracle: caller is not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        
        // Khởi tạo giá ETH thực tế ban đầu từ Binance Vision (Tháng 5/2021): $3,465.98 (8 decimals)
        // Giá trị: 3,465.98 * 10^8 = 346,598,000,000
        assetPrices[ETH_ADDRESS] = 346598000000;
        
        // Cấu hình sẵn Aggregator ETH/USD chính thức của Chainlink trên Sepolia Testnet
        chainlinkEthFeed = AggregatorV3Interface(0x694AA1769357215DE4FAC081bf1f309aDC325306);
        useChainlinkLive = false;
    }

    /**
     * @notice Bật/tắt đọc giá Live từ Chainlink Oracle trên mạng Sepolia
     */
    function setUseChainlinkLive(bool _useLive) external onlyOwner {
        useChainlinkLive = _useLive;
        emit ChainlinkLiveToggled(_useLive, address(chainlinkEthFeed));
    }

    /**
     * @notice Cập nhật địa chỉ Chainlink Feed (nếu deploy sang mạng khác như Arbitrum, Optimism...)
     */
    function setChainlinkFeed(address _feedAddress) external onlyOwner {
        require(_feedAddress != address(0), "Oracle: invalid feed address");
        chainlinkEthFeed = AggregatorV3Interface(_feedAddress);
    }

    /**
     * @notice Cập nhật giá ETH thật theo từng giờ từ dữ liệu Binance Vision
     */
    function setEthPrice(uint256 price) external onlyOwner {
        require(price > 0, "Oracle: price must be positive");
        uint256 oldPrice = assetPrices[ETH_ADDRESS];
        assetPrices[ETH_ADDRESS] = price;
        emit AssetPriceUpdated(ETH_ADDRESS, oldPrice, price, block.timestamp);
    }

    /**
     * @notice Nạp một mảng giá nến Binance liên tục để chạy mô phỏng on-chain tiết kiệm gas
     */
    function setAssetPrice(address asset, uint256 price) external onlyOwner {
        require(price > 0, "Oracle: price must be positive");
        uint256 oldPrice = assetPrices[asset];
        assetPrices[asset] = price;
        emit AssetPriceUpdated(asset, oldPrice, price, block.timestamp);
    }

    /**
     * @notice Lấy giá ETH hiện tại (8 decimals).
     * Ưu tiên Chainlink Live nếu bật useChainlinkLive, ngược lại lấy giá Binance thật đã nạp.
     */
    function getEthPrice() public view returns (uint256) {
        if (useChainlinkLive && address(chainlinkEthFeed) != address(0)) {
            try chainlinkEthFeed.latestRoundData() returns (
                uint80,
                int256 answer,
                uint256,
                uint256 updatedAt,
                uint80
            ) {
                if (answer > 0 && updatedAt > 0) {
                    return uint256(answer);
                }
            } catch {
                // Tự động chuyển về giá Binance nếu Chainlink testnet bị nghẽn
            }
        }
        return assetPrices[ETH_ADDRESS];
    }

    function getAssetPrice(address asset) external view returns (uint256) {
        if (asset == ETH_ADDRESS) {
            return getEthPrice();
        }
        uint256 price = assetPrices[asset];
        require(price > 0, "Oracle: asset price not set");
        return price;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Oracle: new owner is zero address");
        owner = newOwner;
    }
}
