/**
 * Deploy all 6 ModernTensor contracts to Polkadot Hub TestNet.
 * Uses raw ethers.js to bypass Hardhat signer issues with pallet-revive.
 *
 * Usage: node scripts/deploy-polkadot-raw.js
 */
const { ethers } = require("ethers");
const fs = require("fs");
const path = require("path");
require("dotenv").config();

const RPC_URL = "https://services.polkadothub-rpc.com/testnet";
const PRIVATE_KEY = process.env.PRIVATE_KEY?.startsWith("0x")
    ? process.env.PRIVATE_KEY
    : `0x${process.env.PRIVATE_KEY}`;

async function main() {
    const provider = new ethers.JsonRpcProvider(RPC_URL);
    const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
    const balance = await provider.getBalance(wallet.address);
    const network = await provider.getNetwork();
    const feeData = await provider.getFeeData();
    const gasPrice = feeData.gasPrice || 1000000000000n;

    console.log("=".repeat(60));
    console.log("ModernTensor — Polkadot Hub TestNet Deployment");
    console.log("=".repeat(60));
    console.log("Deployer:", wallet.address);
    console.log("Balance:", ethers.formatEther(balance), "PAS");
    console.log("ChainId:", network.chainId.toString());
    console.log("Gas Price:", gasPrice.toString());
    console.log("=".repeat(60));

    const deployed = {};
    let totalGas = 0n;

    function loadArtifact(contractName) {
        const artifactsDir = path.join(__dirname, "..", "artifacts", "src");
        // Recursively search for the artifact
        function searchDir(dir) {
            for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
                const fullPath = path.join(dir, entry.name);
                if (entry.isDirectory()) {
                    const result = searchDir(fullPath);
                    if (result) return result;
                } else if (entry.name === `${contractName}.json`) {
                    return JSON.parse(fs.readFileSync(fullPath, "utf8"));
                }
            }
            return null;
        }
        const artifact = searchDir(artifactsDir);
        if (!artifact) throw new Error(`Artifact not found: ${contractName}`);
        return artifact;
    }

    async function deploy(name, constructorArgs = []) {
        console.log(`\n📦 Deploying ${name}...`);
        const artifact = loadArtifact(name);
        const factory = new ethers.ContractFactory(artifact.abi, artifact.bytecode, wallet);

        const contract = await factory.deploy(...constructorArgs, {
            gasPrice,
            gasLimit: 30000000n,
        });

        const tx = contract.deploymentTransaction();
        console.log(`  🔄 TX: ${tx.hash}`);
        console.log(`  ⏳ Waiting for confirmation...`);

        await contract.waitForDeployment();
        const addr = await contract.getAddress();
        const receipt = await tx.wait();
        const gas = receipt.gasUsed;
        totalGas += gas;
        deployed[name] = addr;

        console.log(`  ✅ ${name}: ${addr}`);
        console.log(`  ⛽ Gas: ${gas.toString()} (${ethers.formatEther(gas * gasPrice)} PAS)`);
        return contract;
    }

    // ============================================
    // Phase 1: Core Token
    // ============================================
    console.log("\n--- Phase 1: Core Token ---");
    await deploy("MDTToken");

    // ============================================
    // Phase 2: Token Infrastructure
    // ============================================
    console.log("\n--- Phase 2: Token Infrastructure ---");
    await deploy("MDTVesting", [deployed["MDTToken"]]);
    await deploy("MDTStaking", [deployed["MDTToken"]]);

    // ============================================
    // Phase 3: AI Infrastructure
    // ============================================
    console.log("\n--- Phase 3: AI Infrastructure ---");
    await deploy("ZkMLVerifier");
    await deploy("AIOracle");

    // ============================================
    // Phase 4: Subnet Registry
    // ============================================
    console.log("\n--- Phase 4: Subnet Registry ---");
    await deploy("SubnetRegistry", [deployed["MDTToken"], deployed["MDTStaking"]]);

    // ============================================
    // Summary
    // ============================================
    const endBalance = await provider.getBalance(wallet.address);

    console.log("\n" + "=".repeat(60));
    console.log("🎉 ALL CONTRACTS DEPLOYED SUCCESSFULLY!");
    console.log("=".repeat(60));
    console.log("\nDeployed Contracts:");
    for (const [name, addr] of Object.entries(deployed)) {
        console.log(`  ${name}: ${addr}`);
    }
    console.log("\n⛽ Total Gas Used:", totalGas.toString());
    console.log("💰 PAS Spent:", ethers.formatEther(balance - endBalance));
    console.log("💰 Remaining:", ethers.formatEther(endBalance), "PAS");

    // Save deployment info
    const info = {
        network: "polkadot_hub_testnet",
        chainId: network.chainId.toString(),
        rpc: RPC_URL,
        deployer: wallet.address,
        timestamp: new Date().toISOString(),
        contracts: deployed,
        totalGas: totalGas.toString(),
    };
    const outPath = path.join(__dirname, "..", "deployments-polkadot.json");
    fs.writeFileSync(outPath, JSON.stringify(info, null, 2));
    console.log("\n📁 Saved to deployments-polkadot.json");
}

main()
    .then(() => process.exit(0))
    .catch((err) => {
        console.error("\n❌ Failed:", err.message?.substring(0, 800) || err);
        process.exit(1);
    });
