/**
 * contract/deploy.js — Deployment Script cho Sepolia Testnet hoặc Local Node
 * 
 * Sử dụng:
 * 1. Cài đặt ethers nếu chưa có: npm install ethers dotenv
 * 2. Cấu hình file .env:
 *    SEPOLIA_RPC_URL="https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY"
 *    PRIVATE_KEY="0xYOUR_PRIVATE_KEY"
 * 3. Chạy script: node contract/deploy.js
 */

const fs = require('fs');
const path = require('path');
const { ethers } = require('ethers');
require('dotenv').config();

async function main() {
    console.log("==================================================================");
    console.log("🚀 BẮT ĐẦU DEPLOY GIAO THỨC DEFI LENDING LÊN SEPOLIA TESTNET");
    console.log("==================================================================");

    const rpcUrl = process.env.SEPOLIA_RPC_URL || "https://rpc.sepolia.org";
    const privateKey = process.env.PRIVATE_KEY;

    if (!privateKey) {
        console.error("❌ Lỗi: Chưa cung cấp PRIVATE_KEY trong file .env!");
        console.log("Vui lòng tạo file .env với nội dung:");
        console.log("PRIVATE_KEY=your_private_key_here");
        console.log("SEPOLIA_RPC_URL=https://rpc.sepolia.org");
        process.exit(1);
    }

    const provider = new ethers.JsonRpcProvider(rpcUrl);
    const wallet = new ethers.Wallet(privateKey, provider);
    console.log(`📡 Deployer Address: ${wallet.address}`);

    const balance = await provider.getBalance(wallet.address);
    console.log(`💰 Số dư ví: ${ethers.formatEther(balance)} ETH`);

    if (balance === 0n) {
        console.error("❌ Ví không có Sepolia ETH để trả gas. Vui lòng nhận faucet tại https://sepoliafaucet.com");
        process.exit(1);
    }

    // Đọc ABI và Bytecode đã compile
    const buildDir = path.join(__dirname, 'build');
    function getArtifact(contractName) {
        const abiPath = path.join(buildDir, `contracts_DeFiLendingPoolFlat_sol_${contractName}.abi`);
        const binPath = path.join(buildDir, `contracts_DeFiLendingPoolFlat_sol_${contractName}.bin`);
        const abi = JSON.parse(fs.readFileSync(abiPath, 'utf8'));
        const bin = "0x" + fs.readFileSync(binPath, 'utf8').trim();
        return { abi, bin };
    }

    // 1. Deploy MockUSDC
    console.log("\n1️⃣  Đang deploy MockUSDC...");
    const usdcArtifact = getArtifact('MockUSDC');
    const usdcFactory = new ethers.ContractFactory(usdcArtifact.abi, usdcArtifact.bin, wallet);
    const usdcContract = await usdcFactory.deploy();
    await usdcContract.waitForDeployment();
    const usdcAddress = await usdcContract.getAddress();
    console.log(`   ✅ MockUSDC deployed at: ${usdcAddress}`);

    // 2. Deploy MockPriceOracle
    console.log("\n2️⃣  Đang deploy MockPriceOracle...");
    const oracleArtifact = getArtifact('MockPriceOracle');
    const oracleFactory = new ethers.ContractFactory(oracleArtifact.abi, oracleArtifact.bin, wallet);
    const oracleContract = await oracleFactory.deploy();
    await oracleContract.waitForDeployment();
    const oracleAddress = await oracleContract.getAddress();
    console.log(`   ✅ MockPriceOracle deployed at: ${oracleAddress}`);

    // 3. Deploy InterestRateModel (Two-slope Kink)
    console.log("\n3️⃣  Đang deploy InterestRateModel (Kink Model)...");
    const irArtifact = getArtifact('InterestRateModel');
    const irFactory = new ethers.ContractFactory(irArtifact.abi, irArtifact.bin, wallet);
    // Base 0%, Slope1 4%, Slope2 75%, U_opt 80%, ReserveFactor 10%
    const baseRate = 0n;
    const slope1 = ethers.parseUnits("0.04", 18);
    const slope2 = ethers.parseUnits("0.75", 18);
    const uOpt = ethers.parseUnits("0.80", 18);
    const reserveFactor = ethers.parseUnits("0.10", 18);

    const irContract = await irFactory.deploy(baseRate, slope1, slope2, uOpt, reserveFactor);
    await irContract.waitForDeployment();
    const irAddress = await irContract.getAddress();
    console.log(`   ✅ InterestRateModel deployed at: ${irAddress}`);

    // 4. Deploy DeFiLendingPool
    console.log("\n4️⃣  Đang deploy DeFiLendingPool...");
    const poolArtifact = getArtifact('DeFiLendingPool');
    const poolFactory = new ethers.ContractFactory(poolArtifact.abi, poolArtifact.bin, wallet);
    const poolContract = await poolFactory.deploy(usdcAddress, oracleAddress, irAddress);
    await poolContract.waitForDeployment();
    const poolAddress = await poolContract.getAddress();
    console.log(`   ✅ DeFiLendingPool deployed at: ${poolAddress}`);

    console.log("\n==================================================================");
    console.log("🎉 DEPLOY THÀNH CÔNG! THÔNG TIN HỢP ĐỒNG ĐỂ ĐƯA VÀO CHƯƠNG 5:");
    console.log("==================================================================");
    console.log(`Mạng: Ethereum Sepolia Testnet`);
    console.log(`MockUSDC:           ${usdcAddress}`);
    console.log(`MockPriceOracle:    ${oracleAddress}`);
    console.log(`InterestRateModel:  ${irAddress}`);
    console.log(`DeFiLendingPool:    ${poolAddress}`);
    console.log(`Sepolia Etherscan:  https://sepolia.etherscan.io/address/${poolAddress}`);
    console.log("==================================================================");
}

if (require.main === module) {
    main().catch(console.error);
}
