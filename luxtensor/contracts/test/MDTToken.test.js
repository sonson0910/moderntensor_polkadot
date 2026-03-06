// SPDX-License-Identifier: MIT
/**
 * MDTToken — Full Test Suite
 *
 * Tests: TGE, mintCategory, finishMinting, allocations, MAX_SUPPLY
 */

const { expect } = require("chai");
const { ethers } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");

describe("MDTToken", function () {
  async function deployFixture() {
    const [owner, alice, bob] = await ethers.getSigners();
    const MDTToken = await ethers.getContractFactory("MDTToken");
    const token = await MDTToken.deploy();
    await token.waitForDeployment();
    return { token, owner, alice, bob };
  }

  // ─── Deployment ──────────────────────────────────────────

  describe("Deployment", function () {
    it("should have correct name and symbol", async function () {
      const { token } = await loadFixture(deployFixture);
      expect(await token.name()).to.equal("ModernTensor");
      expect(await token.symbol()).to.equal("MDT");
    });

    it("should start with zero total supply", async function () {
      const { token } = await loadFixture(deployFixture);
      expect(await token.totalSupply()).to.equal(0);
    });

    it("should have MAX_SUPPLY of 21 million", async function () {
      const { token } = await loadFixture(deployFixture);
      expect(await token.MAX_SUPPLY()).to.equal(ethers.parseEther("21000000"));
    });

    it("should not have minting finished", async function () {
      const { token } = await loadFixture(deployFixture);
      expect(await token.mintingFinished()).to.equal(false);
    });
  });

  // ─── Category Allocations ────────────────────────────────

  describe("Category Allocations", function () {
    it("should return correct allocations for all 8 categories", async function () {
      const { token } = await loadFixture(deployFixture);
      const allocs = await token.getAllocations();
      const max = ethers.parseEther("21000000");
      // Category 0: EmissionRewards 45%
      expect(allocs[0]).to.equal((max * 4500n) / 10000n);
      // Category 1: EcosystemGrants 12%
      expect(allocs[1]).to.equal((max * 1200n) / 10000n);
      // Category 4: IDO 5%
      expect(allocs[4]).to.equal((max * 500n) / 10000n);
    });

    it("should report correct remaining allocation", async function () {
      const { token, owner } = await loadFixture(deployFixture);
      const alloc0 = await token.remainingAllocation(0);
      expect(alloc0).to.equal((ethers.parseEther("21000000") * 4500n) / 10000n);

      // Mint some, remaining decreases
      await token.mintCategory(0, owner.address, ethers.parseEther("1000"));
      const remaining = await token.remainingAllocation(0);
      expect(remaining).to.equal(alloc0 - ethers.parseEther("1000"));
    });
  });

  // ─── mintCategory ────────────────────────────────────────

  describe("mintCategory", function () {
    it("should mint to specified address", async function () {
      const { token, alice } = await loadFixture(deployFixture);
      await token.mintCategory(1, alice.address, ethers.parseEther("100"));
      expect(await token.balanceOf(alice.address)).to.equal(ethers.parseEther("100"));
    });

    it("should update categoryMinted", async function () {
      const { token, owner } = await loadFixture(deployFixture);
      await token.mintCategory(0, owner.address, ethers.parseEther("5000"));
      expect(await token.categoryMinted(0)).to.equal(ethers.parseEther("5000"));
    });

    it("should emit CategoryMinted event", async function () {
      const { token, alice } = await loadFixture(deployFixture);
      await expect(token.mintCategory(2, alice.address, ethers.parseEther("50")))
        .to.emit(token, "CategoryMinted")
        .withArgs(2, alice.address, ethers.parseEther("50"));
    });

    it("should revert when exceeding category allocation", async function () {
      const { token, owner } = await loadFixture(deployFixture);
      const alloc4 = await token.remainingAllocation(4); // IDO = 5%
      await expect(
        token.mintCategory(4, owner.address, alloc4 + 1n)
      ).to.be.revertedWith("MDTToken: exceeds category allocation");
    });

    it("should revert when non-owner calls", async function () {
      const { token, alice } = await loadFixture(deployFixture);
      await expect(
        token.connect(alice).mintCategory(0, alice.address, 100)
      ).to.be.reverted;
    });
  });

  // ─── executeTGE ──────────────────────────────────────────

  describe("executeTGE", function () {
    it("should mint entire category allocation", async function () {
      const { token, owner } = await loadFixture(deployFixture);
      const alloc = await token.remainingAllocation(4); // IDO 5%
      await token.executeTGE(4, owner.address);
      expect(await token.balanceOf(owner.address)).to.equal(alloc);
      expect(await token.categoryMinted(4)).to.equal(alloc);
    });

    it("should set tgeTimestamp on first call", async function () {
      const { token, owner } = await loadFixture(deployFixture);
      expect(await token.tgeTimestamp()).to.equal(0);
      await token.executeTGE(0, owner.address);
      expect(await token.tgeTimestamp()).to.be.gt(0);
    });

    it("should emit CategoryMinted event on executeTGE", async function () {
      const { token, owner } = await loadFixture(deployFixture);
      await expect(token.executeTGE(0, owner.address))
        .to.emit(token, "CategoryMinted");
    });

    it("should revert if category already fully minted", async function () {
      const { token, owner } = await loadFixture(deployFixture);
      await token.executeTGE(4, owner.address);
      await expect(token.executeTGE(4, owner.address)).to.be.revertedWith(
        "MDTToken: category already minted"
      );
    });

    it("should revert when non-owner calls", async function () {
      const { token, alice } = await loadFixture(deployFixture);
      await expect(
        token.connect(alice).executeTGE(0, alice.address)
      ).to.be.reverted;
    });
  });

  // ─── finishMinting ───────────────────────────────────────

  describe("finishMinting", function () {
    it("should revert if not all categories minted", async function () {
      const { token } = await loadFixture(deployFixture);
      await expect(token.finishMinting()).to.be.revertedWith(
        "MDTToken: not all categories minted"
      );
    });

    it("should succeed after all categories are fully minted", async function () {
      const { token, owner } = await loadFixture(deployFixture);
      // Execute TGE for all 8 categories
      for (let i = 0; i < 8; i++) {
        await token.executeTGE(i, owner.address);
      }
      expect(await token.totalSupply()).to.equal(ethers.parseEther("21000000"));
      await expect(token.finishMinting())
        .to.emit(token, "MintingFinished");
      expect(await token.mintingFinished()).to.equal(true);
    });

    it("should prevent further minting after finalized", async function () {
      const { token, owner } = await loadFixture(deployFixture);
      for (let i = 0; i < 8; i++) {
        await token.executeTGE(i, owner.address);
      }
      await token.finishMinting();
      await expect(
        token.mintCategory(0, owner.address, 1)
      ).to.be.reverted;
    });
  });

  // ─── allCategoriesMinted ─────────────────────────────────

  describe("allCategoriesMinted", function () {
    it("should return false initially", async function () {
      const { token } = await loadFixture(deployFixture);
      expect(await token.allCategoriesMinted()).to.equal(false);
    });

    it("should return true after all TGEs", async function () {
      const { token, owner } = await loadFixture(deployFixture);
      for (let i = 0; i < 8; i++) {
        await token.executeTGE(i, owner.address);
      }
      expect(await token.allCategoriesMinted()).to.equal(true);
    });
  });
});
