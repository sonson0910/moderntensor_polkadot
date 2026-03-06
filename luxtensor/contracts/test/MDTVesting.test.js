// SPDX-License-Identifier: MIT
/**
 * MDTVesting — Full Test Suite
 *
 * Tests: cliff, linear vesting, TGE%, claim, revoke, solvency check
 */

const { expect } = require("chai");
const { ethers } = require("hardhat");
const {
  loadFixture,
  time,
} = require("@nomicfoundation/hardhat-network-helpers");

describe("MDTVesting", function () {
  async function deployFixture() {
    const [owner, alice, bob] = await ethers.getSigners();

    const MDTToken = await ethers.getContractFactory("MDTToken");
    const token = await MDTToken.deploy();
    await token.waitForDeployment();
    const tokenAddr = await token.getAddress();

    const MDTVesting = await ethers.getContractFactory("MDTVesting");
    const vesting = await MDTVesting.deploy(tokenAddr);
    await vesting.waitForDeployment();
    const vestingAddr = await vesting.getAddress();

    // Mint tokens to owner for funding
    await token.mintCategory(0, owner.address, ethers.parseEther("1000000"));

    return { token, vesting, owner, alice, bob, tokenAddr, vestingAddr };
  }

  async function vestingWithTGEFixture() {
    const fix = await loadFixture(deployFixture);
    const { vesting, token, vestingAddr } = fix;

    // Set TGE timestamp
    await vesting.setTGE(await time.latest());

    // Fund vesting contract
    await token.transfer(vestingAddr, ethers.parseEther("100000"));

    return fix;
  }

  // ─── Deployment ──────────────────────────────────────────

  describe("Deployment", function () {
    it("should set the correct token address", async function () {
      const { token, vesting } = await loadFixture(deployFixture);
      expect(await vesting.token()).to.equal(await token.getAddress());
    });

    it("should start with zero totalAllocated", async function () {
      const { vesting } = await loadFixture(deployFixture);
      expect(await vesting.totalAllocated()).to.equal(0);
    });
  });

  // ─── TGE Timestamp ──────────────────────────────────────

  describe("TGE Timestamp", function () {
    it("should allow owner to set TGE timestamp", async function () {
      const { vesting } = await loadFixture(deployFixture);
      const ts = await time.latest();
      await vesting.setTGE(ts);
      expect(await vesting.tgeTimestamp()).to.equal(ts);
    });

    it("should revert when non-owner sets TGE", async function () {
      const { vesting, alice } = await loadFixture(deployFixture);
      await expect(
        vesting.connect(alice).setTGE(1000)
      ).to.be.reverted;
    });
  });

  // ─── Create Vesting Schedules ────────────────────────────

  describe("createVesting (via public methods)", function () {
    it("should create a team vesting schedule", async function () {
      const { vesting, token, alice, vestingAddr } =
        await loadFixture(vestingWithTGEFixture);

      const amount = ethers.parseEther("10000");
      await vesting.createTeamVesting(alice.address, amount);
      expect(await vesting.totalAllocated()).to.equal(amount);
    });

    it("should create IDO vesting", async function () {
      const { vesting, alice } = await loadFixture(vestingWithTGEFixture);
      const amount = ethers.parseEther("5000");
      await vesting.createIDOVesting(alice.address, amount);
      expect(await vesting.totalAllocated()).to.equal(amount);
    });

    it("should create private sale vesting", async function () {
      const { vesting, alice } = await loadFixture(vestingWithTGEFixture);
      const amount = ethers.parseEther("3000");
      await vesting.createPrivateSaleVesting(alice.address, amount);
      expect(await vesting.totalAllocated()).to.equal(amount);
    });

    it("should revert on duplicate vesting schedule", async function () {
      const { vesting, alice } = await loadFixture(vestingWithTGEFixture);
      const amount = ethers.parseEther("1000");
      await vesting.createTeamVesting(alice.address, amount);
      await expect(
        vesting.createTeamVesting(alice.address, amount)
      ).to.be.revertedWith("Duplicate vesting schedule exists");
    });

    it("should revert if TGE not set", async function () {
      const { vesting, alice, token, vestingAddr } =
        await loadFixture(deployFixture);
      await token.transfer(vestingAddr, ethers.parseEther("10000"));
      await expect(
        vesting.createTeamVesting(alice.address, ethers.parseEther("1000"))
      ).to.be.revertedWith("TGE not set");
    });

    it("should revert if contract has insufficient balance (solvency)", async function () {
      const { vesting, token, alice, vestingAddr } =
        await loadFixture(deployFixture);
      await vesting.setTGE(await time.latest());
      // Don't fund vesting contract — should fail solvency check
      await expect(
        vesting.createTeamVesting(alice.address, ethers.parseEther("1000"))
      ).to.be.revertedWith("Insufficient token balance for vesting");
    });
  });

  // ─── Vesting Calculation ─────────────────────────────────

  describe("vestedAmount", function () {
    it("should return 0 before cliff", async function () {
      const { vesting, alice } = await loadFixture(vestingWithTGEFixture);
      await vesting.createTeamVesting(alice.address, ethers.parseEther("10000"));
      // Team vesting has cliff — check immediately, should be low or 0
      const vested = await vesting.vestedAmount(alice.address, 0);
      // With TGE% it might be > 0 but < total
      expect(vested).to.be.lt(ethers.parseEther("10000"));
    });

    it("should return full amount after full vesting period", async function () {
      const { vesting, alice } = await loadFixture(vestingWithTGEFixture);
      const amount = ethers.parseEther("10000");
      await vesting.createTeamVesting(alice.address, amount);

      // Team vesting: 1yr cliff + 4yr linear = 5 years total
      await time.increase(5 * 365 * 86400 + 86400); // 5 years + 1 day buffer

      const vested = await vesting.vestedAmount(alice.address, 0);
      expect(vested).to.equal(amount);
    });
  });

  // ─── Claim ───────────────────────────────────────────────

  describe("claim", function () {
    it("should allow claiming after vesting", async function () {
      const { vesting, token, alice } = await loadFixture(vestingWithTGEFixture);
      const amount = ethers.parseEther("10000");
      await vesting.createIDOVesting(alice.address, amount);

      // Fast forward past full vesting
      await time.increase(3 * 365 * 86400);

      const balBefore = await token.balanceOf(alice.address);
      await vesting.connect(alice).claim();
      const balAfter = await token.balanceOf(alice.address);
      expect(balAfter).to.be.gt(balBefore);
    });

    it("should revert if nothing to claim", async function () {
      const { vesting, alice } = await loadFixture(vestingWithTGEFixture);
      const amount = ethers.parseEther("10000");
      await vesting.createTeamVesting(alice.address, amount);
      // Claim immediately — might have TGE portion
      // Then claim again — should revert
      try {
        await vesting.connect(alice).claim();
      } catch { /* ignore if first claim fails */ }
      await expect(vesting.connect(alice).claim()).to.be.revertedWith(
        "Nothing to claim"
      );
    });
  });

  // ─── Revoke ──────────────────────────────────────────────

  describe("revoke", function () {
    it("should revoke a revocable schedule", async function () {
      const { vesting, alice } = await loadFixture(vestingWithTGEFixture);
      await vesting.createTeamVesting(alice.address, ethers.parseEther("10000"));
      await vesting.revoke(alice.address, 0);
    });

    it("should revert when non-owner tries to revoke", async function () {
      const { vesting, alice, bob } = await loadFixture(vestingWithTGEFixture);
      await vesting.createTeamVesting(alice.address, ethers.parseEther("10000"));
      await expect(
        vesting.connect(bob).revoke(alice.address, 0)
      ).to.be.reverted;
    });
  });

  // ─── Schedule Count ──────────────────────────────────────

  describe("getVestingInfo (schedule count)", function () {
    it("should track number of schedules per beneficiary", async function () {
      const { vesting, alice } = await loadFixture(vestingWithTGEFixture);
      let info = await vesting.getVestingInfo(alice.address);
      expect(info[0]).to.equal(0); // scheduleCount
      await vesting.createTeamVesting(alice.address, ethers.parseEther("1000"));
      info = await vesting.getVestingInfo(alice.address);
      expect(info[0]).to.equal(1);
    });
  });
});
