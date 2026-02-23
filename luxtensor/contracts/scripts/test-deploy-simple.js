/**
 * Test deploy SimpleStorage via Hardhat task runner.
 *
 * Usage: npx hardhat run scripts/test-deploy-simple.js --network polkadotTestnet
 */
const hre = require("hardhat");

async function main() {
    const [deployer] = await hre.ethers.getSigners();
    const balance = await hre.ethers.provider.getBalance(deployer.address);

    console.log("Deployer:", deployer.address);
    console.log("Balance:", hre.ethers.formatEther(balance), "PAS");
    console.log("Network:", hre.network.name);

    console.log("\nDeploying SimpleStorage...");
    const factory = await hre.ethers.getContractFactory("SimpleStorage");
    const contract = await factory.deploy();
    await contract.waitForDeployment();

    const addr = await contract.getAddress();
    const tx = contract.deploymentTransaction();
    console.log("✅ SimpleStorage deployed at:", addr);
    console.log("TX Hash:", tx.hash);

    // Verify it works
    const value = await contract.value();
    console.log("Stored value:", value.toString());
}

main()
    .then(() => process.exit(0))
    .catch((err) => {
        console.error("❌ Failed:", err.message?.substring(0, 500) || err);
        process.exit(1);
    });
