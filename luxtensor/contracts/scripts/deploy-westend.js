/**
 * Deploy all 6 ModernTensor contracts to Polkadot Hub TestNet.
 *
 * Usage: npx hardhat run scripts/deploy-westend.js --network polkadotTestnet
 */
const hre = require("hardhat");
const fs = require("fs");

async function main() {
    const [deployer] = await hre.ethers.getSigners();
    const balance = await hre.ethers.provider.getBalance(deployer.address);

    console.log("=".repeat(60));
    console.log("ModernTensor — Polkadot Hub TestNet Deployment");
    console.log("=".repeat(60));
    console.log("Deployer:", deployer.address);
    const tokenName = hre.network.name === 'westend' ? 'WND' : 'PAS';
    console.log("Balance:", hre.ethers.formatEther(balance), tokenName);
    console.log("Network:", hre.network.name);
    console.log("=".repeat(60));

    const deployed = {};
    let totalGas = 0n;

    // Helper to deploy and track gas
    async function deploy(name, ...args) {
        console.log(`\n📦 Deploying ${name}...`);
        const factory = await hre.ethers.getContractFactory(name);
        const contract = await factory.deploy(...args);
        await contract.waitForDeployment();
        const addr = await contract.getAddress();
        const tx = contract.deploymentTransaction();
        const receipt = await tx.wait();
        const gas = receipt.gasUsed;
        totalGas += gas;
        deployed[name] = addr;
        console.log(`  ✅ ${name}: ${addr}`);
        console.log(`  ⛽ Gas: ${gas.toString()}`);
        console.log(`  🔗 TX: ${tx.hash}`);
        return contract;
    }

    // ============================================
    // Phase 1: Core Token
    // ============================================
    console.log("\n--- Phase 1: Core Token ---");
    const token = await deploy("MDTToken");

    // ============================================
    // Phase 2: Token Infrastructure
    // ============================================
    console.log("\n--- Phase 2: Token Infrastructure ---");
    const vesting = await deploy("MDTVesting", deployed["MDTToken"]);
    const staking = await deploy("MDTStaking", deployed["MDTToken"]);

    // ============================================
    // Phase 3: AI Infrastructure
    // ============================================
    console.log("\n--- Phase 3: AI Infrastructure ---");
    const verifier = await deploy("ZkMLVerifier");
    const oracle = await deploy("AIOracle");

    // ============================================
    // Phase 4: Subnet Registry
    // ============================================
    console.log("\n--- Phase 4: Subnet Registry ---");
    const registry = await deploy("SubnetRegistry", deployed["MDTToken"], deployed["MDTStaking"]);

    // ============================================
    // Summary
    // ============================================
    const endBalance = await hre.ethers.provider.getBalance(deployer.address);

    console.log("\n" + "=".repeat(60));
    console.log("🎉 ALL CONTRACTS DEPLOYED SUCCESSFULLY!");
    console.log("=".repeat(60));
    console.log("\nDeployed Contracts:");
    for (const [name, addr] of Object.entries(deployed)) {
        console.log(`  ${name}: ${addr}`);
    }
    console.log("\n⛽ Total Gas Used:", totalGas.toString());
    console.log("💰 " + tokenName + " Spent:", hre.ethers.formatEther(balance - endBalance));
    console.log("💰 Remaining:", hre.ethers.formatEther(endBalance), tokenName);

    // Save deployment info
    const info = {
        network: hre.network.name,
        chainId: (await hre.ethers.provider.getNetwork()).chainId.toString(),
        deployer: deployer.address,
        timestamp: new Date().toISOString(),
        contracts: deployed,
        totalGas: totalGas.toString(),
    };
    fs.writeFileSync("deployments-polkadot.json", JSON.stringify(info, null, 2));
    console.log("\n📁 Saved to deployments-polkadot.json");
}

main()
    .then(() => process.exit(0))
    .catch((err) => {
        console.error("\n❌ Failed:", err.message?.substring(0, 800) || err);
        process.exit(1);
    });
