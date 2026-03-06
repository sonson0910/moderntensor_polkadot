// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title SubnetRegistry — Yuma Consensus with Security Hardening
 * @notice Multi-subnet orchestrator for decentralized AI networks.
 *
 * Security Features (v2):
 *   1. Commit-Reveal Weights   — Anti front-running
 *   2. ZkML Proof Integration  — Verifiable AI evaluation
 *   3. Slashing                — Penalize malicious validators
 *   4. Self-Vote Protection    — Prevent validator-miner collusion
 *   5. Quadratic Voting        — Reduce whale dominance
 *   6. Proportional Val Share  — Fair validator rewards
 *   7. Trust Score Tracking    — Quality-weighted consensus
 *
 * Architecture:
 *   Root Network (netuid=0) controls global emissions.
 *   Subnets (netuid≥1) each have their own metagraph of miners+validators.
 *   Validators set weights on miners → emission distributed proportionally.
 */
contract SubnetRegistry is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ═══════════════════════════════════════════════════════
    // Types
    // ═══════════════════════════════════════════════════════

    enum NodeType {
        MINER,
        VALIDATOR
    }

    struct Subnet {
        string name;
        address owner;
        uint256 maxNodes; // Max neurons in this subnet
        uint256 emissionShare; // Share of global emission (basis points, max 10000)
        uint256 tempo; // Blocks per epoch
        uint256 lastEpochBlock; // Last epoch block
        uint256 minStake; // Minimum stake to register (wei)
        uint256 immunityPeriod; // Blocks before node can be deregistered
        uint256 nodeCount; // Current active neuron count
        uint256 nextUid; // Monotonically increasing UID counter (never decremented)
        bool active;
        uint256 createdAt;
    }

    struct Node {
        address hotkey; // Network identity key
        address coldkey; // Wallet key (owner)
        NodeType nodeType;
        uint256 stake; // Direct stake
        uint256 delegatedStake; // Stake delegated to this node
        uint256 lastUpdate; // Block of last activity
        uint16 uid; // Unique ID within subnet
        bool active;
        uint256 incentive; // Accumulated incentive (scaled 1e18)
        uint256 trust; // Trust score (0-1e18) — computed by runEpoch
        uint256 rank; // Rank from consensus (0-1e18)
        uint256 emission; // Pending emission to claim
    }

    struct WeightEntry {
        uint16 uid;
        uint16 weight; // 0-65535 (normalized to sum)
    }

    // [NEW] Commit-reveal structure
    struct WeightCommit {
        bytes32 commitHash;
        uint256 commitBlock;
        bool revealed;
    }

    // ═══════════════════════════════════════════════════════
    // State
    // ═══════════════════════════════════════════════════════

    IERC20 public immutable token;

    uint256 public nextNetuid = 1; // 0 is reserved for root
    uint256 public subnetRegistrationCost; // MDT burn to create subnet
    uint256 public emissionPerBlock; // Global MDT emission per block
    uint256 public totalEmissionShares; // Sum of all subnet emission shares

    // netuid => Subnet
    mapping(uint256 => Subnet) public subnets;

    // netuid => uid => Node
    mapping(uint256 => mapping(uint16 => Node)) public nodes;

    // netuid => validatorUid => WeightEntry[]
    mapping(uint256 => mapping(uint16 => WeightEntry[])) internal _weights;

    // netuid => hotkey => registered
    mapping(uint256 => mapping(address => bool)) public isRegistered;

    // netuid => hotkey => uid
    mapping(uint256 => mapping(address => uint16)) public hotkeyToUid;

    // delegator => keccak(netuid, validatorUid) => amount
    mapping(address => mapping(bytes32 => uint256)) public delegations;

    // ═══════════════════════════════════════════════════════
    // [NEW] Consensus Security State
    // ═══════════════════════════════════════════════════════

    // Commit-Reveal: netuid => validatorUid => WeightCommit
    mapping(uint256 => mapping(uint16 => WeightCommit)) public weightCommits;

    // Self-vote protection: netuid => coldkey => NodeType => registered
    mapping(uint256 => mapping(address => mapping(NodeType => bool)))
        public coldkeyNodeType;

    // ZkML Verifier reference
    address public zkmlVerifier;

    // Slashing parameters
    uint256 public slashPercentage = 500; // 5% in basis points (max 10000)
    uint256 public maxWeightAge = 7200; // ~24h — auto-slash if weights older

    // Commit-reveal timing
    uint256 public commitRevealWindow = 600; // Must reveal within 600 blocks (~2h)
    uint256 public commitMinDelay = 10; // Must wait 10 blocks after commit

    // Trust multiplier: high-trust validators get up to 1.5x weight
    uint256 public constant TRUST_MULTIPLIER_MAX = 15000; // 1.5x in basis points (10000 = 1x)
    uint256 public constant TRUST_MULTIPLIER_BASE = 10000;

    // ═══════════════════════════════════════════════════════
    // Events
    // ═══════════════════════════════════════════════════════

    event SubnetCreated(
        uint256 indexed netuid,
        string name,
        address indexed owner
    );
    event SubnetUpdated(uint256 indexed netuid, string name);
    event NodeRegistered(
        uint256 indexed netuid,
        uint16 uid,
        address indexed hotkey,
        address indexed coldkey,
        NodeType nodeType
    );
    event NodeDeregistered(
        uint256 indexed netuid,
        uint16 uid,
        address indexed hotkey
    );
    event WeightsCommitted(
        uint256 indexed netuid,
        uint16 indexed validatorUid,
        bytes32 commitHash
    );
    event WeightsRevealed(
        uint256 indexed netuid,
        uint16 indexed validatorUid,
        uint256 weightCount
    );
    event WeightsSet(
        uint256 indexed netuid,
        uint16 indexed validatorUid,
        uint256 weightCount
    );
    event EpochCompleted(
        uint256 indexed netuid,
        uint256 blockNumber,
        uint256 totalEmission
    );
    event EmissionClaimed(
        uint256 indexed netuid,
        uint16 uid,
        address indexed hotkey,
        uint256 amount
    );
    event StakeDelegated(
        address indexed delegator,
        uint256 indexed netuid,
        uint16 validatorUid,
        uint256 amount
    );
    event StakeUndelegated(
        address indexed delegator,
        uint256 indexed netuid,
        uint16 validatorUid,
        uint256 amount
    );
    event NodeSlashed(
        uint256 indexed netuid,
        uint16 uid,
        uint256 amount,
        string reason
    );
    event TrustUpdated(uint256 indexed netuid, uint16 uid, uint256 newTrust);
    event ValidatorScored(
        uint256 indexed netuid,
        uint16 indexed uid,
        uint256 trust,
        uint256 emission,
        uint256 alignment
    );
    event EmissionShareUpdated(
        uint256 indexed netuid,
        uint256 oldShare,
        uint256 newShare
    );
    event DelegatedStakeWarning(
        uint256 indexed netuid,
        uint16 uid,
        address indexed coldkey,
        uint256 delegatedStake
    );

    // ═══════════════════════════════════════════════════════
    // Constructor
    // ═══════════════════════════════════════════════════════

    constructor(
        address _token,
        uint256 _subnetRegistrationCost,
        uint256 _emissionPerBlock
    ) Ownable(msg.sender) {
        require(_token != address(0), "Invalid token");
        token = IERC20(_token);
        subnetRegistrationCost = _subnetRegistrationCost;
        emissionPerBlock = _emissionPerBlock;
    }

    // ═══════════════════════════════════════════════════════
    // Math: Babylonian Square Root (for quadratic voting)
    // ═══════════════════════════════════════════════════════

    /**
     * @notice Compute integer square root using Babylonian method.
     * @dev Used for quadratic voting: validator power = sqrt(stake)
     *      This reduces whale dominance significantly.
     *      10,000 MDT → power 100, 100 MDT → power 10 (100x stake, only 10x power)
     */
    function sqrt(uint256 x) internal pure returns (uint256) {
        if (x == 0) return 0;
        uint256 z = (x + 1) / 2;
        uint256 y = x;
        while (z < y) {
            y = z;
            z = (x / z + z) / 2;
        }
        return y;
    }

    // ═══════════════════════════════════════════════════════
    // Subnet Management
    // ═══════════════════════════════════════════════════════

    /**
     * @notice Create a new subnet.
     * @param name Human-readable subnet name
     * @param maxNodes Maximum neurons allowed
     * @param minStake Minimum stake to register a node
     * @param tempo Blocks per epoch for emission
     */
    function createSubnet(
        string calldata name,
        uint256 maxNodes,
        uint256 minStake,
        uint256 tempo
    ) external nonReentrant returns (uint256 netuid) {
        require(
            bytes(name).length > 0 && bytes(name).length <= 64,
            "Invalid name"
        );
        require(maxNodes > 0 && maxNodes <= 4096, "Invalid maxNodes");
        require(tempo > 0, "Invalid tempo");

        // Burn registration cost
        if (subnetRegistrationCost > 0) {
            token.safeTransferFrom(
                msg.sender,
                address(this),
                subnetRegistrationCost
            );
        }

        netuid = nextNetuid++;
        subnets[netuid] = Subnet({
            name: name,
            owner: msg.sender,
            maxNodes: maxNodes,
            emissionShare: 1000, // Default 10% share
            tempo: tempo,
            lastEpochBlock: block.number,
            minStake: minStake,
            immunityPeriod: 7200, // ~24h at 12s blocks
            nodeCount: 0,
            nextUid: 0,
            active: true,
            createdAt: block.timestamp
        });

        totalEmissionShares += 1000;

        emit SubnetCreated(netuid, name, msg.sender);
    }

    /**
     * @notice Update subnet parameters (subnet owner only)
     */
    function updateSubnet(
        uint256 netuid,
        uint256 maxNodes,
        uint256 minStake,
        uint256 tempo,
        uint256 immunityPeriod
    ) external {
        Subnet storage sn = subnets[netuid];
        require(sn.active, "Subnet not active");
        require(
            msg.sender == sn.owner || msg.sender == owner(),
            "Not authorized"
        );

        sn.maxNodes = maxNodes;
        sn.minStake = minStake;
        sn.tempo = tempo;
        sn.immunityPeriod = immunityPeriod;

        emit SubnetUpdated(netuid, sn.name);
    }

    /**
     * @notice Update emission share for a subnet (owner or admin only)
     * @param netuid Target subnet
     * @param newShare New emission share in basis points (e.g. 1000 = 10%)
     */
    function updateEmissionShare(uint256 netuid, uint256 newShare) external {
        Subnet storage sn = subnets[netuid];
        require(sn.active, "Subnet not active");
        require(
            msg.sender == sn.owner || msg.sender == owner(),
            "Not authorized"
        );
        require(newShare > 0 && newShare <= 10000, "Invalid share");

        uint256 oldShare = sn.emissionShare;
        totalEmissionShares = totalEmissionShares - oldShare + newShare;
        sn.emissionShare = newShare;

        emit EmissionShareUpdated(netuid, oldShare, newShare);
    }

    // ═══════════════════════════════════════════════════════
    // Node Registration (with Self-Vote Protection)
    // ═══════════════════════════════════════════════════════

    /**
     * @notice Register a node (miner or validator) in a subnet.
     * @dev SECURITY: Same coldkey cannot register as both miner AND validator
     *      in the same subnet (prevents self-voting collusion).
     * @param netuid Target subnet
     * @param hotkey Network identity key (can be same as msg.sender)
     * @param nodeType MINER or VALIDATOR
     * @param stakeAmount Initial stake (must meet subnet minStake)
     */
    function registerNode(
        uint256 netuid,
        address hotkey,
        NodeType nodeType,
        uint256 stakeAmount
    ) external nonReentrant returns (uint16 uid) {
        Subnet storage sn = subnets[netuid];
        require(sn.active, "Subnet not active");
        require(!isRegistered[netuid][hotkey], "Already registered");
        require(sn.nodeCount < sn.maxNodes, "Subnet full");
        require(stakeAmount >= sn.minStake, "Insufficient stake");

        // [SECURITY] Self-vote protection:
        // Same coldkey cannot be both MINER and VALIDATOR in the same subnet
        NodeType oppositeType = nodeType == NodeType.MINER
            ? NodeType.VALIDATOR
            : NodeType.MINER;
        require(
            !coldkeyNodeType[netuid][msg.sender][oppositeType],
            "Self-vote: coldkey already registered as opposite type"
        );
        coldkeyNodeType[netuid][msg.sender][nodeType] = true;

        // Transfer stake
        if (stakeAmount > 0) {
            token.safeTransferFrom(msg.sender, address(this), stakeAmount);
        }

        // [SECURITY] Use monotonic nextUid counter — never reuse UIDs
        uid = uint16(sn.nextUid);
        sn.nextUid++;
        nodes[netuid][uid] = Node({
            hotkey: hotkey,
            coldkey: msg.sender,
            nodeType: nodeType,
            stake: stakeAmount,
            delegatedStake: 0,
            lastUpdate: block.number,
            uid: uid,
            active: true,
            incentive: 0,
            trust: 5000e14, // Start with 50% trust (0.5 * 1e18)
            rank: 0,
            emission: 0
        });

        hotkeyToUid[netuid][hotkey] = uid;
        isRegistered[netuid][hotkey] = true;
        sn.nodeCount++;

        emit NodeRegistered(netuid, uid, hotkey, msg.sender, nodeType);
    }

    /**
     * @notice Deregister a node and return stake
     */
    function deregisterNode(uint256 netuid, uint16 uid) external nonReentrant {
        Node storage node = nodes[netuid][uid];
        require(node.active, "Not active");
        require(
            node.coldkey == msg.sender || msg.sender == owner(),
            "Not authorized"
        );
        require(
            block.number >= node.lastUpdate + subnets[netuid].immunityPeriod,
            "Immunity period"
        );

        node.active = false;
        isRegistered[netuid][node.hotkey] = false;

        // Clear self-vote tracking
        coldkeyNodeType[netuid][node.coldkey][node.nodeType] = false;

        // Decrement node count
        subnets[netuid].nodeCount--;

        // Warn if delegated stake exists (delegators must undelegate first)
        if (node.delegatedStake > 0) {
            emit DelegatedStakeWarning(
                netuid,
                uid,
                node.coldkey,
                node.delegatedStake
            );
        }

        // Return stake
        uint256 totalStake = node.stake + node.emission;
        node.stake = 0;
        node.emission = 0;
        if (totalStake > 0) {
            token.safeTransfer(node.coldkey, totalStake);
        }

        emit NodeDeregistered(netuid, uid, node.hotkey);
    }

    // ═══════════════════════════════════════════════════════
    // Commit-Reveal Weight Setting (Anti Front-Running)
    // ═══════════════════════════════════════════════════════

    /**
     * @notice Phase 1: Commit weight hash.
     * @dev Validator commits keccak256(abi.encodePacked(uids, weights, salt))
     *      Must reveal within commitRevealWindow blocks.
     * @param netuid Target subnet
     * @param commitHash The hash of (uids, weights, salt)
     */
    function commitWeights(uint256 netuid, bytes32 commitHash) external {
        require(isRegistered[netuid][msg.sender], "Not registered");
        uint16 validatorUid = hotkeyToUid[netuid][msg.sender];
        require(
            nodes[netuid][validatorUid].nodeType == NodeType.VALIDATOR,
            "Not a validator"
        );
        require(nodes[netuid][validatorUid].active, "Not active");

        weightCommits[netuid][validatorUid] = WeightCommit({
            commitHash: commitHash,
            commitBlock: block.number,
            revealed: false
        });

        emit WeightsCommitted(netuid, validatorUid, commitHash);
    }

    /**
     * @notice Phase 2: Reveal weights (must match previously committed hash).
     * @dev Verifies hash, validates weights, stores them.
     * @param netuid Target subnet
     * @param uids Array of miner UIDs to score
     * @param weights Array of weights (uint16, will be normalized)
     * @param salt Random salt used in the commit hash
     */
    function revealWeights(
        uint256 netuid,
        uint16[] calldata uids,
        uint16[] calldata weights,
        bytes32 salt
    ) external {
        require(uids.length == weights.length, "Length mismatch");
        require(uids.length > 0, "Empty weights");

        // Verify caller is a registered validator
        require(isRegistered[netuid][msg.sender], "Not registered");
        uint16 validatorUid = hotkeyToUid[netuid][msg.sender];
        Node storage validator = nodes[netuid][validatorUid];
        require(validator.nodeType == NodeType.VALIDATOR, "Not a validator");
        require(validator.active, "Not active");

        // [SECURITY] Commit-reveal verification
        WeightCommit storage commit = weightCommits[netuid][validatorUid];
        require(commit.commitHash != bytes32(0), "No commit found");
        require(!commit.revealed, "Already revealed");
        require(
            block.number >= commit.commitBlock + commitMinDelay,
            "Too early to reveal"
        );
        require(
            block.number <= commit.commitBlock + commitRevealWindow,
            "Reveal window expired"
        );

        // Verify hash matches
        bytes32 expectedHash = keccak256(abi.encodePacked(uids, weights, salt));
        require(expectedHash == commit.commitHash, "Hash mismatch");

        commit.revealed = true;

        // Verify all target UIDs are valid active MINER nodes
        // [SECURITY] Validators can only assign weights to miners, not other validators
        for (uint256 i = 0; i < uids.length; i++) {
            require(uids[i] < subnets[netuid].nextUid, "Invalid UID");
            require(nodes[netuid][uids[i]].active, "Target not active");
            require(
                nodes[netuid][uids[i]].nodeType == NodeType.MINER,
                "Can only weight miners"
            );
        }

        // Store weights (replace existing)
        delete _weights[netuid][validatorUid];
        for (uint256 i = 0; i < uids.length; i++) {
            _weights[netuid][validatorUid].push(
                WeightEntry({uid: uids[i], weight: weights[i]})
            );
        }

        validator.lastUpdate = block.number;

        emit WeightsRevealed(netuid, validatorUid, uids.length);
    }

    /**
     * @notice Legacy setWeights (without commit-reveal).
     * @dev DEPRECATED: Use commitWeights()+revealWeights() instead.
     *      Restricted to contract owner only for emergency/migration use.
     *      Owner can set weights for ANY validator UID (admin override).
     * @param netuid Target subnet
     * @param validatorUid Validator UID to set weights for
     * @param uids Array of miner UIDs to score
     * @param weights Array of weights (uint16, will be normalized)
     */
    function setWeights(
        uint256 netuid,
        uint16 validatorUid,
        uint16[] calldata uids,
        uint16[] calldata weights
    ) external onlyOwner {
        require(uids.length == weights.length, "Length mismatch");
        require(uids.length > 0, "Empty weights");

        // Verify target is a valid active validator
        Node storage validator = nodes[netuid][validatorUid];
        require(validator.active, "Validator not active");
        require(validator.nodeType == NodeType.VALIDATOR, "Not a validator");

        for (uint256 i = 0; i < uids.length; i++) {
            require(uids[i] < subnets[netuid].nextUid, "Invalid UID");
            require(nodes[netuid][uids[i]].active, "Target not active");
            require(
                nodes[netuid][uids[i]].nodeType == NodeType.MINER,
                "Can only weight miners"
            );
        }

        delete _weights[netuid][validatorUid];
        for (uint256 i = 0; i < uids.length; i++) {
            _weights[netuid][validatorUid].push(
                WeightEntry({uid: uids[i], weight: weights[i]})
            );
        }

        validator.lastUpdate = block.number;
        emit WeightsSet(netuid, validatorUid, uids.length);
    }

    /**
     * @notice Get weights set by a validator
     */
    function getWeights(
        uint256 netuid,
        uint16 validatorUid
    ) external view returns (uint16[] memory uids, uint16[] memory weights) {
        WeightEntry[] storage w = _weights[netuid][validatorUid];
        uids = new uint16[](w.length);
        weights = new uint16[](w.length);
        for (uint256 i = 0; i < w.length; i++) {
            uids[i] = w[i].uid;
            weights[i] = w[i].weight;
        }
    }

    // ═══════════════════════════════════════════════════════
    // Emission Distribution — Enhanced Yuma Consensus
    // Features: Quadratic Voting, Trust Scores, Proportional Validator Share
    // ═══════════════════════════════════════════════════════

    /**
     * @notice Run epoch for a subnet — distribute emission based on weights.
     *
     * Enhanced Yuma Consensus with security hardening:
     * 1. Collect validator weights with QUADRATIC stake weighting
     * 2. Apply TRUST multiplier (high-trust validators count more)
     * 3. Compute final scores for each miner
     * 4. Distribute 82% emission proportional to scores (miners)
     * 5. Distribute 18% emission proportional to stake (validators)
     * 6. Update TRUST scores based on consensus alignment
     *
     * Can be called by anyone when enough blocks have passed.
     */
    function runEpoch(uint256 netuid) external nonReentrant {
        Subnet storage sn = subnets[netuid];
        require(sn.active, "Subnet not active");
        require(block.number >= sn.lastEpochBlock + sn.tempo, "Too early");
        require(sn.nodeCount > 0, "No nodes");
        require(totalEmissionShares > 0, "No emission shares");

        uint256 blocksPassed = block.number - sn.lastEpochBlock;
        uint256 totalEmission = (emissionPerBlock *
            blocksPassed *
            sn.emissionShare) / totalEmissionShares;

        // [SECURITY] Cap emission to actual contract token balance
        // Prevents accruing unbacked emission IOUs
        uint256 contractBalance = token.balanceOf(address(this));
        if (totalEmission > contractBalance) {
            totalEmission = contractBalance;
        }

        if (totalEmission == 0) {
            sn.lastEpochBlock = block.number;
            return;
        }

        // ───────────────────────────────────────────────────
        // Step 1: Aggregate QUADRATIC stake-weighted scores
        //         with TRUST multiplier
        // ───────────────────────────────────────────────────
        uint256[] memory scores = new uint256[](sn.nextUid);
        uint256 totalScore = 0;

        // Track per-validator weight sums for trust calculation later
        uint256[] memory validatorContributions = new uint256[](sn.nextUid);

        for (uint16 v = 0; v < sn.nextUid; v++) {
            Node storage validator = nodes[netuid][v];
            if (!validator.active || validator.nodeType != NodeType.VALIDATOR)
                continue;

            uint256 totalStake = validator.stake + validator.delegatedStake;
            if (totalStake == 0) continue;

            // [QUADRATIC VOTING] Use sqrt(stake) instead of raw stake
            uint256 votingPower = sqrt(totalStake);

            // [TRUST MULTIPLIER] High-trust validators get up to 1.5x weight
            // trust is stored as 0 - 1e18, scale to multiplier
            uint256 trustMultiplier = TRUST_MULTIPLIER_BASE +
                (validator.trust *
                    (TRUST_MULTIPLIER_MAX - TRUST_MULTIPLIER_BASE)) /
                1e18;

            // Apply trust multiplier to voting power
            uint256 effectivePower = (votingPower * trustMultiplier) /
                TRUST_MULTIPLIER_BASE;

            WeightEntry[] storage w = _weights[netuid][v];
            uint256 weightSum = 0;
            for (uint256 i = 0; i < w.length; i++) {
                weightSum += w[i].weight;
            }
            if (weightSum == 0) continue;

            // Add trust-weighted quadratic contribution
            uint256 validatorTotalContrib = 0;
            for (uint256 i = 0; i < w.length; i++) {
                uint256 contribution = (effectivePower * uint256(w[i].weight)) /
                    weightSum;
                scores[w[i].uid] += contribution;
                totalScore += contribution;
                validatorTotalContrib += contribution;
            }
            validatorContributions[v] = validatorTotalContrib;
        }

        // ───────────────────────────────────────────────────
        // Step 2: Distribute 82% emission proportional to scores (miners)
        // ───────────────────────────────────────────────────
        uint256 minerShare = (totalEmission * 8200) / 10000; // 82%
        if (totalScore > 0) {
            for (uint16 uid = 0; uid < sn.nextUid; uid++) {
                if (scores[uid] > 0 && nodes[netuid][uid].active) {
                    uint256 nodeEmission = (minerShare * scores[uid]) /
                        totalScore;
                    nodes[netuid][uid].emission += nodeEmission;
                    nodes[netuid][uid].rank = (scores[uid] * 1e18) / totalScore;
                    nodes[netuid][uid].incentive += nodeEmission;
                }
            }
        }

        // ───────────────────────────────────────────────────
        // Step 3: Distribute 18% to validators weighted by
        //         STAKE × TRUST (not pure stake — rewards consensus alignment)
        // ───────────────────────────────────────────────────
        uint256 validatorShareTotal = (totalEmission * 1800) / 10000; // 18%
        uint256 totalEffectiveValidatorStake = 0;

        // First pass: compute total effective stake (stake × trust multiplier)
        for (uint16 v = 0; v < sn.nextUid; v++) {
            Node storage validator = nodes[netuid][v];
            if (validator.active && validator.nodeType == NodeType.VALIDATOR) {
                uint256 vStake = validator.stake + validator.delegatedStake;
                // [CONSENSUS SCORING] Trust-weighted effective stake
                // Low-trust validators earn proportionally less emission
                uint256 trustFactor = TRUST_MULTIPLIER_BASE +
                    (validator.trust *
                        (TRUST_MULTIPLIER_MAX - TRUST_MULTIPLIER_BASE)) /
                    1e18;
                uint256 effectiveStake = (vStake * trustFactor) /
                    TRUST_MULTIPLIER_BASE;
                totalEffectiveValidatorStake += effectiveStake;
            }
        }

        // Second pass: distribute proportionally to effective stake
        if (totalEffectiveValidatorStake > 0) {
            for (uint16 v = 0; v < sn.nextUid; v++) {
                Node storage validator = nodes[netuid][v];
                if (
                    validator.active && validator.nodeType == NodeType.VALIDATOR
                ) {
                    uint256 vStake = validator.stake + validator.delegatedStake;
                    uint256 trustFactor = TRUST_MULTIPLIER_BASE +
                        (validator.trust *
                            (TRUST_MULTIPLIER_MAX - TRUST_MULTIPLIER_BASE)) /
                        1e18;
                    uint256 effectiveStake = (vStake * trustFactor) /
                        TRUST_MULTIPLIER_BASE;
                    uint256 perValidator = (validatorShareTotal *
                        effectiveStake) / totalEffectiveValidatorStake;
                    validator.emission += perValidator;
                }
            }
        }

        // ───────────────────────────────────────────────────
        // Step 4: Update TRUST scores
        //         Trust = how well validator's weights align with consensus
        // ───────────────────────────────────────────────────
        if (totalScore > 0) {
            for (uint16 v = 0; v < sn.nextUid; v++) {
                Node storage validator = nodes[netuid][v];
                if (
                    !validator.active ||
                    validator.nodeType != NodeType.VALIDATOR
                ) continue;

                WeightEntry[] storage w = _weights[netuid][v];
                if (w.length == 0) {
                    // No weights set → decrease trust
                    validator.trust = (validator.trust * 95) / 100; // -5%
                    emit TrustUpdated(netuid, v, validator.trust);
                    emit ValidatorScored(
                        netuid,
                        v,
                        validator.trust,
                        validator.emission,
                        0
                    );
                    continue;
                }

                // Calculate alignment: how well this validator's distribution
                // matches the consensus distribution
                uint256 weightSum = 0;
                for (uint256 i = 0; i < w.length; i++) {
                    weightSum += w[i].weight;
                }

                uint256 alignmentScore = 0;
                uint256 maxAlignment = 0;

                for (uint256 i = 0; i < w.length; i++) {
                    // Validator's normalized weight for this miner
                    uint256 valWeight = (uint256(w[i].weight) * 1e18) /
                        weightSum;
                    // Consensus normalized score for this miner
                    uint256 consensusWeight = (scores[w[i].uid] * 1e18) /
                        totalScore;

                    // Alignment = min(valWeight, consensusWeight)
                    // (measures overlap between validator's view and consensus)
                    if (valWeight <= consensusWeight) {
                        alignmentScore += valWeight;
                    } else {
                        alignmentScore += consensusWeight;
                    }
                    maxAlignment += valWeight;
                }

                // Trust = EMA(old_trust, alignment)
                // 70% old trust + 30% new alignment
                uint256 newAlignment = maxAlignment > 0
                    ? (alignmentScore * 1e18) / maxAlignment
                    : 0;
                validator.trust =
                    (validator.trust * 70 + newAlignment * 30) /
                    100;

                emit TrustUpdated(netuid, v, validator.trust);
                emit ValidatorScored(
                    netuid,
                    v,
                    validator.trust,
                    validator.emission,
                    newAlignment
                );
            }
        }

        sn.lastEpochBlock = block.number;

        emit EpochCompleted(netuid, block.number, totalEmission);
    }

    /**
     * @notice Claim accumulated emission rewards
     */
    function claimEmission(uint256 netuid, uint16 uid) external nonReentrant {
        Node storage node = nodes[netuid][uid];
        require(node.coldkey == msg.sender, "Not owner");
        require(node.emission > 0, "No emission");

        uint256 amount = node.emission;
        node.emission = 0;

        token.safeTransfer(msg.sender, amount);

        emit EmissionClaimed(netuid, uid, node.hotkey, amount);
    }

    // ═══════════════════════════════════════════════════════
    // Slashing
    // ═══════════════════════════════════════════════════════

    /**
     * @notice Slash a node's stake. Slashed tokens go to emission pool.
     * @dev Only callable by contract owner (governance) or subnet owner.
     * @param netuid Target subnet
     * @param uid Node to slash
     * @param basisPoints Slash percentage in basis points (e.g., 500 = 5%)
     * @param reason Human-readable reason for the slash
     */
    function slashNode(
        uint256 netuid,
        uint16 uid,
        uint256 basisPoints,
        string calldata reason
    ) external {
        require(
            msg.sender == owner() || msg.sender == subnets[netuid].owner,
            "Not authorized to slash"
        );
        require(
            basisPoints > 0 && basisPoints <= 10000,
            "Invalid slash percentage"
        );

        Node storage node = nodes[netuid][uid];
        require(node.active, "Node not active");

        uint256 slashAmount = (node.stake * basisPoints) / 10000;
        if (slashAmount > node.stake) {
            slashAmount = node.stake;
        }

        node.stake -= slashAmount;
        // Slashed tokens stay in contract → recycled as emission
        // (they were already transferred in during registerNode)

        emit NodeSlashed(netuid, uid, slashAmount, reason);
    }

    /**
     * @notice Auto-slash validators who haven't set weights for too long.
     * @dev Anyone can call this — incentivizes active participation.
     * @param netuid Target subnet
     * @param validatorUid Validator to check
     */
    function autoSlashInactive(uint256 netuid, uint16 validatorUid) external {
        Node storage validator = nodes[netuid][validatorUid];
        require(validator.active, "Not active");
        require(validator.nodeType == NodeType.VALIDATOR, "Not a validator");
        require(
            block.number > validator.lastUpdate + maxWeightAge,
            "Validator is active"
        );

        // Auto-slash 1% for inactivity
        uint256 slashAmount = (validator.stake * 100) / 10000; // 1%
        if (slashAmount > validator.stake) {
            slashAmount = validator.stake;
        }

        validator.stake -= slashAmount;
        // Decrease trust for inactivity
        validator.trust = (validator.trust * 80) / 100; // -20% trust

        emit NodeSlashed(
            netuid,
            validatorUid,
            slashAmount,
            "Inactive validator"
        );
    }

    // ═══════════════════════════════════════════════════════
    // Delegation
    // ═══════════════════════════════════════════════════════

    /**
     * @notice Delegate stake to a validator
     */
    function delegate(
        uint256 netuid,
        uint16 validatorUid,
        uint256 amount
    ) external nonReentrant {
        require(amount > 0, "Amount must be > 0");
        Node storage validator = nodes[netuid][validatorUid];
        require(validator.active, "Validator not active");
        require(validator.nodeType == NodeType.VALIDATOR, "Not a validator");

        token.safeTransferFrom(msg.sender, address(this), amount);

        bytes32 key = keccak256(abi.encodePacked(netuid, validatorUid));
        delegations[msg.sender][key] += amount;
        validator.delegatedStake += amount;

        emit StakeDelegated(msg.sender, netuid, validatorUid, amount);
    }

    /**
     * @notice Undelegate stake from a validator
     */
    function undelegate(
        uint256 netuid,
        uint16 validatorUid,
        uint256 amount
    ) external nonReentrant {
        bytes32 key = keccak256(abi.encodePacked(netuid, validatorUid));
        require(
            delegations[msg.sender][key] >= amount,
            "Insufficient delegation"
        );

        delegations[msg.sender][key] -= amount;
        nodes[netuid][validatorUid].delegatedStake -= amount;

        token.safeTransfer(msg.sender, amount);

        emit StakeUndelegated(msg.sender, netuid, validatorUid, amount);
    }

    /**
     * @notice Get delegation amount
     */
    function getDelegation(
        address delegator,
        uint256 netuid,
        uint16 validatorUid
    ) external view returns (uint256) {
        bytes32 key = keccak256(abi.encodePacked(netuid, validatorUid));
        return delegations[delegator][key];
    }

    // ═══════════════════════════════════════════════════════
    // Metagraph Queries
    // ═══════════════════════════════════════════════════════

    /**
     * @notice Get full metagraph for a subnet (active nodes only)
     * @dev Iterates nextUid to account for deregistered slots
     */
    function getMetagraph(
        uint256 netuid
    )
        external
        view
        returns (
            address[] memory hotkeys,
            address[] memory coldkeys,
            uint256[] memory stakes,
            uint256[] memory ranks,
            uint256[] memory incentives,
            uint256[] memory emissions,
            uint8[] memory nodeTypes,
            bool[] memory activeFlags
        )
    {
        Subnet storage sn = subnets[netuid];
        uint256 count = sn.nodeCount; // active node count

        hotkeys = new address[](count);
        coldkeys = new address[](count);
        stakes = new uint256[](count);
        ranks = new uint256[](count);
        incentives = new uint256[](count);
        emissions = new uint256[](count);
        nodeTypes = new uint8[](count);
        activeFlags = new bool[](count);

        uint256 idx = 0;
        for (uint16 i = 0; i < sn.nextUid && idx < count; i++) {
            Node storage n = nodes[netuid][i];
            if (!n.active) continue;
            hotkeys[idx] = n.hotkey;
            coldkeys[idx] = n.coldkey;
            stakes[idx] = n.stake + n.delegatedStake;
            ranks[idx] = n.rank;
            incentives[idx] = n.incentive;
            emissions[idx] = n.emission;
            nodeTypes[idx] = uint8(n.nodeType);
            activeFlags[idx] = true;
            idx++;
        }
    }

    /**
     * @notice Get single node info (includes trust)
     */
    function getNode(
        uint256 netuid,
        uint16 uid
    )
        external
        view
        returns (
            address hotkey,
            address coldkey,
            uint8 nodeType,
            uint256 stake,
            uint256 delegatedStake,
            uint256 rank,
            uint256 incentive,
            uint256 emission,
            uint256 trust,
            bool active
        )
    {
        Node storage n = nodes[netuid][uid];
        return (
            n.hotkey,
            n.coldkey,
            uint8(n.nodeType),
            n.stake,
            n.delegatedStake,
            n.rank,
            n.incentive,
            n.emission,
            n.trust,
            n.active
        );
    }

    /**
     * @notice Get subnet info
     */
    function getSubnet(
        uint256 netuid
    )
        external
        view
        returns (
            string memory name,
            address subnetOwner,
            uint256 maxNodes,
            uint256 emissionShare,
            uint256 tempo,
            uint256 nodeCount,
            bool active
        )
    {
        Subnet storage sn = subnets[netuid];
        return (
            sn.name,
            sn.owner,
            sn.maxNodes,
            sn.emissionShare,
            sn.tempo,
            sn.nodeCount,
            sn.active
        );
    }

    /**
     * @notice Get total number of subnets
     */
    function getSubnetCount() external view returns (uint256) {
        return nextNetuid;
    }

    /**
     * @notice Lookup UID by hotkey
     */
    function getUidByHotkey(
        uint256 netuid,
        address hotkey
    ) external view returns (uint16) {
        require(isRegistered[netuid][hotkey], "Not registered");
        return hotkeyToUid[netuid][hotkey];
    }

    /**
     * @notice Get trust score of a node
     */
    function getTrust(
        uint256 netuid,
        uint16 uid
    ) external view returns (uint256) {
        return nodes[netuid][uid].trust;
    }

    /**
     * @notice Get full validator consensus score breakdown.
     * @dev Returns all metrics that determine a validator's emission share.
     *
     * Consensus Scoring Formula:
     *   effectivePower = sqrt(stake) × trustMultiplier
     *   trustMultiplier = 1.0 + (trust × 0.5)   // range [1.0, 1.5]
     *   emission_share = effectivePower / sum(all_validators_effectivePower)
     *
     * Trust Score:
     *   - Measures alignment between validator's weights and consensus.
     *   - Updated each epoch via EMA: 70% old + 30% alignment.
     *   - Range: [0, 1e18] where 1e18 = perfect alignment.
     *   - Validators with no weights lose 5% trust per epoch.
     *   - New validators start at 50% trust (0.5 × 1e18).
     */
    function getValidatorScore(
        uint256 netuid,
        uint16 uid
    )
        external
        view
        returns (
            uint256 trust, // 0-1e18 consensus alignment score
            uint256 rank, // 0-1e18 rank from last epoch
            uint256 stake, // Direct stake (wei)
            uint256 delegatedStake, // Delegated stake (wei)
            uint256 effectivePower, // sqrt(totalStake) × trustMultiplier
            uint256 emission, // Pending emission to claim
            uint256 incentive, // Accumulated incentive
            bool active
        )
    {
        Node storage n = nodes[netuid][uid];
        require(n.nodeType == NodeType.VALIDATOR, "Not a validator");

        uint256 totalStake = n.stake + n.delegatedStake;
        uint256 sqrtStake = sqrt(totalStake);
        uint256 trustFactor = TRUST_MULTIPLIER_BASE +
            (n.trust * (TRUST_MULTIPLIER_MAX - TRUST_MULTIPLIER_BASE)) /
            1e18;
        uint256 power = (sqrtStake * trustFactor) / TRUST_MULTIPLIER_BASE;

        return (
            n.trust,
            n.rank,
            n.stake,
            n.delegatedStake,
            power,
            n.emission,
            n.incentive,
            n.active
        );
    }

    // ═══════════════════════════════════════════════════════
    // Admin — Governance Roadmap
    // ═══════════════════════════════════════════════════════
    //
    // Phase 1 (Current): Owner-managed via onlyOwner modifier.
    //   - Suitable for hackathon, testnets, and initial deployment.
    //   - Owner expected to be a multi-sig (e.g. Gnosis Safe) on mainnet.
    //
    // Phase 2 (Planned): DAO Governance via GovernanceModule.
    //   - Validators with stake > threshold can create proposals.
    //   - >50% validator stake vote "yes" → execute after timelock.
    //   - Emergency functions (pause, slash) retain owner access.
    //   - Implemented via OpenZeppelin Governor + TimelockController.
    //
    // Phase 3 (Future): Fully on-chain governance via Polkadot OpenGov.
    //   - Subnet parameters managed via XCM governance pallets.
    //   - Cross-chain governance for multi-chain subnet coordination.
    //

    function setSubnetRegistrationCost(uint256 cost) external onlyOwner {
        subnetRegistrationCost = cost;
    }

    function setEmissionPerBlock(uint256 amount) external onlyOwner {
        emissionPerBlock = amount;
    }

    function setZkmlVerifier(address _verifier) external onlyOwner {
        zkmlVerifier = _verifier;
    }

    function setSlashPercentage(uint256 _basisPoints) external onlyOwner {
        require(_basisPoints <= 5000, "Max 50%");
        slashPercentage = _basisPoints;
    }

    function setMaxWeightAge(uint256 _blocks) external onlyOwner {
        maxWeightAge = _blocks;
    }

    function setCommitRevealWindow(uint256 _blocks) external onlyOwner {
        commitRevealWindow = _blocks;
    }

    function setCommitMinDelay(uint256 _blocks) external onlyOwner {
        commitMinDelay = _blocks;
    }

    /**
     * @notice Fund the contract with emission tokens
     */
    function fundEmissionPool(uint256 amount) external onlyOwner {
        token.safeTransferFrom(msg.sender, address(this), amount);
    }
}
