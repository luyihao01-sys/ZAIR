// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * 🐝 Zair Protocol Smart Contracts
 * 
 * On-chain components for the Federated Risk Intelligence Network:
 * 1. PHI Token (ERC-20) — Reward token for miners
 * 2. MinerRegistry — Track registered mining nodes
 * 3. RewardVault — Hold and distribute PHI tokens
 * 4. ConsensusOracle — Store on-chain verification records
 * 5. SlashingPool — Penalize inaccurate miners
 */

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

// ============================================================================
// 1. PHI TOKEN (ERC-20)
// ============================================================================

/**
 * @title PHI Token
 * @notice Proof-of-Alpha reward token for federated mining
 * 
 * Supply:
 * - Total: 1 Billion PHI
 * - Mint: ~450 PHI per RWA asset inference cycle
 * - Burn: Slashing mechanism removes inaccurate miner rewards
 * 
 * Uses:
 * - Validator voting power (PHI staked = governance votes)
 * - Miner reputation system
 * - DAO treasury for future enhancements
 */
contract PHI is ERC20, Ownable, Pausable {
    
    uint256 public constant INITIAL_SUPPLY = 1_000_000_000 * 10 ** 18;  // 1B PHI
    uint256 public constant MAX_SUPPLY = 2_000_000_000 * 10 ** 18;      // 2B cap
    
    address public rewardVault;
    address public minterRole;
    
    event PHIBurned(address indexed from, uint256 amount, string reason);
    event MinterUpdated(address indexed oldMinter, address indexed newMinter);
    
    constructor() ERC20("Zair PHI", "PHI") {
        _mint(msg.sender, INITIAL_SUPPLY);
    }
    
    /**
     * @notice Set authorized minter (validator contract)
     */
    function setMinter(address _minter) external onlyOwner {
        require(_minter != address(0), "Invalid minter");
        address oldMinter = minterRole;
        minterRole = _minter;
        emit MinterUpdated(oldMinter, _minter);
    }
    
    /**
     * @notice Mint tokens (only minter role)
     */
    function mint(address to, uint256 amount) external {
        require(msg.sender == minterRole, "Only minter");
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        _mint(to, amount);
    }
    
    /**
     * @notice Burn tokens (slashing for inaccurate nodes)
     */
    function burn(uint256 amount) public override {
        _burn(_msgSender(), amount);
    }
    
    /**
     * @notice Burn from address (slashing mechanism)
     */
    function burnFrom(address account, uint256 amount) external onlyOwner {
        _burn(account, amount);
        emit PHIBurned(account, amount, "slashing");
    }
    
    /**
     * @notice Pause all transfers (emergency)
     */
    function pause() external onlyOwner {
        _pause();
    }
    
    /**
     * @notice Resume transfers
     */
    function unpause() external onlyOwner {
        _unpause();
    }
    
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override whenNotPaused {
        super._beforeTokenTransfer(from, to, amount);
    }
}


// ============================================================================
// 2. MINER REGISTRY
// ============================================================================

/**
 * @title MinerRegistry
 * @notice Track registered mining nodes and their metadata
 */
contract MinerRegistry is Ownable {
    
    struct Miner {
        string nodeName;         // e.g., "Node_Dubai"
        string region;          // e.g., "MEA"
        address ethAddress;     // Wallet for receiving PHI
        uint256 registeredAt;   // Block timestamp
        uint256 cumulativeTokens;  // Total PHI earned
        bool isActive;          // Can submit vectors?
    }
    
    mapping(string => Miner) public miners;  // nodeName -> Miner
    mapping(address => string) public addressToNode;  // eth address -> nodeName
    string[] public activeNodes;
    
    event MinerRegistered(string indexed nodeName, address indexed ethAddress, string region);
    event MinerDeactivated(string indexed nodeName);
    event TokensUpdated(string indexed nodeName, uint256 newTotal);
    
    /**
     * @notice Register new mining node
     */
    function registerMiner(
        string memory _nodeName,
        string memory _region,
        address _ethAddress
    ) external onlyOwner {
        require(_ethAddress != address(0), "Invalid address");
        require(miners[_nodeName].ethAddress == address(0), "Already registered");
        
        miners[_nodeName] = Miner({
            nodeName: _nodeName,
            region: _region,
            ethAddress: _ethAddress,
            registeredAt: block.timestamp,
            cumulativeTokens: 0,
            isActive: true
        });
        
        addressToNode[_ethAddress] = _nodeName;
        activeNodes.push(_nodeName);
        
        emit MinerRegistered(_nodeName, _ethAddress, _region);
    }
    
    /**
     * @notice Update miner's cumulative tokens (called by validator)
     */
    function updateTokens(string memory _nodeName, uint256 _tokensEarned) external onlyOwner {
        require(miners[_nodeName].ethAddress != address(0), "Miner not found");
        miners[_nodeName].cumulativeTokens += _tokensEarned;
        emit TokensUpdated(_nodeName, miners[_nodeName].cumulativeTokens);
    }
    
    /**
     * @notice Get miner info
     */
    function getMiner(string memory _nodeName) external view returns (Miner memory) {
        return miners[_nodeName];
    }
    
    /**
     * @notice Get all active nodes
     */
    function getActiveNodes() external view returns (string[] memory) {
        return activeNodes;
    }
}


// ============================================================================
// 3. REWARD VAULT
// ============================================================================

/**
 * @title RewardVault
 * @notice Hold and distribute PHI token rewards from validator
 */
contract RewardVault is Ownable {
    
    PHI public phiToken;
    MinerRegistry public minerRegistry;
    
    uint256 public totalRewardsDistributed;
    mapping(string => uint256) public minerRewards;  // nodeName -> unclaimed PHI
    
    event RewardDistributed(string indexed nodeName, uint256 amount);
    event RewardClaimed(string indexed nodeName, address indexed claimant, uint256 amount);
    
    constructor(address _phiToken, address _minerRegistry) {
        phiToken = PHI(_phiToken);
        minerRegistry = MinerRegistry(_minerRegistry);
    }
    
    /**
     * @notice Distribute rewards to miners (called by validator)
     */
    function distributeRewards(
        string memory _nodeName,
        uint256 _phiAmount
    ) external onlyOwner {
        require(_phiAmount > 0, "Invalid amount");
        
        minerRewards[_nodeName] += _phiAmount;
        totalRewardsDistributed += _phiAmount;
        
        emit RewardDistributed(_nodeName, _phiAmount);
    }
    
    /**
     * @notice Claim accumulated rewards
     */
    function claimRewards(string memory _nodeName) external {
        uint256 amount = minerRewards[_nodeName];
        require(amount > 0, "No rewards");
        
        MinerRegistry.Miner memory miner = minerRegistry.getMiner(_nodeName);
        require(msg.sender == miner.ethAddress, "Not miner");
        
        minerRewards[_nodeName] = 0;
        phiToken.transfer(msg.sender, amount);
        
        emit RewardClaimed(_nodeName, msg.sender, amount);
    }
    
    /**
     * @notice Get pending rewards for miner
     */
    function getPendingRewards(string memory _nodeName) external view returns (uint256) {
        return minerRewards[_nodeName];
    }
}


// ============================================================================
// 4. CONSENSUS ORACLE (On-Chain Verification)
// ============================================================================

/**
 * @title ConsensusOracle
 * @notice Store and verify consensus results on-chain
 */
contract ConsensusOracle is Ownable {
    
    struct ConsensusRecord {
        string assetId;
        string assetName;
        uint256 consensusRisk;          // Scaled: 0-10000 (0-100.00%)
        uint256 consensusConfidence;
        string sentiment;               // "bullish", "neutral", "bearish"
        uint256 numNodes;
        uint256 totalTokensDistributed;
        uint256 recordedAt;
        bool resolved;                  // Outcome verified?
        bool actualStability;           // Ground truth
    }
    
    mapping(string => ConsensusRecord) public records;  // assetId -> record
    string[] public recordedAssets;
    
    event ConsensusRecorded(
        string indexed assetId,
        uint256 consensusRisk,
        uint256 numNodes
    );
    event ConsensusResolved(
        string indexed assetId,
        bool actualStability,
        uint256 tokensDistributed
    );
    
    /**
     * @notice Record consensus result on-chain
     */
    function recordConsensus(
        string memory _assetId,
        string memory _assetName,
        uint256 _consensusRisk,
        uint256 _confidence,
        string memory _sentiment,
        uint256 _numNodes,
        uint256 _totalTokens
    ) external onlyOwner {
        require(records[_assetId].recordedAt == 0, "Already recorded");
        
        records[_assetId] = ConsensusRecord({
            assetId: _assetId,
            assetName: _assetName,
            consensusRisk: _consensusRisk,
            consensusConfidence: _confidence,
            sentiment: _sentiment,
            numNodes: _numNodes,
            totalTokensDistributed: _totalTokens,
            recordedAt: block.timestamp,
            resolved: false,
            actualStability: false
        });
        
        recordedAssets.push(_assetId);
        
        emit ConsensusRecorded(_assetId, _consensusRisk, _numNodes);
    }
    
    /**
     * @notice Resolve with ground truth (after settlement)
     */
    function resolveConsensus(
        string memory _assetId,
        bool _actualStability
    ) external onlyOwner {
        require(records[_assetId].recordedAt != 0, "Not recorded");
        require(!records[_assetId].resolved, "Already resolved");
        
        records[_assetId].resolved = true;
        records[_assetId].actualStability = _actualStability;
        
        emit ConsensusResolved(
            _assetId,
            _actualStability,
            records[_assetId].totalTokensDistributed
        );
    }
    
    /**
     * @notice Get record
     */
    function getRecord(string memory _assetId) 
        external 
        view 
        returns (ConsensusRecord memory) 
    {
        return records[_assetId];
    }
}


// ============================================================================
// 5. SLASHING POOL (Penalize Inaccurate Miners)
// ============================================================================

/**
 * @title SlashingPool
 * @notice Penalize miners who consistently submit inaccurate vectors
 */
contract SlashingPool is Ownable {
    
    PHI public phiToken;
    MinerRegistry public minerRegistry;
    
    uint256 public slashThreshold = 3;      // Slash after 3 consecutive misses
    mapping(string => uint256) public consecutiveMisses;
    mapping(string => uint256) public slashedAmount;
    
    event MinerSlashed(string indexed nodeName, uint256 slashAmount, string reason);
    
    constructor(address _phiToken, address _minerRegistry) {
        phiToken = PHI(_phiToken);
        minerRegistry = MinerRegistry(_minerRegistry);
    }
    
    /**
     * @notice Record a miss (inaccurate prediction)
     */
    function recordMiss(string memory _nodeName, uint256 _tokensToSlash) external onlyOwner {
        consecutiveMisses[_nodeName]++;
        
        if (consecutiveMisses[_nodeName] >= slashThreshold) {
            _slash(_nodeName, _tokensToSlash);
        }
    }
    
    /**
     * @notice Reset miss counter on accurate prediction
     */
    function resetMissCounter(string memory _nodeName) external onlyOwner {
        consecutiveMisses[_nodeName] = 0;
    }
    
    /**
     * @notice Internal slash function
     */
    function _slash(string memory _nodeName, uint256 _amount) internal {
        require(_amount > 0, "Invalid slash amount");
        
        MinerRegistry.Miner memory miner = minerRegistry.getMiner(_nodeName);
        uint256 actualSlash = _amount > miner.cumulativeTokens ? 
            miner.cumulativeTokens : _amount;
        
        phiToken.burnFrom(miner.ethAddress, actualSlash);
        slashedAmount[_nodeName] += actualSlash;
        consecutiveMisses[_nodeName] = 0;
        
        emit MinerSlashed(_nodeName, actualSlash, "consecutive_misses");
    }
    
    /**
     * @notice Set slash threshold
     */
    function setSlashThreshold(uint256 _threshold) external onlyOwner {
        require(_threshold > 0, "Invalid threshold");
        slashThreshold = _threshold;
    }
}
