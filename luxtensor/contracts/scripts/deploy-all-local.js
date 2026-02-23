/**
 * Deploy ALL ModernTensor contracts to local Hardhat node
 *
 * Deploys: MDTToken, MDTVesting, MDTStaking, ZkMLVerifier, AIOracle, SubnetRegistry
 * Then: TGE, approvals, fulfiller registration
 *
 * Usage: npx hardhat run scripts/deploy-all-local.js --network localhost
 */

const hre = require("hardhat");
const fs = require("fs");

async function main() {
    const [deployer, miner] = await hre.ethers.getSigners();

    console.log("=".repeat(60));
    console.log("🚀 ModernTensor — Full Local Deploy");
    console.log("=".repeat(60));
    console.log("Deployer:", deployer.address);
    console.log("Miner:   ", miner.address);
    console.log("");

    // 1. MDTToken
    console.log("📝 Deploying MDTToken...");
    const MDTToken = await hre.ethers.getContractFactory("MDTToken");
    const token = await MDTToken.deploy();
    await token.waitForDeployment();
    const tokenAddr = await token.getAddress();
    console.log("✅ MDTToken:", tokenAddr);

    // 2. MDTVesting
    console.log("📝 Deploying MDTVesting...");
    const MDTVesting = await hre.ethers.getContractFactory("MDTVesting");
    const vesting = await MDTVesting.deploy(tokenAddr);
    await vesting.waitForDeployment();
    const vestingAddr = await vesting.getAddress();
    console.log("✅ MDTVesting:", vestingAddr);

    // 3. MDTStaking
    console.log("📝 Deploying MDTStaking...");
    const MDTStaking = await hre.ethers.getContractFactory("MDTStaking");
    const staking = await MDTStaking.deploy(tokenAddr);
    await staking.waitForDeployment();
    const stakingAddr = await staking.getAddress();
    console.log("✅ MDTStaking:", stakingAddr);

    // 4. ZkMLVerifier
    console.log("📝 Deploying ZkMLVerifier...");
    const ZkMLVerifier = await hre.ethers.getContractFactory("ZkMLVerifier");
    const zkml = await ZkMLVerifier.deploy();
    await zkml.waitForDeployment();
    const zkmlAddr = await zkml.getAddress();
    console.log("✅ ZkMLVerifier:", zkmlAddr);

    // 5. AIOracle
    console.log("📝 Deploying AIOracle...");
    const AIOracle = await hre.ethers.getContractFactory("AIOracle");
    const oracle = await AIOracle.deploy();
    await oracle.waitForDeployment();
    const oracleAddr = await oracle.getAddress();
    console.log("✅ AIOracle:", oracleAddr);

    // 6. SubnetRegistry (token, registrationCost=0, emissionPerBlock=1e18)
    console.log("📝 Deploying SubnetRegistry...");
    const SubnetRegistry = await hre.ethers.getContractFactory("SubnetRegistry");
    const subnet = await SubnetRegistry.deploy(
        tokenAddr,
        0,  // registrationCost = 0 for testing
        hre.ethers.parseEther("1")  // emissionPerBlock = 1 MDT
    );
    await subnet.waitForDeployment();
    const subnetAddr = await subnet.getAddress();
    console.log("✅ SubnetRegistry:", subnetAddr);

    // ── Post-deploy setup ──
    console.log("\n🔧 Post-deploy setup...");

    // TGE: Mint initial tokens to deployer
    // Category 0=EmissionRewards, 1=EcosystemGrants, etc.
    console.log("  Minting tokens (EcosystemGrants → deployer)...");
    const mintAmount = hre.ethers.parseEther("100000"); // 100k MDT
    await token.mintCategory(1, deployer.address, mintAmount); // Category 1 = EcosystemGrants
    const balance = await token.balanceOf(deployer.address);
    console.log("  Deployer MDT:", hre.ethers.formatEther(balance));

    // Enable dev mode on ZkMLVerifier
    console.log("  Enabling ZkML dev mode...");
    await zkml.setDevMode(true);

    // Set ZkML verifier on AIOracle
    console.log("  Setting ZkML verifier on AIOracle...");
    await oracle.setZkMLVerifier(zkmlAddr);

    // Register miner as fulfiller (F-08 fix validation)
    console.log("  Registering miner as fulfiller...");
    await oracle.registerFulfiller(miner.address);

    // Also register deployer as fulfiller
    await oracle.registerFulfiller(deployer.address);

    // Approve a test model
    const testModelHash = hre.ethers.keccak256(hre.ethers.toUtf8Bytes("test-nlp-v1"));
    console.log("  Approving test model...");
    await oracle.approveModel(testModelHash);

    // Transfer some tokens to staking contract for bonuses
    console.log("  Funding staking bonus pool...");
    const bonusAmount = hre.ethers.parseEther("1000");
    await token.transfer(stakingAddr, bonusAmount);

    // Approve staking contract
    console.log("  Approving staking...");
    await token.approve(stakingAddr, hre.ethers.parseEther("100000"));

    // Approve subnet registry
    console.log("  Approving subnet registry...");
    await token.approve(subnetAddr, hre.ethers.parseEther("100000"));

    // ── Save deployment ──
    const deployment = {
        network: "localhost",
        deployer: deployer.address,
        miner: miner.address,
        timestamp: new Date().toISOString(),
        MDTToken: tokenAddr,
        MDTVesting: vestingAddr,
        MDTStaking: stakingAddr,
        ZkMLVerifier: zkmlAddr,
        AIOracle: oracleAddr,
        SubnetRegistry: subnetAddr,
    };

    fs.writeFileSync("deployments-local.json", JSON.stringify(deployment, null, 2));
    console.log("\n✅ Saved to deployments-local.json");

    console.log("\n" + "=".repeat(60));
    console.log("📋 All Contracts Deployed");
    console.log("=".repeat(60));
    for (const [name, addr] of Object.entries(deployment)) {
        if (name !== "network" && name !== "timestamp") {
            console.log(`  ${name.padEnd(20)} → ${addr}`);
        }
    }
    console.log("\n🎉 Ready for testing! Run: python tests/test_local_flow.py");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
