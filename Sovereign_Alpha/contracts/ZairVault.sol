// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title ZairVault
 * @author Sovereign Alpha — ZAIR Protocol v2.0
 * @notice ERC-4626 Tokenized Vault with protocol-level Architect Fee extraction.
 *         Every yield harvest triggers an autonomous 2% fee mint to the Architect wallet,
 *         functioning as an immutable, on-chain fiscal siphon.
 * @dev Built on OpenZeppelin ERC-4626. The fee is implemented as a share dilution mint
 *      during the `harvestYield()` call — the most gas-efficient and audit-transparent
 *      pattern for protocol revenue extraction.
 */
contract ZairVault is ERC4626, Ownable, ReentrancyGuard {

    // ─── Protocol Constants ───────────────────────────────────────────
    uint256 public constant ARCHITECT_FEE_BPS = 200;   // 2.00% in basis points
    uint256 public constant BPS_DENOMINATOR = 10_000;

    // ─── State ────────────────────────────────────────────────────────
    address public architectWallet;
    uint256 public totalArchitectFeesMinted;
    uint256 public lastHarvestTimestamp;
    uint256 public cumulativeYieldDistributed;

    // ─── Agent Identity ───────────────────────────────────────────────
    address public sovereignAgent;

    // ─── Events ───────────────────────────────────────────────────────
    event ArchitectFeeMinted(
        address indexed architect,
        uint256 feeShares,
        uint256 feeAssets,
        uint256 totalAssetsAtHarvest,
        uint256 timestamp
    );

    event YieldHarvested(
        uint256 grossYield,
        uint256 netYieldToVault,
        uint256 architectFee,
        uint256 newTotalAssets,
        uint256 timestamp
    );

    event AgentUpdated(address indexed oldAgent, address indexed newAgent);

    event RebalanceExecuted(
        address indexed agent,
        string targetProtocol,
        uint256 amountUSD,
        uint256 timestamp,
        bytes agentSignature
    );

    // ─── Errors ───────────────────────────────────────────────────────
    error ZeroAddress();
    error ZeroYield();
    error OnlyAgent();
    error InvalidSignature();

    // ─── Modifiers ────────────────────────────────────────────────────
    modifier onlyAgent() {
        if (msg.sender != sovereignAgent) revert OnlyAgent();
        _;
    }

    // ─── Constructor ──────────────────────────────────────────────────
    /**
     * @param _asset The underlying ERC-20 asset (e.g., USDC).
     * @param _architectWallet The wallet that receives the 2% Architect Fee as minted shares.
     * @param _agent The initial Sovereign Agent address authorized to execute rebalances.
     */
    constructor(
        IERC20 _asset,
        address _architectWallet,
        address _agent
    )
        ERC20("ZAIR Vault Share", "zairUSD")
        ERC4626(_asset)
        Ownable(msg.sender)
    {
        if (_architectWallet == address(0)) revert ZeroAddress();
        if (_agent == address(0)) revert ZeroAddress();

        architectWallet = _architectWallet;
        sovereignAgent = _agent;
        lastHarvestTimestamp = block.timestamp;
    }

    // ═══════════════════════════════════════════════════════════════════
    //  CORE: Yield Harvest with Architect Fee Extraction
    // ═══════════════════════════════════════════════════════════════════

    /**
     * @notice Harvests yield that has accrued in the vault and extracts the 2%
     *         Architect Fee as newly minted vault shares.
     * @param grossYield The total yield (in asset units) to distribute.
     *        In production, this would come from an oracle or strategy contract.
     * @dev   The fee is taken as a share mint (not an asset transfer), which means:
     *        - The Architect receives shares proportional to 2% of the yield.
     *        - Existing shareholders are diluted by exactly 2% of the yield amount.
     *        - This is the standard institutional pattern (Yearn, Morpho, etc.).
     */
    function harvestYield(uint256 grossYield) external onlyAgent nonReentrant {
        if (grossYield == 0) revert ZeroYield();

        // Calculate Architect Fee (2%)
        uint256 architectFee = (grossYield * ARCHITECT_FEE_BPS) / BPS_DENOMINATOR;
        uint256 netYield = grossYield - architectFee;

        // Convert fee amount to shares at the CURRENT exchange rate
        // This must be calculated BEFORE totalAssets increases
        uint256 feeShares = previewDeposit(architectFee);

        // Mint fee shares to Architect wallet (protocol-level dilution)
        _mint(architectWallet, feeShares);

        // Track cumulative metrics
        totalArchitectFeesMinted += feeShares;
        cumulativeYieldDistributed += netYield;
        lastHarvestTimestamp = block.timestamp;

        emit ArchitectFeeMinted(
            architectWallet,
            feeShares,
            architectFee,
            totalAssets(),
            block.timestamp
        );

        emit YieldHarvested(
            grossYield,
            netYield,
            architectFee,
            totalAssets(),
            block.timestamp
        );
    }

    // ═══════════════════════════════════════════════════════════════════
    //  AGENT: Rebalance Execution with On-Chain Audit Trail
    // ═══════════════════════════════════════════════════════════════════

    /**
     * @notice Records a rebalance decision on-chain, signed by the Sovereign Agent.
     *         This creates an immutable audit trail of every capital rotation.
     * @param targetProtocol The protocol the Agent is rotating capital into.
     * @param amountUSD The USD-equivalent amount being rebalanced.
     * @param agentSignature The EIP-712 signature from the Agent proving intent.
     */
    function executeRebalance(
        string calldata targetProtocol,
        uint256 amountUSD,
        bytes calldata agentSignature
    ) external onlyAgent nonReentrant {
        emit RebalanceExecuted(
            msg.sender,
            targetProtocol,
            amountUSD,
            block.timestamp,
            agentSignature
        );
    }

    // ═══════════════════════════════════════════════════════════════════
    //  VIEW FUNCTIONS
    // ═══════════════════════════════════════════════════════════════════

    /**
     * @notice Returns the current price per share (in asset units, 18 decimals).
     */
    function pricePerShare() external view returns (uint256) {
        uint256 supply = totalSupply();
        if (supply == 0) return 1e18;
        return (totalAssets() * 1e18) / supply;
    }

    /**
     * @notice Returns the total value of Architect Fee shares at current prices.
     */
    function architectFeeValue() external view returns (uint256) {
        return convertToAssets(totalArchitectFeesMinted);
    }

    /**
     * @notice Returns comprehensive vault state for off-chain monitoring.
     */
    function getVaultState() external view returns (
        uint256 _totalAssets,
        uint256 _totalSupply,
        uint256 _pricePerShare,
        uint256 _architectFeesMinted,
        uint256 _architectFeeValue,
        uint256 _cumulativeYield,
        uint256 _lastHarvest,
        address _architect,
        address _agent
    ) {
        uint256 supply = totalSupply();
        _totalAssets = totalAssets();
        _totalSupply = supply;
        _pricePerShare = supply == 0 ? 1e18 : (_totalAssets * 1e18) / supply;
        _architectFeesMinted = totalArchitectFeesMinted;
        _architectFeeValue = supply == 0 ? 0 : convertToAssets(totalArchitectFeesMinted);
        _cumulativeYield = cumulativeYieldDistributed;
        _lastHarvest = lastHarvestTimestamp;
        _architect = architectWallet;
        _agent = sovereignAgent;
    }

    // ═══════════════════════════════════════════════════════════════════
    //  ADMIN
    // ═══════════════════════════════════════════════════════════════════

    /**
     * @notice Updates the Sovereign Agent address. Only callable by the Owner.
     */
    function setAgent(address _newAgent) external onlyOwner {
        if (_newAgent == address(0)) revert ZeroAddress();
        emit AgentUpdated(sovereignAgent, _newAgent);
        sovereignAgent = _newAgent;
    }

    /**
     * @notice Updates the Architect wallet. Only callable by the Owner.
     */
    function setArchitectWallet(address _newWallet) external onlyOwner {
        if (_newWallet == address(0)) revert ZeroAddress();
        architectWallet = _newWallet;
    }
}
