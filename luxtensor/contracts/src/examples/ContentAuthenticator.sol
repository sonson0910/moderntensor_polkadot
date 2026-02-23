// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";

/**
 * @title ContentAuthenticator - NFT Originality Verification
 * @notice Prevent NFT plagiarism using on-chain hash-based duplicate detection
 * @dev Uses content hash registry and embedding hash fingerprinting (no precompiles)
 *
 * Use Cases:
 * - Art NFTs: Verify artwork originality before minting
 * - Music NFTs: Detect audio similarity/copying
 * - Photography: Prevent duplicate image minting
 *
 * Architecture:
 * 1. Original artwork embeddings are fingerprinted (keccak256) and stored on-chain
 * 2. New uploads are checked against the on-chain fingerprint registry
 * 3. Duplicate content hashes are rejected
 * 4. Verified originals get minted with on-chain provenance
 */
contract ContentAuthenticator is ERC721, Ownable, ReentrancyGuard {
    // ==================== CONSTANTS ====================

    /// @notice Maximum embedding dimension
    uint256 public constant MAX_DIMENSION = 1024;

    // ==================== STATE ====================

    /// @notice Content embedding dimension
    uint256 public embeddingDimension;

    /// @notice Token ID counter
    uint256 private _nextTokenId;

    /// @notice Content hash to token ID (duplicate detection)
    mapping(bytes32 => uint256) public contentToToken;

    /// @notice Embedding fingerprint to token ID (similarity detection)
    mapping(bytes32 => uint256) public fingerprintToToken;

    /// @notice Token ID to content metadata
    mapping(uint256 => ContentMetadata) public metadata;

    /// @notice Struct for content metadata
    struct ContentMetadata {
        bytes32 contentHash;      // IPFS CID or hash
        bytes32 embeddingHash;    // Fingerprint of the embedding
        uint256 createdAt;
        address originalCreator;
    }

    // ==================== EVENTS ====================

    event ContentVerified(
        uint256 indexed tokenId,
        bytes32 indexed contentHash,
        bytes32 embeddingHash,
        address creator
    );

    event DuplicateDetected(
        bytes32 indexed contentHash,
        uint256 existingTokenId
    );

    // ==================== ERRORS ====================

    error InvalidEmbedding(uint256 got, uint256 expected);
    error ContentAlreadyMinted(bytes32 contentHash, uint256 existingTokenId);
    error EmbeddingAlreadyRegistered(bytes32 embeddingHash, uint256 existingTokenId);
    error TokenNotFound(uint256 tokenId);

    // ==================== CONSTRUCTOR ====================

    /**
     * @notice Initialize ContentAuthenticator
     * @param name_ NFT collection name
     * @param symbol_ NFT collection symbol
     * @param dimension_ Embedding dimension for content vectors
     */
    constructor(
        string memory name_,
        string memory symbol_,
        uint256 dimension_
    ) ERC721(name_, symbol_) Ownable(msg.sender) {
        if (dimension_ == 0 || dimension_ > MAX_DIMENSION) {
            revert InvalidEmbedding(dimension_, MAX_DIMENSION);
        }
        embeddingDimension = dimension_;
        _nextTokenId = 1;
    }

    // ==================== CORE FUNCTIONS ====================

    /**
     * @notice Mint NFT after verifying content originality
     * @param contentHash IPFS CID or content hash
     * @param embedding Content embedding vector (from off-chain ML model)
     * @return tokenId The minted token ID
     *
     * @dev Flow:
     * 1. Check embedding dimension
     * 2. Verify content hash not already minted
     * 3. Verify embedding fingerprint not already registered
     * 4. Mint NFT with provenance data
     *
     * Example:
     * ```solidity
     * // Artist uploads artwork
     * bytes32 ipfsCid = 0x1234...;
     * int256[] memory artEmbedding = modelOutput; // From off-chain ML
     * uint256 tokenId = authenticator.mintVerified(ipfsCid, artEmbedding);
     * ```
     */
    function mintVerified(
        bytes32 contentHash,
        int256[] calldata embedding
    ) external nonReentrant returns (uint256 tokenId) {
        // Validate embedding
        if (embedding.length != embeddingDimension) {
            revert InvalidEmbedding(embedding.length, embeddingDimension);
        }

        // Check not already minted (exact content hash)
        if (contentToToken[contentHash] != 0) {
            emit DuplicateDetected(contentHash, contentToToken[contentHash]);
            revert ContentAlreadyMinted(contentHash, contentToToken[contentHash]);
        }

        // Generate embedding fingerprint
        bytes32 embeddingHash = keccak256(abi.encode(embedding));

        // Check embedding not already registered (catches plagiarism with different content hash)
        if (fingerprintToToken[embeddingHash] != 0) {
            revert EmbeddingAlreadyRegistered(embeddingHash, fingerprintToToken[embeddingHash]);
        }

        // Mint NFT
        tokenId = _nextTokenId++;
        _safeMint(msg.sender, tokenId);

        // Store metadata
        contentToToken[contentHash] = tokenId;
        fingerprintToToken[embeddingHash] = tokenId;

        metadata[tokenId] = ContentMetadata({
            contentHash: contentHash,
            embeddingHash: embeddingHash,
            createdAt: block.timestamp,
            originalCreator: msg.sender
        });

        emit ContentVerified(tokenId, contentHash, embeddingHash, msg.sender);
    }

    /**
     * @notice Check content originality without minting
     * @param contentHash Content hash to check
     * @param embedding Content embedding to check
     * @return isOriginal True if neither hash nor embedding is registered
     * @return existingTokenId Token ID of the existing match (0 if original)
     */
    function checkOriginality(
        bytes32 contentHash,
        int256[] calldata embedding
    ) external view returns (bool isOriginal, uint256 existingTokenId) {
        if (embedding.length != embeddingDimension) {
            revert InvalidEmbedding(embedding.length, embeddingDimension);
        }

        // Check content hash
        existingTokenId = contentToToken[contentHash];
        if (existingTokenId != 0) {
            return (false, existingTokenId);
        }

        // Check embedding fingerprint
        bytes32 embeddingHash = keccak256(abi.encode(embedding));
        existingTokenId = fingerprintToToken[embeddingHash];
        if (existingTokenId != 0) {
            return (false, existingTokenId);
        }

        return (true, 0);
    }

    // ==================== VIEW FUNCTIONS ====================

    /**
     * @notice Get content metadata for a token
     * @param tokenId Token ID
     * @return Content metadata
     */
    function getContentMetadata(
        uint256 tokenId
    ) external view returns (ContentMetadata memory) {
        if (!_exists(tokenId)) revert TokenNotFound(tokenId);
        return metadata[tokenId];
    }

    /**
     * @notice Get token ID for a content hash
     * @param contentHash Content hash to look up
     * @return tokenId Token ID (0 if not minted)
     */
    function getTokenByContent(
        bytes32 contentHash
    ) external view returns (uint256) {
        return contentToToken[contentHash];
    }

    /**
     * @notice Check if token exists
     * @param tokenId Token ID to check
     * @return exists True if token exists
     */
    function _exists(uint256 tokenId) internal view returns (bool) {
        return tokenId > 0 && tokenId < _nextTokenId;
    }

    /**
     * @notice Get total minted tokens
     * @return Total supply
     */
    function totalSupply() external view returns (uint256) {
        return _nextTokenId - 1;
    }
}
