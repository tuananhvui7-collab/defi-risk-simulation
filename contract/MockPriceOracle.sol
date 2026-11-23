// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MockPriceOracle
 * @notice Price Oracle for DeFi Lending Protocol simulating Chainlink Price Feeds.
 * Asset prices are returned in 8 decimals (e.g. 2,000 USD = 2000 * 10^8).
 */
contract MockPriceOracle {
    address public owner;
    
    // Address of asset => price with 8 decimals
    mapping(address => uint256) public assetPrices;
    
    // Default constant key for Native ETH
    address public constant ETH_ADDRESS = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;

    event AssetPriceUpdated(address indexed asset, uint256 oldPrice, uint256 newPrice, uint256 timestamp);

    modifier onlyOwner() {
        require(msg.sender == owner, "Oracle: caller is not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        // Default initial ETH price: $2,000.00 (8 decimals)
        assetPrices[ETH_ADDRESS] = 2000 * 10**8;
    }

    function setAssetPrice(address asset, uint256 price) external onlyOwner {
        require(price > 0, "Oracle: price must be positive");
        uint256 oldPrice = assetPrices[asset];
        assetPrices[asset] = price;
        emit AssetPriceUpdated(asset, oldPrice, price, block.timestamp);
    }

    function setEthPrice(uint256 price) external onlyOwner {
        require(price > 0, "Oracle: price must be positive");
        uint256 oldPrice = assetPrices[ETH_ADDRESS];
        assetPrices[ETH_ADDRESS] = price;
        emit AssetPriceUpdated(ETH_ADDRESS, oldPrice, price, block.timestamp);
    }

    function getAssetPrice(address asset) external view returns (uint256) {
        uint256 price = assetPrices[asset];
        require(price > 0, "Oracle: asset price not set");
        return price;
    }

    function getEthPrice() external view returns (uint256) {
        return assetPrices[ETH_ADDRESS];
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Oracle: new owner is zero address");
        owner = newOwner;
    }
}
