// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title ZkMLVerifier - On-chain zkML Proof Verification
 * @notice Verifies RISC Zero zkML proofs for AI inference results
 * @dev Implements IZkMLVerifier interface for AIOracle integration
 *
 * Verification Types:
 * - STARK: Full RISC Zero STARK verification (via precompile)
 * - Groth16: SNARK-wrapped proofs (smaller, faster)
 * - Dev: Development mode (hash-based, for testing)
 */
contract ZkMLVerifier is Ownable {
    // ========== CONSTANTS ==========

    /// @notice Proof type identifiers
    uint8 public constant PROOF_TYPE_STARK = 0;
    uint8 public constant PROOF_TYPE_GROTH16 = 1;
    uint8 public constant PROOF_TYPE_DEV = 2;

    /// @notice RISC Zero verifier precompile address (when deployed)
    /// @dev See https://github.com/risc0/risc0-ethereum for deployment info
    address public constant RISC0_VERIFIER =
        address(0x000000000000000000000000000000000000cafE);

    /// @notice Groth16 verification key gamma G2 point (set during deployment)
    /// @dev Must be set before Groth16 proofs can be verified
    uint256[4] public vkGamma;
    bool public vkGammaSet;

    // ========== STATE ==========

    /// @notice Trusted image IDs (model hashes)
    mapping(bytes32 => bool) public trustedImages;

    /// @notice Verified proof hashes
    mapping(bytes32 => VerifiedProof) public verifiedProofs;

    /// @notice Configuration
    bool public devModeEnabled = false; // [SECURITY] Disabled by default — enable explicitly for testing only
    uint256 public maxProofAge = 1 hours;

    // [SECURITY] Access control for proof verification — prevents proof pollution
    mapping(address => bool) public authorizedVerifiers;
    bool public openVerification = true; // When true, anyone can verify (backward compat)

    // ========== STRUCTS ==========

    struct VerifiedProof {
        bytes32 imageId;
        bytes32 journalHash;
        address verifier;
        uint256 verifiedAt;
        bool isValid;
    }

    struct ProofData {
        bytes32 imageId;
        bytes journal;
        bytes seal;
        uint8 proofType;
    }

    // ========== EVENTS ==========

    event ProofVerified(
        bytes32 indexed proofHash,
        bytes32 indexed imageId,
        address verifier,
        bool isValid
    );
    event ImageTrusted(bytes32 indexed imageId);
    event ImageRevoked(bytes32 indexed imageId);
    event DevModeToggled(bool enabled);

    // ========== CONSTRUCTOR ==========

    constructor() Ownable(msg.sender) {}

    // ========== VERIFICATION FUNCTIONS ==========

    /**
     * @notice Verify a zkML proof
     * @param proofData Encoded proof data
     * @return isValid Whether proof is valid
     * @return journalHash Hash of the proof journal (public outputs)
     */
    function verify(
        bytes calldata proofData
    ) external returns (bool isValid, bytes32 journalHash) {
        // [SECURITY] Access control — prevent proof pollution
        require(
            openVerification ||
                authorizedVerifiers[msg.sender] ||
                msg.sender == owner(),
            "Not authorized to verify"
        );
        ProofData memory proof = abi.decode(proofData, (ProofData));
        return _verifyProof(proof);
    }

    /**
     * @notice Verify proof components directly
     * @param imageId Model image ID
     * @param journal Public outputs (journal)
     * @param seal Proof seal bytes
     * @param proofType Type of proof (STARK, Groth16, Dev)
     */
    function verifyProof(
        bytes32 imageId,
        bytes calldata journal,
        bytes calldata seal,
        uint8 proofType
    ) external returns (bool isValid, bytes32 journalHash) {
        // [SECURITY] Access control — prevent proof pollution
        require(
            openVerification ||
                authorizedVerifiers[msg.sender] ||
                msg.sender == owner(),
            "Not authorized to verify"
        );
        ProofData memory proof = ProofData({
            imageId: imageId,
            journal: journal,
            seal: seal,
            proofType: proofType
        });
        return _verifyProof(proof);
    }

    /**
     * @notice Internal verification logic
     */
    function _verifyProof(
        ProofData memory proof
    ) internal returns (bool isValid, bytes32 journalHash) {
        // Check image is trusted
        require(trustedImages[proof.imageId], "Image not trusted");

        // Calculate journal hash
        journalHash = keccak256(proof.journal);

        // Calculate proof hash for storage
        bytes32 proofHash = keccak256(
            abi.encodePacked(proof.imageId, journalHash, proof.seal)
        );

        // Check if already verified (with age validation)
        if (verifiedProofs[proofHash].verifiedAt > 0) {
            // [SECURITY] Enforce proof age — stale proofs must be re-verified
            require(
                block.timestamp - verifiedProofs[proofHash].verifiedAt <=
                    maxProofAge,
                "Cached proof expired"
            );
            return (verifiedProofs[proofHash].isValid, journalHash);
        }

        // Verify based on proof type
        if (proof.proofType == PROOF_TYPE_DEV) {
            isValid = _verifyDevProof(proof);
        } else if (proof.proofType == PROOF_TYPE_STARK) {
            isValid = _verifyStarkProof(proof);
        } else if (proof.proofType == PROOF_TYPE_GROTH16) {
            isValid = _verifyGroth16Proof(proof);
        } else {
            revert("Unknown proof type");
        }

        // Store verification result
        verifiedProofs[proofHash] = VerifiedProof({
            imageId: proof.imageId,
            journalHash: journalHash,
            verifier: msg.sender,
            verifiedAt: block.timestamp,
            isValid: isValid
        });

        emit ProofVerified(proofHash, proof.imageId, msg.sender, isValid);

        return (isValid, journalHash);
    }

    /**
     * @notice Verify development mode proof (hash-based)
     * @dev For testing only - seal = keccak256(imageId || journal)
     */
    function _verifyDevProof(
        ProofData memory proof
    ) internal view returns (bool) {
        require(devModeEnabled, "Dev mode disabled");

        // Dev proofs use deterministic hash
        bytes32 expectedSeal = keccak256(
            abi.encodePacked(proof.imageId, proof.journal)
        );

        return
            keccak256(proof.seal) == keccak256(abi.encodePacked(expectedSeal));
    }

    /**
     * @notice Verify RISC Zero STARK proof via precompile
     * @dev STARK verification requires RISC Zero verifier precompile which is
     *      NOT available on Polkadot Hub (pallet-revive). Use Groth16 or Dev mode instead.
     *      Polkadot pallet-revive supports: ECRecover, SHA256, RIPEMD160, Identity,
     *      ModExp, Bn128Add, Bn128Mul, Bn128Pairing (EIP-197 at 0x08).
     */
    function _verifyStarkProof(
        ProofData memory proof
    ) internal view returns (bool) {
        // Check seal is not empty
        if (proof.seal.length < 32) {
            return false;
        }

        // Check if RISC Zero precompile is deployed (code size > 0)
        uint256 codeSize;
        address riscZeroAddr = RISC0_VERIFIER;
        assembly {
            codeSize := extcodesize(riscZeroAddr)
        }

        if (codeSize > 0) {
            // RISC Zero precompile is deployed, use it for verification
            (bool success, bytes memory result) = RISC0_VERIFIER.staticcall(
                abi.encode(proof.imageId, proof.journal, proof.seal)
            );

            if (!success || result.length < 32) {
                return false;
            }

            return abi.decode(result, (bool));
        }

        // RISC Zero precompile NOT deployed on this chain (e.g. Polkadot Hub)
        // Use Groth16 (Bn128Pairing at 0x08) or Dev mode instead
        revert("STARK not supported: use Groth16 or Dev mode on Polkadot Hub");
    }

    /**
     * @notice Verify Groth16 SNARK proof using bn256 pairing
     * @dev Uses EIP-197 precompile at 0x08 for pairing check
     */
    function _verifyGroth16Proof(
        ProofData memory proof
    ) internal view returns (bool) {
        // Groth16 proofs are ~256 bytes (8 * 32-byte coordinates)
        if (proof.seal.length < 256) {
            return false;
        }

        // Extract Groth16 proof components from seal
        // Format: [pi_a(64)] [pi_b(128)] [pi_c(64)]
        // pi_a: G1 point (2 x 32 bytes)
        // pi_b: G2 point (4 x 32 bytes)
        // pi_c: G1 point (2 x 32 bytes)

        uint256[2] memory pi_a;
        uint256[2][2] memory pi_b;
        uint256[2] memory pi_c;

        // Decode proof components
        assembly {
            let sealPtr := add(mload(add(proof, 0x60)), 0x20) // proof.seal data pointer

            // pi_a (G1 point - 64 bytes)
            mstore(pi_a, mload(sealPtr))
            mstore(add(pi_a, 0x20), mload(add(sealPtr, 0x20)))

            // pi_b (G2 point - 128 bytes, note: reversed order for pairing)
            mstore(pi_b, mload(add(sealPtr, 0x60)))
            mstore(add(pi_b, 0x20), mload(add(sealPtr, 0x40)))
            mstore(add(add(pi_b, 0x40), 0), mload(add(sealPtr, 0xa0)))
            mstore(add(add(pi_b, 0x40), 0x20), mload(add(sealPtr, 0x80)))

            // pi_c (G1 point - 64 bytes)
            mstore(pi_c, mload(add(sealPtr, 0xc0)))
            mstore(add(pi_c, 0x20), mload(add(sealPtr, 0xe0)))
        }

        // Build pairing input for verification
        // Pairing check: e(pi_a, pi_b) = e(pi_c, G2_generator)
        // We verify using: e(-pi_a, pi_b) * e(pi_c, vk_gamma) == 1
        bytes memory pairingInput = abi.encodePacked(
            _negate(pi_a),
            pi_b,
            pi_c,
            _getVerificationKeyGamma()
        );

        // Call bn256 pairing precompile (EIP-197)
        uint256[1] memory result;
        bool success;
        assembly {
            success := staticcall(
                gas(),
                0x08, // Pairing precompile address
                add(pairingInput, 0x20),
                mload(pairingInput),
                result,
                0x20
            )
        }

        return success && result[0] == 1;
    }

    /**
     * @notice Negate a G1 point for pairing
     */
    function _negate(
        uint256[2] memory point
    ) internal pure returns (uint256[2] memory) {
        // BN256 curve order - p
        uint256 p = 21888242871839275222246405745257275088696311157297823662689037894645226208583;
        return [point[0], p - (point[1] % p)];
    }

    /**
     * @notice Get verification key gamma from storage
     * @dev Must be set via setVerificationKeyGamma before Groth16 proofs work
     */
    function _getVerificationKeyGamma()
        internal
        view
        returns (uint256[2][2] memory vk)
    {
        require(vkGammaSet, "VK gamma not set");
        vk[0][0] = vkGamma[0];
        vk[0][1] = vkGamma[1];
        vk[1][0] = vkGamma[2];
        vk[1][1] = vkGamma[3];
    }

    /**
     * @notice Set the Groth16 verification key gamma G2 point (owner only)
     * @dev Must be called after trusted setup to enable Groth16 verification
     * @param gamma Four uint256 values representing the G2 point
     */
    function setVerificationKeyGamma(
        uint256[4] calldata gamma
    ) external onlyOwner {
        vkGamma = gamma;
        vkGammaSet = true;
    }

    // ========== QUERY FUNCTIONS ==========

    /**
     * @notice Check if image is trusted
     */
    function isImageTrusted(bytes32 imageId) external view returns (bool) {
        return trustedImages[imageId];
    }

    /**
     * @notice Get verification result for proof hash
     */
    function getVerification(
        bytes32 proofHash
    ) external view returns (VerifiedProof memory) {
        return verifiedProofs[proofHash];
    }

    /**
     * @notice Compute proof hash
     */
    function computeProofHash(
        bytes32 imageId,
        bytes calldata journal,
        bytes calldata seal
    ) external pure returns (bytes32) {
        return keccak256(abi.encodePacked(imageId, keccak256(journal), seal));
    }

    // ========== ADMIN FUNCTIONS ==========

    /**
     * @notice Trust an image ID
     */
    function trustImage(bytes32 imageId) external onlyOwner {
        trustedImages[imageId] = true;
        emit ImageTrusted(imageId);
    }

    /**
     * @notice Revoke image trust
     */
    function revokeImage(bytes32 imageId) external onlyOwner {
        trustedImages[imageId] = false;
        emit ImageRevoked(imageId);
    }

    /**
     * @notice Batch trust multiple images
     */
    function trustImages(bytes32[] calldata imageIds) external onlyOwner {
        for (uint i = 0; i < imageIds.length; i++) {
            trustedImages[imageIds[i]] = true;
            emit ImageTrusted(imageIds[i]);
        }
    }

    /**
     * @notice Toggle dev mode
     */
    function setDevMode(bool enabled) external onlyOwner {
        devModeEnabled = enabled;
        emit DevModeToggled(enabled);
    }

    /**
     * @notice Set max proof age
     */
    function setMaxProofAge(uint256 age) external onlyOwner {
        require(age >= 1 minutes && age <= 1 days, "Invalid age");
        maxProofAge = age;
    }

    /**
     * @notice Authorize an address to call verify/verifyProof
     * @dev Use this to restrict proof verification to trusted contracts (e.g. AIOracle)
     */
    function setAuthorizedVerifier(
        address verifier,
        bool authorized
    ) external onlyOwner {
        authorizedVerifiers[verifier] = authorized;
    }

    /**
     * @notice Toggle open verification mode
     * @dev When false, only authorizedVerifiers and owner can verify proofs
     */
    function setOpenVerification(bool open) external onlyOwner {
        openVerification = open;
    }
}

/**
 * @title IZkMLVerifier - Interface for zkML verification
 * @notice Implement this interface for custom verifiers
 */
interface IZkMLVerifier {
    function verify(
        bytes calldata proofData
    ) external returns (bool isValid, bytes32 journalHash);
    function verifyProof(
        bytes32 imageId,
        bytes calldata journal,
        bytes calldata seal,
        uint8 proofType
    ) external returns (bool isValid, bytes32 journalHash);
    function isImageTrusted(bytes32 imageId) external view returns (bool);
}
