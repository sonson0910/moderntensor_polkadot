/**
 * Deploy SubnetRegistry only (the last contract that failed).
 *
 * Usage: npx hardhat run scripts/deploy-subnet-registry.js --network polkadotTestnet
 */
const hre = require("hardhat");
const fs = require("fs");

async function main() {
    const [deployer] = await hre.ethers.getSigners();

    // Previously deployed addresses
    const MDT_TOKEN = "0x78225b092c91C7DCC4Cc977e328182c34b52cFB5";

    console.log("Deployer:", deployer.address);
    console.log("MDTToken:", MDT_TOKEN);

    // SubnetRegistry constructor: (address _token, uint256 _subnetRegistrationCost, uint256 _emissionPerBlock)
    const registrationCost = hre.ethers.parseEther("100");  // 100 MDT
    const emissionPerBlock = hre.ethers.parseEther("1");    // 1 MDT per block

    console.log("\n📦 Deploying SubnetRegistry...");
    const factory = await hre.ethers.getContractFactory("SubnetRegistry");
    const contract = await factory.deploy(MDT_TOKEN, registrationCost, emissionPerBlock);
    await contract.waitForDeployment();

    const addr = await contract.getAddress();
    const tx = contract.deploymentTransaction();
    const receipt = await tx.wait();

    console.log("✅ SubnetRegistry:", addr);
    console.log("⛽ Gas:", receipt.gasUsed.toString());
    console.log("🔗 TX:", tx.hash);

    // Update deployments file
    const deployments = JSON.parse(fs.readFileSync("deployments-polkadot.json", "utf-8"));
    deployments.contracts.SubnetRegistry = addr;
    fs.writeFileSync("deployments-polkadot.json", JSON.stringify(deployments, null, 2));
    console.log("\n📁 Updated deployments-polkadot.json");

    // Print all contracts
    console.log("\n🎉 ALL CONTRACTS:");
    for (const [name, address] of Object.entries(deployments.contracts)) {
        console.log(`  ${name}: ${address}`);
    }
}

main()
    .then(() => process.exit(0))
    .catch((err) => {
        console.error("❌ Failed:", err.message?.substring(0, 500) || err);
        process.exit(1);
    });
