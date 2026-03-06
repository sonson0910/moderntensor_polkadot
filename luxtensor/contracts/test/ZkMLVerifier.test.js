// SPDX-License-Identifier: MIT
/**
 * ZkMLVerifier — Full Test Suite
 *
 * Tests: dev mode verification, proof caching, access control,
 *        trust management, proof types, admin functions
 */

const { expect } = require("chai");
const { ethers } = require("hardhat");
const {
  loadFixture,
  time,
} = require("@nomicfoundation/hardhat-network-helpers");

describe("ZkMLVerifier", function () {
  async function deployFixture() {
    const [owner, verifier, outsider] = await ethers.getSigners();

    const ZkMLVerifier = await ethers.getContractFactory("ZkMLVerifier");
    const zkml = await ZkMLVerifier.deploy();
    await zkml.waitForDeployment();

    // Enable dev mode for testing
    await zkml.setDevMode(true);

    const imageId = ethers.keccak256(ethers.toUtf8Bytes("test-model-image"));
    await zkml.trustImage(imageId);

    return { zkml, owner, verifier, outsider, imageId };
  }

  // ─── Deployment ──────────────────────────────────────────

  describe("Deployment", function () {
    it("should set owner correctly", async function () {
      const { zkml, owner } = await loadFixture(deployFixture);
      expect(await zkml.owner()).to.equal(owner.address);
    });

    it("should start with dev mode disabled (before fixture enables it)", async function () {
      const [owner] = await ethers.getSigners();
      const ZkMLVerifier = await ethers.getContractFactory("ZkMLVerifier");
      const zkml = await ZkMLVerifier.deploy();
      await zkml.waitForDeployment();
      expect(await zkml.devModeEnabled()).to.equal(false);
    });
  });

  // ─── Dev Mode ────────────────────────────────────────────

  describe("Dev Mode", function () {
    it("should toggle dev mode", async function () {
      const { zkml } = await loadFixture(deployFixture);
      await expect(zkml.setDevMode(false))
        .to.emit(zkml, "DevModeToggled")
        .withArgs(false);
      expect(await zkml.devModeEnabled()).to.equal(false);
    });

    it("should revert for non-owner", async function () {
      const { zkml, outsider } = await loadFixture(deployFixture);
      await expect(zkml.connect(outsider).setDevMode(true)).to.be.reverted;
    });
  });

  // ─── Trust Management ────────────────────────────────────

  describe("Trust Management", function () {
    it("should trust an image", async function () {
      const { zkml } = await loadFixture(deployFixture);
      const newImage = ethers.keccak256(ethers.toUtf8Bytes("new-model"));
      await expect(zkml.trustImage(newImage))
        .to.emit(zkml, "ImageTrusted")
        .withArgs(newImage);
      expect(await zkml.isImageTrusted(newImage)).to.equal(true);
    });

    it("should revoke an image", async function () {
      const { zkml, imageId } = await loadFixture(deployFixture);
      await zkml.revokeImage(imageId);
      expect(await zkml.isImageTrusted(imageId)).to.equal(false);
    });

    it("should trust multiple images at once", async function () {
      const { zkml } = await loadFixture(deployFixture);
      const images = [
        ethers.keccak256(ethers.toUtf8Bytes("img1")),
        ethers.keccak256(ethers.toUtf8Bytes("img2")),
        ethers.keccak256(ethers.toUtf8Bytes("img3")),
      ];
      await zkml.trustImages(images);
      for (const img of images) {
        expect(await zkml.isImageTrusted(img)).to.equal(true);
      }
    });

    it("should revert trust for non-owner", async function () {
      const { zkml, outsider } = await loadFixture(deployFixture);
      const img = ethers.keccak256(ethers.toUtf8Bytes("x"));
      await expect(zkml.connect(outsider).trustImage(img)).to.be.reverted;
    });
  });

  // ─── Verification (Dev Mode) ────────────────────────────

  describe("Verification (Dev Mode)", function () {
    it("should verify a valid dev proof via verifyProof()", async function () {
      const { zkml, imageId } = await loadFixture(deployFixture);
      const journal = ethers.toUtf8Bytes("journal-data-123");
      // Dev mode seal = keccak256(imageId || journal)
      const seal = ethers.keccak256(
        ethers.solidityPacked(["bytes32", "bytes"], [imageId, journal])
      );
      const proofType = 2; // DEV

      const [isValid, journalHash] = await zkml.verifyProof.staticCall(
        imageId, journal, seal, proofType
      );
      expect(isValid).to.equal(true);
    });

    it("should reject invalid dev proof", async function () {
      const { zkml, imageId } = await loadFixture(deployFixture);
      const journal = ethers.toUtf8Bytes("journal-data");
      const badSeal = ethers.keccak256(ethers.toUtf8Bytes("wrong-seal"));
      const proofType = 2; // DEV

      const [isValid] = await zkml.verifyProof.staticCall(
        imageId, journal, badSeal, proofType
      );
      expect(isValid).to.equal(false);
    });

    it("should verify via verify() with encoded data", async function () {
      const { zkml, imageId } = await loadFixture(deployFixture);
      const journal = ethers.toUtf8Bytes("test-journal");
      const seal = ethers.keccak256(
        ethers.solidityPacked(["bytes32", "bytes"], [imageId, journal])
      );
      const proofType = 2;

      // Encode as ProofData struct: (bytes32 imageId, bytes journal, bytes seal, uint8 proofType)
      // seal is bytes32 but struct expects bytes — convert to raw bytes
      const sealBytes = ethers.getBytes(seal);
      const encoded = ethers.AbiCoder.defaultAbiCoder().encode(
        ["tuple(bytes32, bytes, bytes, uint8)"],
        [[imageId, journal, sealBytes, proofType]]
      );

      // verify() modifies state (caches proof), so use a regular call + check event
      await expect(zkml.verify(encoded))
        .to.emit(zkml, "ProofVerified");
    });

    it("should cache verified proofs", async function () {
      const { zkml, imageId } = await loadFixture(deployFixture);
      const journal = ethers.toUtf8Bytes("cache-test");
      const seal = ethers.keccak256(
        ethers.solidityPacked(["bytes32", "bytes"], [imageId, journal])
      );

      // Call the state-modifying version to cache
      await zkml.verifyProof(imageId, journal, seal, 2);

      // Check cached proof exists
      const proofHash = await zkml.computeProofHash(imageId, journal, seal);
      const cached = await zkml.getVerification(proofHash);
      expect(cached.isValid).to.equal(true);
      expect(cached.imageId).to.equal(imageId);
    });
  });

  // ─── STARK Proof (should fail on non-RISC0 chain) ──────

  describe("STARK Proof", function () {
    it("should revert for STARK proofs (no RISC0 precompile)", async function () {
      const { zkml, imageId } = await loadFixture(deployFixture);
      const journal = ethers.toUtf8Bytes("stark-test");
      const seal = ethers.randomBytes(32);

      // STARK = 0, should revert on local hardhat (no RISC Zero precompile)
      await expect(
        zkml.verifyProof(imageId, journal, seal, 0)
      ).to.be.reverted;
    });
  });

  // ─── Access Control for Verification ────────────────────

  describe("Access Control", function () {
    it("should restrict verification when openVerification is false", async function () {
      const { zkml, outsider, imageId } = await loadFixture(deployFixture);
      await zkml.setOpenVerification(false);

      const journal = ethers.toUtf8Bytes("restricted");
      const seal = ethers.keccak256(
        ethers.solidityPacked(["bytes32", "bytes"], [imageId, journal])
      );

      await expect(
        zkml.connect(outsider).verifyProof(imageId, journal, seal, 2)
      ).to.be.revertedWith("Not authorized to verify");
    });

    it("should allow authorized verifier even when closed", async function () {
      const { zkml, verifier, imageId } = await loadFixture(deployFixture);
      await zkml.setOpenVerification(false);
      await zkml.setAuthorizedVerifier(verifier.address, true);

      const journal = ethers.toUtf8Bytes("authorized");
      const seal = ethers.keccak256(
        ethers.solidityPacked(["bytes32", "bytes"], [imageId, journal])
      );

      // Should succeed
      await zkml.connect(verifier).verifyProof(imageId, journal, seal, 2);
    });
  });

  // ─── Admin Functions ─────────────────────────────────────

  describe("Admin", function () {
    it("should set max proof age", async function () {
      const { zkml } = await loadFixture(deployFixture);
      await zkml.setMaxProofAge(1800); // 30 minutes
      expect(await zkml.maxProofAge()).to.equal(1800);
    });

    it("should revert max proof age out of range", async function () {
      const { zkml } = await loadFixture(deployFixture);
      await expect(zkml.setMaxProofAge(10)).to.be.revertedWith(
        "Invalid age"
      );
    });

    it("should set verification key gamma", async function () {
      const { zkml } = await loadFixture(deployFixture);
      await zkml.setVerificationKeyGamma([1, 2, 3, 4]);
      expect(await zkml.vkGammaSet()).to.equal(true);
    });

    it("should set authorized verifier", async function () {
      const { zkml, verifier } = await loadFixture(deployFixture);
      await zkml.setAuthorizedVerifier(verifier.address, true);
      expect(await zkml.authorizedVerifiers(verifier.address)).to.equal(true);
    });
  });
});
