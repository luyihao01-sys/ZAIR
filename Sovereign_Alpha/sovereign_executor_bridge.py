#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║          SOVEREIGN EXECUTOR BRIDGE v1.0                            ║
║    Intent Solver → Gnosis Safe Transaction Payload Engine          ║
║                                                                    ║
║  Receives solver JSON, applies Protocol Tax, builds Safe-ready     ║
║  multi-call transaction payloads with hex-encoded calldata.        ║
╚══════════════════════════════════════════════════════════════════════╝

Usage:
    # From solver JSON file:
    python sovereign_executor_bridge.py --input solver_report.json

    # Pipe from solver:
    python sovereign_intent_solver.py "maximize yield" | python sovereign_executor_bridge.py --stdin

    # With custom Safe & wallet addresses:
    python sovereign_executor_bridge.py --input solver_report.json ^
        --safe 0x1234...abcd --architect-wallet 0xABCD...1234
"""

import json
import sys
import os
import time
import hmac
import hashlib
import argparse
from datetime import datetime, timezone, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
#  Windows console UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
#  Web3 Import
# ---------------------------------------------------------------------------
try:
    from web3 import Web3
    from eth_abi import encode as abi_encode
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False

# ---------------------------------------------------------------------------
#  Constants & Configuration
# ---------------------------------------------------------------------------

# Default addresses (Ethereum mainnet dry-run placeholders)
DEFAULT_SAFE_ADDRESS = "0x50Vere19n5AFe000000000000000000000000001"
DEFAULT_ARCHITECT_WALLET = "0xA2C41tECfEEwa11E7000000000000000000000002"
DEFAULT_USDC_TOKEN = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"     # USDC
DEFAULT_USDT_TOKEN = "0xdAC17F958D2ee523a2206206994597C13D831ec7"     # USDT

PROTOCOL_TAX_PCT = 2.0  # 2% performance fee to Architect Wallet

# Known protocol deposit contract addresses (mainnet)
PROTOCOL_CONTRACTS = {
    "Ondo Finance (USDY)": {
        "deposit_contract": "0x96F6eF951840721AdBF46Ac996b59E0235CB985C",
        "token_out": "USDY",
        "method": "deposit(uint256)",
        "method_id": "0xb6b55f25",
    },
    "BlackRock BUIDL": {
        "deposit_contract": "0x7712c34205737192402172185a29E4395e4C36e0",
        "token_out": "BUIDL",
        "method": "subscribe(uint256)",
        "method_id": "0xa694fc3a",
    },
    "Centrifuge (CFG)": {
        "deposit_contract": "0x4597ca09fCB98080a5A5F2e7DE3E40869b1Af818",
        "token_out": "CFG-LP",
        "method": "requestDeposit(uint256,address)",
        "method_id": "0xe8eda9df",
    },
    "sDAI (Spark/MakerDAO)": {
        "deposit_contract": "0x83F20F44975D03b1b09e64809B757c47f942BEeA",
        "token_out": "sDAI",
        "method": "deposit(uint256,address)",
        "method_id": "0x6e553f65",
    },
    "Ethena sUSDe": {
        "deposit_contract": "0x9D39A5DE30e57443BfF2A8307A4256c8797A3497",
        "token_out": "sUSDe",
        "method": "deposit(uint256,address)",
        "method_id": "0x6e553f65",
    },
    "Aave USDC": {
        "deposit_contract": "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
        "token_out": "aUSDC",
        "method": "supply(address,uint256,address,uint16)",
        "method_id": "0x617ba037",
    },
}

# ERC-20 ABI fragment for transfer & approve
ERC20_TRANSFER_METHOD_ID = "0xa9059cbb"   # transfer(address,uint256)
ERC20_APPROVE_METHOD_ID = "0x095ea7b3"    # approve(address,uint256)

# Gnosis Safe constants
SAFE_OPERATION_CALL = 0
SAFE_OPERATION_DELEGATECALL = 1

SIGNING_KEY_ENV = "SOVEREIGN_SIGNING_KEY"

# Default allocation amount (in USDC, 6 decimals)
DEFAULT_ALLOCATION_USD = 1_000_000  # $1M per action


# ---------------------------------------------------------------------------
#  Web3 Helpers
# ---------------------------------------------------------------------------

def get_web3() -> "Web3":
    """Initialize a Web3 instance (dry-run mode with no real RPC)."""
    if not HAS_WEB3:
        raise RuntimeError("web3.py not installed. Run: pip install web3")
    # Use a local provider that won't make real calls
    return Web3(Web3.EthereumTesterProvider() if hasattr(Web3, 'EthereumTesterProvider')
                else Web3())


def to_checksum(addr: str) -> str:
    """Convert to checksum address, handling placeholder addresses."""
    try:
        return Web3.to_checksum_address(addr)
    except Exception:
        return addr


def encode_uint256(value: int) -> str:
    """Encode a uint256 value as 32-byte hex."""
    return hex(value)[2:].zfill(64)


def encode_address(addr: str) -> str:
    """Encode an address as 32-byte hex (left-padded).

    Strips any non-hex characters to handle placeholder addresses.
    """
    clean = addr.lower().replace("0x", "")
    # Keep only valid hex characters
    clean = "".join(c for c in clean if c in "0123456789abcdef")
    # Pad or truncate to exactly 40 hex chars (20 bytes)
    clean = clean[:40].ljust(40, "0")
    return clean.zfill(64)


# ---------------------------------------------------------------------------
#  Protocol Tax Calculator
# ---------------------------------------------------------------------------

def calculate_protocol_tax(
    gross_amount_usd: float,
    tax_pct: float = PROTOCOL_TAX_PCT,
) -> dict:
    """Calculate the Architect's performance fee (Protocol Tax).

    Before any allocation, the tax is deducted and routed to the
    Architect Wallet. The remaining amount goes to the protocol.

    Returns breakdown with token amounts (USDC, 6 decimals).
    """
    tax_amount = gross_amount_usd * (tax_pct / 100)
    net_amount = gross_amount_usd - tax_amount

    return {
        "gross_amount_usd": gross_amount_usd,
        "tax_pct": tax_pct,
        "tax_amount_usd": round(tax_amount, 2),
        "net_amount_usd": round(net_amount, 2),
        "tax_amount_wei": int(tax_amount * 1e6),      # USDC 6 decimals
        "net_amount_wei": int(net_amount * 1e6),
    }


# ---------------------------------------------------------------------------
#  Safe Transaction Builder
# ---------------------------------------------------------------------------

def build_erc20_transfer_calldata(to_address: str, amount_wei: int) -> str:
    """Build ERC-20 transfer(address, uint256) calldata."""
    return (
        ERC20_TRANSFER_METHOD_ID
        + encode_address(to_address)
        + encode_uint256(amount_wei)
    )


def build_erc20_approve_calldata(spender: str, amount_wei: int) -> str:
    """Build ERC-20 approve(address, uint256) calldata."""
    return (
        ERC20_APPROVE_METHOD_ID
        + encode_address(spender)
        + encode_uint256(amount_wei)
    )


def build_deposit_calldata(protocol_name: str, amount_wei: int, recipient: str) -> str:
    """Build protocol-specific deposit calldata."""
    proto = PROTOCOL_CONTRACTS.get(protocol_name, {})
    method_id = proto.get("method_id", "0x00000000")
    method = proto.get("method", "")

    if "address" in method:
        # deposit(uint256, address) or similar
        return method_id + encode_uint256(amount_wei) + encode_address(recipient)
    else:
        # deposit(uint256) only
        return method_id + encode_uint256(amount_wei)


def build_safe_tx(
    to: str,
    value: int,
    data: str,
    operation: int = SAFE_OPERATION_CALL,
    description: str = "",
) -> dict:
    """Build a single Gnosis Safe transaction object."""
    return {
        "to": to,
        "value": str(value),
        "data": data,
        "operation": operation,
        "description": description,
    }


# ---------------------------------------------------------------------------
#  Core Bridge: Intent Action → Safe Batch Transaction
# ---------------------------------------------------------------------------

def bridge_action_to_safe_txs(
    action: dict,
    safe_address: str,
    architect_wallet: str,
    usdc_token: str,
    allocation_usd: float,
) -> dict:
    """Convert a solver action into a batch of Safe transactions.

    For ALLOCATE / ALLOCATE_RISK_FREE:
        TX1: Transfer Protocol Tax (2%) to Architect Wallet
        TX2: Approve deposit contract to spend net amount
        TX3: Deposit net amount into protocol

    For EMERGENCY_EXIT:
        TX1: Withdraw all from protocol (encoded as generic call)
        TX2: Transfer recovered funds to Safe (self)
    """
    action_type = action.get("action", "")
    protocol = action.get("protocol", action.get("source_protocol", "Unknown"))
    proto_info = PROTOCOL_CONTRACTS.get(protocol, {})
    deposit_contract = proto_info.get("deposit_contract", "0x" + "0" * 40)

    transactions = []
    tax_info = None

    if action_type in ("ALLOCATE", "ALLOCATE_RISK_FREE"):
        # ── Calculate Protocol Tax ──────────────────────────────────
        tax_info = calculate_protocol_tax(allocation_usd, PROTOCOL_TAX_PCT)

        # TX1: Transfer tax to Architect Wallet
        tax_calldata = build_erc20_transfer_calldata(
            architect_wallet, tax_info["tax_amount_wei"]
        )
        transactions.append(build_safe_tx(
            to=usdc_token,
            value=0,
            data=tax_calldata,
            description=f"Protocol Tax: Transfer ${tax_info['tax_amount_usd']:,.2f} USDC ({PROTOCOL_TAX_PCT}%) to Architect Wallet",
        ))

        # TX2: Approve protocol to spend net amount
        approve_calldata = build_erc20_approve_calldata(
            deposit_contract, tax_info["net_amount_wei"]
        )
        transactions.append(build_safe_tx(
            to=usdc_token,
            value=0,
            data=approve_calldata,
            description=f"Approve {protocol} to spend ${tax_info['net_amount_usd']:,.2f} USDC",
        ))

        # TX3: Deposit into protocol
        deposit_calldata = build_deposit_calldata(
            protocol, tax_info["net_amount_wei"], safe_address
        )
        transactions.append(build_safe_tx(
            to=deposit_contract,
            value=0,
            data=deposit_calldata,
            description=f"Deposit ${tax_info['net_amount_usd']:,.2f} USDC into {protocol}",
        ))

    elif action_type == "EMERGENCY_EXIT":
        # Emergency: encode a generic withdraw call
        # In production, this would call protocol-specific withdraw methods
        withdraw_method_id = "0x2e1a7d4d"  # withdraw(uint256)
        max_uint = (2 ** 256) - 1
        withdraw_calldata = withdraw_method_id + encode_uint256(max_uint)

        transactions.append(build_safe_tx(
            to=deposit_contract,
            value=0,
            data=withdraw_calldata,
            description=f"EMERGENCY: Withdraw ALL from {protocol}",
        ))

        # Route recovered funds to sDAI as safe haven
        safe_haven = PROTOCOL_CONTRACTS.get("sDAI (Spark/MakerDAO)", {})
        if safe_haven:
            transactions.append(build_safe_tx(
                to=safe_haven.get("deposit_contract", "0x" + "0" * 40),
                value=0,
                data="0x",  # Placeholder — amount unknown until withdraw settles
                description=f"Re-route recovered funds to sDAI safe haven",
            ))

    elif action_type == "REDIRECT_TO_RISK_FREE":
        # Redirect is informational — build allocation to best risk-free pool
        tax_info = calculate_protocol_tax(allocation_usd, PROTOCOL_TAX_PCT)

        # TX1: Protocol Tax
        tax_calldata = build_erc20_transfer_calldata(
            architect_wallet, tax_info["tax_amount_wei"]
        )
        transactions.append(build_safe_tx(
            to=usdc_token,
            value=0,
            data=tax_calldata,
            description=f"Protocol Tax: ${tax_info['tax_amount_usd']:,.2f} USDC → Architect Wallet",
        ))

        # TX2: Deposit into sDAI (default risk-free destination)
        sdai = PROTOCOL_CONTRACTS.get("sDAI (Spark/MakerDAO)", {})
        deposit_calldata = build_deposit_calldata(
            "sDAI (Spark/MakerDAO)", tax_info["net_amount_wei"], safe_address
        )
        transactions.append(build_safe_tx(
            to=sdai.get("deposit_contract", "0x" + "0" * 40),
            value=0,
            data=deposit_calldata,
            description=f"Deposit ${tax_info['net_amount_usd']:,.2f} into sDAI (risk-free redirect)",
        ))

    return {
        "action": action,
        "protocol": protocol,
        "tax_breakdown": tax_info,
        "transactions": transactions,
        "transaction_count": len(transactions),
    }


# ---------------------------------------------------------------------------
#  Multi-Send Encoder (Safe Batch)
# ---------------------------------------------------------------------------

def encode_multi_send(transactions: list[dict]) -> str:
    """Encode transactions into Gnosis Safe MultiSend format.

    MultiSend packed encoding:
        For each tx: operation (1 byte) + to (20 bytes) + value (32 bytes)
                     + data_length (32 bytes) + data (variable)
    """
    packed = b""
    for tx in transactions:
        operation = tx.get("operation", SAFE_OPERATION_CALL)
        to_addr = tx["to"].replace("0x", "").lower()
        # Strip non-hex chars, pad/truncate to 20 bytes (40 hex chars)
        to_addr = "".join(c for c in to_addr if c in "0123456789abcdef")
        to_addr = to_addr[:40].ljust(40, "0")
        to_bytes = bytes.fromhex(to_addr)
        value = int(tx.get("value", "0"))
        data_hex = tx.get("data", "0x").replace("0x", "")
        if len(data_hex) % 2 != 0:
            data_hex = "0" + data_hex
        data_bytes = bytes.fromhex(data_hex) if data_hex else b""

        packed += operation.to_bytes(1, "big")
        packed += to_bytes
        packed += value.to_bytes(32, "big")
        packed += len(data_bytes).to_bytes(32, "big")
        packed += data_bytes

    return "0x" + packed.hex()


# ---------------------------------------------------------------------------
#  Safe Transaction Hash (EIP-712 style)
# ---------------------------------------------------------------------------

def compute_safe_tx_hash(
    safe_address: str,
    multi_send_data: str,
    nonce: int = 0,
    chain_id: int = 1,
) -> str:
    """Compute a simplified Safe transaction hash for display.

    Note: In production, use the full EIP-712 typed data hash with
    the Safe's domain separator. This is a simplified version for
    demonstration and dry-run purposes.
    """
    preimage = (
        f"{safe_address}:{chain_id}:{nonce}:{multi_send_data}"
    ).encode("utf-8")
    return "0x" + hashlib.sha256(preimage).hexdigest()


# ---------------------------------------------------------------------------
#  HMAC Signing
# ---------------------------------------------------------------------------

def sign_bridge_output(result: dict, signing_key: str) -> dict:
    """Sign the bridge output for oracle chain."""
    payload = {
        "epoch_utc": result["epoch_utc"],
        "safe_tx_hash": result.get("safe_tx_hash", ""),
        "total_tax_usd": result.get("total_tax_usd", 0),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    sig = hmac.new(
        signing_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "algorithm": "HMAC-SHA256",
        "signature": sig,
        "signer": "sovereign-executor-bridge",
    }


# ---------------------------------------------------------------------------
#  Pretty Console Output
# ---------------------------------------------------------------------------

def print_banner():
    print(r"""
    ╔══════════════════════════════════════════════════════════════╗
    ║   🌉  SOVEREIGN EXECUTOR BRIDGE  🌉                       ║
    ║   Intent Solver → Gnosis Safe Transaction Engine            ║
    ╚══════════════════════════════════════════════════════════════╝
    """)


def print_result(result: dict):
    print(f"  🏦  Safe Address     : {result['safe_address']}")
    print(f"  👛  Architect Wallet : {result['architect_wallet']}")
    print(f"  💰  Allocation/Action: ${result['allocation_usd']:,.0f}")
    print(f"  🏷️  Protocol Tax     : {PROTOCOL_TAX_PCT}%")
    print()

    for i, batch in enumerate(result["batches"], 1):
        action = batch["action"]
        protocol = batch["protocol"]
        print(f"  ┌──────────────────────────────────────────────────────────┐")
        print(f"  │  📦 BATCH {i}: {action.get('action', 'N/A'):<42} │")
        print(f"  │  Protocol: {protocol:<46} │")
        print(f"  ├──────────────────────────────────────────────────────────┤")

        tax = batch.get("tax_breakdown")
        if tax:
            print(f"  │  Gross : ${tax['gross_amount_usd']:>12,.2f}")
            print(f"  │  Tax   : ${tax['tax_amount_usd']:>12,.2f}  ({tax['tax_pct']}%)")
            print(f"  │  Net   : ${tax['net_amount_usd']:>12,.2f}")
            print(f"  ├──────────────────────────────────────────────────────────┤")

        for j, tx in enumerate(batch["transactions"], 1):
            print(f"  │  TX{j}: {tx['description']}")
            print(f"  │   to  : {tx['to']}")
            data_preview = tx["data"][:42] + "…" if len(tx["data"]) > 42 else tx["data"]
            print(f"  │   data : {data_preview}")
        print(f"  └──────────────────────────────────────────────────────────┘")
        print()

    # Multi-send & hash
    print(f"  ┌──────────────────────────────────────────────────────────┐")
    print(f"  │  🔐 SAFE TRANSACTION SUMMARY                            │")
    print(f"  ├──────────────────────────────────────────────────────────┤")
    ms = result["multi_send_data"]
    print(f"  │  MultiSend Data : {ms[:48]}…")
    print(f"  │  Data Length    : {len(ms)} chars ({(len(ms)-2)//2} bytes)")
    print(f"  │  Safe TX Hash   : {result['safe_tx_hash']}")
    print(f"  │  Total Tax      : ${result['total_tax_usd']:,.2f}")
    sig = result.get("oracle_signature", {})
    if sig.get("signature"):
        print(f"  │  Oracle Sig     : {sig['signature'][:32]}…")
        print(f"  │  Status         : ✅ SIGNED")
    else:
        print(f"  │  Status         : ⚠️ UNSIGNED")
    print(f"  └──────────────────────────────────────────────────────────┘")


# ---------------------------------------------------------------------------
#  Core Bridge Pipeline
# ---------------------------------------------------------------------------

def execute_bridge(
    solver_output: dict,
    safe_address: str,
    architect_wallet: str,
    usdc_token: str,
    allocation_usd: float,
    signing_key: Optional[str] = None,
) -> dict:
    """Full pipeline: solver JSON → Safe transaction payload."""
    now = datetime.now(timezone(timedelta(hours=8)))

    # Collect all actionable items
    actionable = []

    # Primary recommendation
    primary = solver_output.get("primary_recommendation")
    if primary and primary.get("action") in ("ALLOCATE", "EMERGENCY_EXIT", "REDIRECT_TO_RISK_FREE", "ALLOCATE_RISK_FREE"):
        actionable.append(primary)

    # Emergency exits (highest priority)
    for ex in solver_output.get("emergency_exits", []):
        if ex not in actionable:
            actionable.append(ex)

    # Build batches
    batches = []
    all_txs = []
    total_tax = 0.0

    for action in actionable:
        batch = bridge_action_to_safe_txs(
            action, safe_address, architect_wallet, usdc_token, allocation_usd
        )
        batches.append(batch)
        all_txs.extend(batch["transactions"])
        if batch["tax_breakdown"]:
            total_tax += batch["tax_breakdown"]["tax_amount_usd"]

    # Encode multi-send
    multi_send_data = encode_multi_send(all_txs) if all_txs else "0x"
    safe_tx_hash = compute_safe_tx_hash(safe_address, multi_send_data)

    result = {
        "bridge_title": "Sovereign Executor Bridge — Safe Transaction Payload",
        "generated_at": now.isoformat(),
        "epoch_utc": int(time.time()),
        "safe_address": safe_address,
        "architect_wallet": architect_wallet,
        "usdc_token": usdc_token,
        "allocation_usd": allocation_usd,
        "protocol_tax_pct": PROTOCOL_TAX_PCT,
        "total_tax_usd": round(total_tax, 2),
        "batches": batches,
        "all_transactions": all_txs,
        "transaction_count": len(all_txs),
        "multi_send_data": multi_send_data,
        "safe_tx_hash": safe_tx_hash,
        "solver_intent": solver_output.get("intent", {}),
        "solver_signature": solver_output.get("oracle_signature", {}),
    }

    # Sign
    if signing_key:
        result["oracle_signature"] = sign_bridge_output(result, signing_key)
    else:
        result["oracle_signature"] = {"status": "UNSIGNED"}

    return result


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sovereign Executor Bridge — Intent → Safe TX Engine"
    )
    parser.add_argument("--input", "-f", type=str, help="Path to solver JSON output file")
    parser.add_argument("--stdin", action="store_true", help="Read solver JSON from stdin")
    parser.add_argument("--output", "-o", type=str, default=None, help="Save result JSON to file")
    parser.add_argument("--safe", type=str, default=DEFAULT_SAFE_ADDRESS, help="Gnosis Safe address")
    parser.add_argument("--architect-wallet", type=str, default=DEFAULT_ARCHITECT_WALLET, help="Architect fee wallet")
    parser.add_argument("--usdc", type=str, default=DEFAULT_USDC_TOKEN, help="USDC token address")
    parser.add_argument("--amount", type=float, default=DEFAULT_ALLOCATION_USD, help="Allocation amount in USD")
    args = parser.parse_args()

    print_banner()

    # ── Load solver output ──────────────────────────────────────────────
    solver_output = None

    if args.stdin:
        print("  [INFO] Reading solver JSON from stdin…")
        raw = sys.stdin.read()
        solver_output = json.loads(raw)
    elif args.input:
        print(f"  [INFO] Loading solver output from: {args.input}")
        with open(args.input, "r", encoding="utf-8") as f:
            solver_output = json.load(f)
    else:
        # Try default path
        default_path = os.path.join(os.path.dirname(__file__), "solver_report.json")
        if os.path.exists(default_path):
            print(f"  [INFO] Loading default: {default_path}")
            with open(default_path, "r", encoding="utf-8") as f:
                solver_output = json.load(f)
        else:
            print("  [ERROR] No input provided. Use --input <file> or --stdin")
            sys.exit(1)

    intent = solver_output.get("intent", {})
    print(f"  [OK]   Solver intent: \"{intent.get('raw_input', 'N/A')}\"")
    print(f"  [OK]   Actions: {len(solver_output.get('all_actions', []))} | "
          f"Emergencies: {len(solver_output.get('emergency_exits', []))}\n")

    # ── Signing key ─────────────────────────────────────────────────────
    signing_key = os.environ.get(SIGNING_KEY_ENV, "")
    if signing_key:
        print(f"  [INFO] Oracle signing key loaded.")
    else:
        print(f"  [WARN] {SIGNING_KEY_ENV} not set — output will be UNSIGNED\n")

    # ── Execute bridge ──────────────────────────────────────────────────
    print("  [INFO] Building Safe transaction payloads…\n")
    result = execute_bridge(
        solver_output=solver_output,
        safe_address=args.safe,
        architect_wallet=args.architect_wallet,
        usdc_token=args.usdc,
        allocation_usd=args.amount,
        signing_key=signing_key or None,
    )

    # ── Output ──────────────────────────────────────────────────────────
    print_result(result)
    print()

    result_json = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result_json)
        print(f"  [OK] JSON saved to: {args.output}")
    else:
        print("  ═══════════════════ JSON PAYLOAD ═══════════════════")
        print(result_json)

    print("\n  [DONE] Sovereign Executor Bridge complete. 🌉\n")


if __name__ == "__main__":
    main()
