/**
 * Test deploy SimpleStorage to Westend AssetHub.
 * Minimal contract to verify deploy pipeline works.
 *
 * Usage: node scripts/test-deploy-token.js
 */
const { ethers } = require("ethers");
const fs = require("fs");
require("dotenv").config();

const RPC_URL = "https://westend-asset-hub-eth-rpc.polkadot.io";
const CHAIN_ID = 420420421;

async function main() {
    const provider = new ethers.JsonRpcProvider(RPC_URL, {
        chainId: CHAIN_ID,
        name: "westend-assethub",
    });
    const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);
    const balance = await provider.getBalance(wallet.address);

    console.log("Deployer:", wallet.address);
    console.log("Balance:", ethers.formatEther(balance), "WND");

    // Load SimpleStorage artifact
    const artifact = JSON.parse(
        fs.readFileSync("artifacts/src/SimpleStorage.sol/SimpleStorage.json", "utf-8")
    );
    console.log("Artifact format:", artifact._format);
    console.log("Bytecode length:", artifact.bytecode.length, "chars");

    const factory = new ethers.ContractFactory(
        artifact.abi,
        artifact.bytecode,
        wallet
    );

    console.log("\nDeploying SimpleStorage (EIP-1559)...");
    const contract = await factory.deploy({
        gasLimit: 5_000_000n,
    });

    const txHash = contract.deploymentTransaction().hash;
    console.log("TX Hash:", txHash);
    console.log("Waiting for confirmation...");

    const receipt = await contract.deploymentTransaction().wait(1);
    const addr = await contract.getAddress();

    console.log("\n✅ SimpleStorage deployed!");
    console.log("Address:", addr);
    console.log("Gas used:", receipt.gasUsed.toString());
    console.log("Block:", receipt.blockNumber);

    // Verify it works
    const deployed = new ethers.Contract(addr, artifact.abi, wallet);
    const val = await deployed.value();
    console.log("Value:", val.toString());
    console.log("\nSubscan:", "https://assethub-westend.subscan.io/tx/" + txHash);
}

main()
    .then(() => process.exit(0))
    .catch((err) => {
        console.error("\n❌ Failed:", err.code || "UNKNOWN");
        console.error("Message:", (err.message || "").substring(0, 500));
        if (err.error) console.error("RPC Error:", JSON.stringify(err.error).substring(0, 300));
        process.exit(1);
    });
