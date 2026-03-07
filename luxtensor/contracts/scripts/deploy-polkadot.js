/**
 * Deploy ModernTensor Full AI Stack to Polkadot Hub
 *
 * Deploys the complete ModernTensor AI protocol onto Polkadot Hub
 * via pallet-revive EVM compatibility layer.
 *
 * Usage:
 *   npx hardhat run scripts/deploy-polkadot.js --network polkadotTestnet
 *   npx hardhat run scripts/deploy-polkadot.js --network westend
 *   npx hardhat run scripts/deploy-polkadot.js --network hardhat
 *
 * Deploys:
 *   1. MDTToken       - ERC20 token (21M supply, category-based minting)
 *   2. MDTVesting     - Token vesting with cliff + linear release
 *   3. MDTStaking     - Time-lock staking with bonus rates
 *   4. ZkMLVerifier   - On-chain zkML proof verification
 *   5. AIOracle       - AI request/fulfill oracle with zkML
 *   6. SubnetRegistry  - Metagraph, consensus, weights, emission
 *   7. GradientAggregator - Federated learning training jobs
 *   8. TrainingEscrow - Reward distribution + slashing
 *
 * After deployment:
 *   - All contracts are linked together
 *   - Demo AI model is approved on AIOracle
 *   - ZkML verifier is set to dev mode for testing
 *   - Addresses saved to deployments-polkadot.json
 */

const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

// ============================================
// Helpers
// ============================================

function banner(text) {
    console.log("");
    console.log("=".repeat(70));
    console.log(`🔗 ${text}`);
    console.log("=".repeat(70));
}

function step(num, text) {
    console.log(`\n  [${num}] ${text}`);
}

function success(text) {
    console.log(`      ✅ ${text}`);
}

function info(text) {
    console.log(`      ℹ️  ${text}`);
}

// ============================================
// Main Deployment
// ============================================

async function main() {
    const [deployer] = await hre.ethers.getSigners();

    banner("ModernTensor → Polkadot Hub Deployment");
    console.log(`  Network:  ${hre.network.name}`);
    console.log(`  Deployer: ${deployer.address}`);

    const balance = await deployer.provider.getBalance(deployer.address);
    console.log(`  Balance:  ${hre.ethers.formatEther(balance)} native tokens`);

    if (balance === 0n) {
        console.error("\n  ❌ ERROR: Deployer has zero balance!");
        console.error("  Get testnet tokens from: https://faucet.polkadot.io/");
        process.exit(1);
    }

    const deployed = {};
    const startTime = Date.now();

    // ─────────────────────────────────────────
    // Phase 1: Core Token Infrastructure
    // ─────────────────────────────────────────
    banner("Phase 1: Core Token Infrastructure");

    step(1, "Deploying MDTToken (ERC20, 21M supply)...");
    const MDTToken = await hre.ethers.getContractFactory("MDTToken");
    const token = await MDTToken.deploy();
    await token.waitForDeployment();
    deployed.MDTToken = await token.getAddress();
    success(`MDTToken: ${deployed.MDTToken}`);

    // Print allocations
    const alloc = await token.getAllocations();
    info(`Max Supply: 21,000,000 MDT`);
    info(`Emission Rewards: ${hre.ethers.formatEther(alloc[0])} MDT (45%)`);
    info(`DAO Treasury: ${hre.ethers.formatEther(alloc[5])} MDT (10%)`);

    step(2, "Deploying MDTVesting (cliff + linear release)...");
    const MDTVesting = await hre.ethers.getContractFactory("MDTVesting");
    const vesting = await MDTVesting.deploy(deployed.MDTToken);
    await vesting.waitForDeployment();
    deployed.MDTVesting = await vesting.getAddress();
    success(`MDTVesting: ${deployed.MDTVesting}`);

    step(3, "Deploying MDTStaking (time-lock bonuses)...");
    const MDTStaking = await hre.ethers.getContractFactory("MDTStaking");
    const staking = await MDTStaking.deploy(deployed.MDTToken);
    await staking.waitForDeployment();
    deployed.MDTStaking = await staking.getAddress();
    success(`MDTStaking: ${deployed.MDTStaking}`);
    info("Bonus rates: 30d→10%, 90d→25%, 180d→50%, 365d→100%");

    // ─────────────────────────────────────────
    // Phase 2: AI Verification & Oracle
    // ─────────────────────────────────────────
    banner("Phase 2: AI Verification & Oracle");

    step(4, "Deploying ZkMLVerifier (STARK/Groth16/Dev proofs)...");
    const ZkMLVerifier = await hre.ethers.getContractFactory("ZkMLVerifier");
    const zkml = await ZkMLVerifier.deploy();
    await zkml.waitForDeployment();
    deployed.ZkMLVerifier = await zkml.getAddress();
    success(`ZkMLVerifier: ${deployed.ZkMLVerifier}`);

    step(5, "Deploying AIOracle (request/fulfill AI tasks)...");
    const AIOracle = await hre.ethers.getContractFactory("AIOracle");
    const oracle = await AIOracle.deploy();
    await oracle.waitForDeployment();
    deployed.AIOracle = await oracle.getAddress();
    success(`AIOracle: ${deployed.AIOracle}`);

    // ─────────────────────────────────────────
    // Phase 3.5a: TGE — Mint tokens FIRST (needed for subnet creation)
    // ─────────────────────────────────────────
    banner("Phase 3.5a: Mint Test Tokens (TGE)");

    step("8a-1", "Minting Emission Rewards → deployer (for testing)...");
    try {
        const txTge = await token.executeTGE(0, deployer.address); // Category.EmissionRewards = 0
        await txTge.wait();
        const minted = await token.categoryMinted(0);
        success(`Minted: ${hre.ethers.formatEther(minted)} MDT (Emission Rewards)`);
    } catch (e) {
        info(`Skipped TGE (may already be executed): ${e.message.substring(0, 80)}`);
    }

    step("8a-2", "Minting DAO Treasury → deployer (for testing)...");
    try {
        const txDao = await token.executeTGE(5, deployer.address); // Category.DaoTreasury = 5
        await txDao.wait();
        const mintedDao = await token.categoryMinted(5);
        success(`Minted: ${hre.ethers.formatEther(mintedDao)} MDT (DAO Treasury)`);
    } catch (e) {
        info(`Skipped DAO TGE: ${e.message.substring(0, 80)}`);
    }

    // Check total supply
    const totalSupply = await token.totalSupply();
    info(`Total Supply: ${hre.ethers.formatEther(totalSupply)} MDT`);

    // ─────────────────────────────────────────
    // Phase 3.5b: Subnet Registry (Metagraph + Consensus)
    // ─────────────────────────────────────────
    banner("Phase 3.5b: Subnet Registry (Metagraph + Consensus)");

    step("8b", "Deploying SubnetRegistry (key reg, weights, emission)...");
    const SubnetRegistry = await hre.ethers.getContractFactory("SubnetRegistry");
    const subnetCost = hre.ethers.parseEther("100");       // 100 MDT to register subnet
    const emissionPerBlock = hre.ethers.parseUnits("1", 15); // 0.001 MDT per block
    const registry = await SubnetRegistry.deploy(deployed.MDTToken, subnetCost, emissionPerBlock);
    await registry.waitForDeployment();
    deployed.SubnetRegistry = await registry.getAddress();
    success(`SubnetRegistry: ${deployed.SubnetRegistry}`);
    info("Subnet cost: 100 MDT, Emission: 0.001 MDT/block");

    step("8c", "Creating demo AI subnet...");
    try {
        // Approve tokens for subnet creation
        const txApproveSubnet = await token.approve(deployed.SubnetRegistry, subnetCost);
        await txApproveSubnet.wait();
        const txCreateSubnet = await registry.createSubnet(
            "ModernTensor AI Subnet",  // name
            256,                        // maxNodes
            hre.ethers.parseEther("10"), // minStake (10 MDT)
            360                         // tempo (360 blocks per epoch)
        );
        await txCreateSubnet.wait();
        success("Created subnet netuid=1: ModernTensor AI Subnet");
        info("maxNodes=256, minStake=10 MDT, tempo=360 blocks");
    } catch (e) {
        info(`Skipped demo subnet: ${e.message.substring(0, 80)}`);
    }

    step("8d", "Funding emission pool (1M MDT)...");
    try {
        const emissionFund = hre.ethers.parseEther("1000000");
        const txApproveFund = await token.approve(deployed.SubnetRegistry, emissionFund);
        await txApproveFund.wait();
        const txFund = await registry.fundEmissionPool(emissionFund);
        await txFund.wait();
        success("Funded emission pool with 1,000,000 MDT");
    } catch (e) {
        info(`Skipped emission funding: ${e.message.substring(0, 80)}`);
    }

    // ─────────────────────────────────────────
    // Phase 3.5c: Federated Learning & Escrow
    // ─────────────────────────────────────────
    banner("Phase 3.5c: Federated Learning Infrastructure");

    step("8e", "Deploying GradientAggregator (FedAvg on-chain)...");
    const GradientAggregator = await hre.ethers.getContractFactory("GradientAggregator");
    const gradAgg = await GradientAggregator.deploy(deployed.MDTToken);
    await gradAgg.waitForDeployment();
    deployed.GradientAggregator = await gradAgg.getAddress();
    success(`GradientAggregator: ${deployed.GradientAggregator}`);

    step("8f", "Deploying TrainingEscrow (stake + slash + rewards)...");
    const TrainingEscrow = await hre.ethers.getContractFactory("TrainingEscrow");
    const escrow = await TrainingEscrow.deploy(deployed.MDTToken, 5000); // 50% slash rate
    await escrow.waitForDeployment();
    deployed.TrainingEscrow = await escrow.getAddress();
    success(`TrainingEscrow: ${deployed.TrainingEscrow}`);
    info("Slash rate: 50% (5000 bps)");

    // ─────────────────────────────────────────
    // Phase 4: Configuration & Linking
    // ─────────────────────────────────────────
    banner("Phase 4: Contract Configuration");

    step(9, "Linking ZkMLVerifier → AIOracle...");
    const txZkml = await oracle.setZkMLVerifier(deployed.ZkMLVerifier);
    await txZkml.wait();
    success("ZkMLVerifier linked to AIOracle");

    step(10, "Enabling ZkMLVerifier dev mode (testnet)...");
    const txDev = await zkml.setDevMode(true);
    await txDev.wait();
    success("Dev mode enabled for testing");

    step(12, "Approving demo AI models...");
    const models = [
        { name: "moderntensor-code-review-v1", hash: null },
        { name: "moderntensor-ai-scoring-v1", hash: null },
        { name: "demo-federated-learning-v1", hash: null },
    ];
    for (const model of models) {
        model.hash = hre.ethers.keccak256(hre.ethers.toUtf8Bytes(model.name));
        const txModel = await oracle.approveModel(model.hash);
        await txModel.wait();
        success(`Model approved: ${model.name}`);
        info(`Hash: ${model.hash}`);
    }


    // ─────────────────────────────────────────
    // Save Deployment Info
    // ─────────────────────────────────────────
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

    const deploymentInfo = {
        project: "ModernTensor",
        description: "Decentralized AI Quality Protocol on Polkadot Hub",
        network: hre.network.name,
        chainId: hre.network.config.chainId,
        rpcUrl: hre.network.config.url,
        deployer: deployer.address,
        timestamp: new Date().toISOString(),
        deploymentTime: `${elapsed}s`,
        contracts: deployed,
        models: models.reduce((acc, m) => { acc[m.name] = m.hash; return acc; }, {}),
        hackathon: {
            name: "Polkadot Solidity Hackathon 2026",
            track: "Track 1: EVM Smart Contract — AI-powered dApps",
            organizer: "OpenGuild",
            platform: "DoraHacks",
            submission_deadline: "2026-03-20",
        }
    };

    const outputPath = path.join(__dirname, "..", "deployments-polkadot.json");
    fs.writeFileSync(outputPath, JSON.stringify(deploymentInfo, null, 2));

    // ─────────────────────────────────────────
    // Summary
    // ─────────────────────────────────────────
    banner("DEPLOYMENT COMPLETE 🎉");

    console.log("\n  📋 Deployed Contracts:");
    console.log("  ─────────────────────────────────────────────");
    for (const [name, addr] of Object.entries(deployed)) {
        console.log(`  ${name.padEnd(25)} ${addr}`);
    }

    console.log(`\n  ⏱️  Completed in ${elapsed}s`);
    console.log(`  📁 Saved to: deployments-polkadot.json`);

    console.log("\n  🔗 Verify on Polkadot Explorer:");
    if (hre.network.name.includes("westend") || hre.network.name === "polkadotTestnet") {
        console.log(`  https://westend-asset-hub.subscan.io/`);
    } else if (hre.network.name === "polkadot_mainnet") {
        console.log(`  https://assethub-polkadot.subscan.io/`);
    }

    console.log("\n  📝 Next Steps:");
    console.log("  1. Verify contracts on block explorer");
    console.log("  2. Test AI Oracle flow (requestAI → fulfillRequest)");
    console.log("  3. Test staking flow (lock → unlock with bonus)");
    console.log("  4. Create training job via GradientAggregator + TrainingEscrow");
    console.log("  5. Connect dashboard frontend to deployed addresses");
    console.log("  6. Record demo video for hackathon submission");
    console.log("");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("\n  ❌ Deployment failed:", error.message);
        console.error(error);
        process.exit(1);
    });
