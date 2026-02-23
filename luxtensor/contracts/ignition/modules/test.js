/**
 * Minimal test Ignition module — deploy SimpleStorage only.
 * npx hardhat ignition deploy ./ignition/modules/test.js --network polkadot_testnet
 */
const { buildModule } = require("@nomicfoundation/hardhat-ignition/modules");

module.exports = buildModule("TestDeploy", (m) => {
    const storage = m.contract("SimpleStorage");
    return { storage };
});
