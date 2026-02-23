// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title TrustGraph - Social Trust Scoring System
 * @notice On-chain reputation + attestation-based trust classification (no precompiles)
 * @dev Trust is computed from weighted attestations — pure Solidity, fully on-chain
 *
 * Use Cases:
 * - DeFi: Under-collateralized lending based on reputation
 * - DAO: Voting weight based on trust score
 * - Marketplace: Buyer/seller trust verification
 * - Social: Content creator authenticity
 *
 * Architecture:
 * 1. Users register profiles on-chain
 * 2. Approved protocols (attesters) submit trust attestations
 * 3. Trust level is computed from weighted attestation scores
 * 4. Cross-protocol queries enable portable reputation
 *
 * Trust Levels:
 * - 0: Unknown (new or insufficient data)
 * - 1: Risky (flagged behavior patterns)
 * - 2: Neutral (normal behavior)
 * - 3: Trusted (positive behavior patterns)
 * - 4: Verified (exceptional reputation)
 */
contract TrustGraph is Ownable, ReentrancyGuard {
    // ==================== ENUMS ====================

    /// @notice Trust classification levels
    enum TrustLevel {
        Unknown, // 0 - New user, insufficient data
        Risky, // 1 - Flagged patterns
        Neutral, // 2 - Normal behavior
        Trusted, // 3 - Good reputation
        Verified // 4 - Exceptional
    }

    // ==================== STRUCTS ====================

    /// @notice User trust profile
    struct TrustProfile {
        TrustLevel level; // Current classification
        uint256 confidence; // Classification confidence (0-1e18)
        uint256 positiveActions; // Count of positive signals
        uint256 negativeActions; // Count of negative signals
        uint256 lastUpdated; // Timestamp
        bool isVerified; // Manual verification status
        bool exists; // Profile exists flag
    }

    /// @notice Trust attestation from another protocol
    struct Attestation {
        address attester; // Protocol that attested
        TrustLevel attestedLevel; // Attested trust level
        uint256 weight; // Attestation weight
        uint256 timestamp;
        string reason;
    }

    // ==================== STATE ====================

    /// @notice User profiles
    mapping(address => TrustProfile) public profiles;

    /// @notice Attestations per user
    mapping(address => Attestation[]) public attestations;

    /// @notice Approved attesters (protocols that can attest)
    mapping(address => bool) public approvedAttesters;

    /// @notice Minimum confidence for valid classification
    uint256 public minConfidence;

    /// @notice Attestation weight thresholds
    uint256 public constant WEIGHT_THRESHOLD = 1000;

    /// @notice Maximum attestations per user to prevent Gas DoS
    uint256 public constant MAX_ATTESTATIONS = 100;

    /// @notice Thresholds for trust levels (weighted average * 1e18)
    /// Level boundaries: Unknown<0.5e18, Risky<1.5e18, Neutral<2.5e18, Trusted<3.5e18, Verified>=3.5e18
    uint256 public constant RISKY_THRESHOLD = 5e17;
    uint256 public constant NEUTRAL_THRESHOLD = 15e17;
    uint256 public constant TRUSTED_THRESHOLD = 25e17;
    uint256 public constant VERIFIED_THRESHOLD = 35e17;

    // ==================== EVENTS ====================

    event ProfileCreated(address indexed user);

    event TrustClassified(
        address indexed user,
        TrustLevel level,
        uint256 confidence
    );

    event AttestationReceived(
        address indexed user,
        address indexed attester,
        TrustLevel level
    );

    event TrustLevelUpgraded(
        address indexed user,
        TrustLevel from,
        TrustLevel to
    );

    event TrustLevelDowngraded(
        address indexed user,
        TrustLevel from,
        TrustLevel to
    );

    // ==================== ERRORS ====================

    error ProfileNotFound(address user);
    error ProfileExists(address user);
    error UnauthorizedAttester(address attester);
    error InsufficientData(address user);
    error AlreadyVerified(address user);
    error MaxAttestationsReached(address user);

    // ==================== CONSTRUCTOR ====================

    /**
     * @notice Initialize TrustGraph
     * @param minConfidence_ Minimum classification confidence (0-1e18)
     */
    constructor(uint256 minConfidence_) Ownable(msg.sender) {
        minConfidence = minConfidence_;
    }

    // ==================== PROFILE MANAGEMENT ====================

    /**
     * @notice Register a user's trust profile
     * @param user User address
     */
    function registerProfile(address user) external nonReentrant {
        if (profiles[user].exists) revert ProfileExists(user);

        profiles[user] = TrustProfile({
            level: TrustLevel.Unknown,
            confidence: 0,
            positiveActions: 0,
            negativeActions: 0,
            lastUpdated: block.timestamp,
            isVerified: false,
            exists: true
        });

        emit ProfileCreated(user);
    }

    /**
     * @notice Classify user's trust level from attestation data
     * @param user User to classify
     * @return level Classified trust level
     * @return confidence Classification confidence
     *
     * @dev Trust level is computed from weighted-average attestation score
     */
    function classifyTrust(
        address user
    ) external nonReentrant returns (TrustLevel level, uint256 confidence) {
        TrustProfile storage profile = profiles[user];
        if (!profile.exists) revert ProfileNotFound(user);

        Attestation[] storage userAttestations = attestations[user];
        if (userAttestations.length < 2) revert InsufficientData(user);

        // Compute weighted average trust level
        uint256 totalWeight = 0;
        uint256 weightedSum = 0;

        for (uint256 i = 0; i < userAttestations.length; i++) {
            totalWeight += userAttestations[i].weight;
            weightedSum +=
                uint256(userAttestations[i].attestedLevel) *
                userAttestations[i].weight *
                1e18;
        }

        uint256 avgLevel = weightedSum / totalWeight; // scaled by 1e18

        // Classify based on thresholds
        if (avgLevel >= VERIFIED_THRESHOLD) {
            level = TrustLevel.Verified;
        } else if (avgLevel >= TRUSTED_THRESHOLD) {
            level = TrustLevel.Trusted;
        } else if (avgLevel >= NEUTRAL_THRESHOLD) {
            level = TrustLevel.Neutral;
        } else if (avgLevel >= RISKY_THRESHOLD) {
            level = TrustLevel.Risky;
        } else {
            level = TrustLevel.Unknown;
        }

        // Confidence is based on number of attestations and total weight
        // More attestations + higher weight = higher confidence
        confidence = _computeConfidence(userAttestations.length, totalWeight);

        // Update profile if confidence is sufficient
        if (confidence >= minConfidence) {
            TrustLevel oldLevel = profile.level;
            profile.level = level;
            profile.confidence = confidence;
            profile.lastUpdated = block.timestamp;

            emit TrustClassified(user, level, confidence);

            if (level > oldLevel) {
                emit TrustLevelUpgraded(user, oldLevel, level);
            } else if (level < oldLevel) {
                emit TrustLevelDowngraded(user, oldLevel, level);
            }
        }
    }

    /**
     * @notice Get trust level for a user (view only)
     * @param user User address
     * @return level Current trust level
     * @return confidence Classification confidence
     * @return isStale True if profile needs reclassification
     */
    function getTrustLevel(
        address user
    )
        external
        view
        returns (TrustLevel level, uint256 confidence, bool isStale)
    {
        TrustProfile storage profile = profiles[user];
        if (!profile.exists) {
            return (TrustLevel.Unknown, 0, true);
        }

        level = profile.level;
        confidence = profile.confidence;

        // Consider stale if older than 7 days
        isStale = block.timestamp > profile.lastUpdated + 7 days;
    }

    /**
     * @notice Check if user meets trust requirement
     * @param user User to check
     * @param minLevel Minimum required trust level
     * @return meets True if user meets requirement
     * @return actual User's actual trust level
     */
    function meetsTrustRequirement(
        address user,
        TrustLevel minLevel
    ) external view returns (bool meets, TrustLevel actual) {
        TrustProfile storage profile = profiles[user];
        if (!profile.exists) {
            return (minLevel == TrustLevel.Unknown, TrustLevel.Unknown);
        }

        actual = profile.level;
        meets = uint8(actual) >= uint8(minLevel);
    }

    // ==================== ATTESTATIONS ====================

    /**
     * @notice Attest to a user's trust level (protocol-to-protocol)
     * @param user User to attest
     * @param level Attested trust level
     * @param weight Attestation weight
     * @param reason Reason for attestation
     */
    function attest(
        address user,
        TrustLevel level,
        uint256 weight,
        string calldata reason
    ) external nonReentrant {
        if (!approvedAttesters[msg.sender]) {
            revert UnauthorizedAttester(msg.sender);
        }

        TrustProfile storage profile = profiles[user];
        if (!profile.exists) revert ProfileNotFound(user);
        if (attestations[user].length >= MAX_ATTESTATIONS)
            revert MaxAttestationsReached(user);

        attestations[user].push(
            Attestation({
                attester: msg.sender,
                attestedLevel: level,
                weight: weight,
                timestamp: block.timestamp,
                reason: reason
            })
        );

        // Update action counts based on attestation
        if (level >= TrustLevel.Trusted) {
            profile.positiveActions += weight;
        } else if (level == TrustLevel.Risky) {
            profile.negativeActions += weight;
        }

        emit AttestationReceived(user, msg.sender, level);
    }

    /**
     * @notice Get aggregated attestation score
     * @param user User address
     * @return totalWeight Total attestation weight
     * @return avgLevel Average attested level (scaled by 1e18)
     */
    function getAttestationScore(
        address user
    ) external view returns (uint256 totalWeight, uint256 avgLevel) {
        Attestation[] storage userAttestations = attestations[user];
        if (userAttestations.length == 0) return (0, 0);

        uint256 weightedSum = 0;
        for (uint256 i = 0; i < userAttestations.length; i++) {
            totalWeight += userAttestations[i].weight;
            weightedSum +=
                uint256(userAttestations[i].attestedLevel) *
                userAttestations[i].weight;
        }

        avgLevel = (weightedSum * 1e18) / totalWeight;
    }

    // ==================== ADMIN ====================

    /**
     * @notice Approve an attester protocol
     * @param attester Protocol address
     */
    function approveAttester(address attester) external onlyOwner {
        approvedAttesters[attester] = true;
    }

    /**
     * @notice Revoke attester approval
     * @param attester Protocol address
     */
    function revokeAttester(address attester) external onlyOwner {
        approvedAttesters[attester] = false;
    }

    /**
     * @notice Manually verify a user
     * @param user User to verify
     */
    function verifyUser(address user) external onlyOwner {
        TrustProfile storage profile = profiles[user];
        if (!profile.exists) revert ProfileNotFound(user);
        if (profile.isVerified) revert AlreadyVerified(user);

        profile.isVerified = true;
        profile.level = TrustLevel.Verified;
        profile.confidence = 1e18; // 100% confidence

        emit TrustClassified(user, TrustLevel.Verified, 1e18);
    }

    /**
     * @notice Update minimum confidence threshold
     * @param newMinConfidence New threshold (0-1e18)
     */
    function setMinConfidence(uint256 newMinConfidence) external onlyOwner {
        require(newMinConfidence <= 1e18, "Invalid confidence");
        minConfidence = newMinConfidence;
    }

    // ==================== INTERNAL ====================

    /**
     * @dev Compute confidence from attestation data
     * @param attestationCount Number of attestations
     * @param totalWeight Total attestation weight
     * @return confidence Confidence score (0-1e18)
     */
    function _computeConfidence(
        uint256 attestationCount,
        uint256 totalWeight
    ) internal pure returns (uint256 confidence) {
        // Confidence grows with both count and weight
        // Cap at 1e18 (100%)

        // Count factor: saturates at 10 attestations
        uint256 countFactor = attestationCount >= 10
            ? 1e18
            : (attestationCount * 1e18) / 10;

        // Weight factor: saturates at WEIGHT_THRESHOLD
        uint256 weightFactor = totalWeight >= WEIGHT_THRESHOLD
            ? 1e18
            : (totalWeight * 1e18) / WEIGHT_THRESHOLD;

        // Combined confidence (geometric mean approximation)
        confidence = (countFactor + weightFactor) / 2;
        if (confidence > 1e18) confidence = 1e18;
    }

    // ==================== VIEW ====================

    /**
     * @notice Get user's full profile
     * @param user User address
     * @return Profile data
     */
    function getProfile(
        address user
    ) external view returns (TrustProfile memory) {
        return profiles[user];
    }

    /**
     * @notice Get attestations for a user
     * @param user User address
     * @return Array of attestations
     */
    function getAttestations(
        address user
    ) external view returns (Attestation[] memory) {
        return attestations[user];
    }

    /**
     * @notice Check if address is approved attester
     * @param attester Address to check
     * @return True if approved
     */
    function isApprovedAttester(address attester) external view returns (bool) {
        return approvedAttesters[attester];
    }
}
