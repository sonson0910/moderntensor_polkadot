/**
 * Verify all 8 deployed contracts are live and responding on-chain.
 * Usage: npx hardhat run scripts/verify-onchain.js --network localhost
 */
const fs = require("fs");
const hre = require("hardhat");

async function main() {
    const deploy = JSON.parse(fs.readFileSync("deployments-polkadot.json"));
    console.log("\n🔍 Verifying 8 deployed contracts on-chain...\n");

    // 1. MDTToken
    const token = await hre.ethers.getContractAt("MDTToken", deploy.contracts.MDTToken);
    const supply = await token.totalSupply();
    console.log(`  ✅ MDTToken          ${deploy.contracts.MDTToken}`);
    console.log(`     totalSupply: ${hre.ethers.formatEther(supply)} MDT`);

    // 2. MDTVesting
    const vesting = await hre.ethers.getContractAt("MDTVesting", deploy.contracts.MDTVesting);
    const vestToken = await vesting.token();
    console.log(`  ✅ MDTVesting        ${deploy.contracts.MDTVesting}`);
    console.log(`     linked token: ${vestToken}`);

    // 3. MDTStaking
    const staking = await hre.ethers.getContractAt("MDTStaking", deploy.contracts.MDTStaking);
    const stakingToken = await staking.token();
    console.log(`  ✅ MDTStaking        ${deploy.contracts.MDTStaking}`);
    console.log(`     linked token: ${stakingToken}`);

    // 4. ZkMLVerifier
    const zkml = await hre.ethers.getContractAt("ZkMLVerifier", deploy.contracts.ZkMLVerifier);
    const devMode = await zkml.devModeEnabled();
    console.log(`  ✅ ZkMLVerifier      ${deploy.contracts.ZkMLVerifier}`);
    console.log(`     devMode: ${devMode}`);

    // 5. AIOracle
    const oracle = await hre.ethers.getContractAt("AIOracle", deploy.contracts.AIOracle);
    const totalReqs = await oracle.requestCount();
    const feeBps = await oracle.protocolFeeBps();
    console.log(`  ✅ AIOracle          ${deploy.contracts.AIOracle}`);
    console.log(`     totalRequests: ${totalReqs}, protocolFee: ${feeBps} bps`);

    // 6. SubnetRegistry
    const registry = await hre.ethers.getContractAt("SubnetRegistry", deploy.contracts.SubnetRegistry);
    const subnetCount = await registry.getSubnetCount();
    console.log(`  ✅ SubnetRegistry    ${deploy.contracts.SubnetRegistry}`);
    console.log(`     subnets: ${subnetCount}`);

    // 7. GradientAggregator
    const gradAgg = await hre.ethers.getContractAt("GradientAggregator", deploy.contracts.GradientAggregator);
    const jobCount = await gradAgg.nextJobId();
    const aggToken = await gradAgg.token();
    console.log(`  ✅ GradientAggregator ${deploy.contracts.GradientAggregator}`);
    console.log(`     jobCount: ${jobCount}, rewardToken: ${aggToken}`);

    // 8. TrainingEscrow
    const escrow = await hre.ethers.getContractAt("TrainingEscrow", deploy.contracts.TrainingEscrow);
    const taskCount = await escrow.nextTaskId();
    const slashRate = await escrow.slashRate();
    console.log(`  ✅ TrainingEscrow    ${deploy.contracts.TrainingEscrow}`);
    console.log(`     taskCount: ${taskCount}, slashRate: ${slashRate} bps (${Number(slashRate)/100}%)`);

    // Summary
    console.log(`\n${"═".repeat(60)}`);
    console.log(`  ✅ ALL 8 CONTRACTS VERIFIED ON-CHAIN`);
    console.log(`  Network: ${hre.network.name}`);
    console.log(`  Deployer: ${deploy.deployer}`);
    console.log(`  Timestamp: ${deploy.timestamp}`);
    console.log(`${"═".repeat(60)}\n`);
}

main()
    .then(() => process.exit(0))
    .catch((err) => {
        console.error("❌ Verification failed:", err.message);
        process.exit(1);
    });
