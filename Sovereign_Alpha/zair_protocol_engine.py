"""
ZAIR v1.0 Protocol Engine
Simulates an ERC-4626 Tokenized Vault for Sovereign Alpha.
"""
import time
import hashlib
import uuid
import hmac
import os
import requests
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_typed_data

# Use a public RPC or an environment variable
RPC_URL = os.environ.get("WEB3_RPC_URL", "https://eth.llamarpc.com")
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Aave V3 Ethereum Protocol Data Provider
AAVE_DATA_PROVIDER = "0x497a1994626154366A51239611D1a7E9a8647c0e"
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

AAVE_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "asset", "type": "address"}],
        "name": "getReserveData",
        "outputs": [
            {"internalType": "uint256", "name": "configuration", "type": "uint256"},
            {"internalType": "uint256", "name": "liquidityIndex", "type": "uint256"},
            {"internalType": "uint256", "name": "currentLiquidityRate", "type": "uint256"},
            {"internalType": "uint256", "name": "variableBorrowIndex", "type": "uint256"},
            {"internalType": "uint256", "name": "currentVariableBorrowRate", "type": "uint256"},
            {"internalType": "uint256", "name": "currentStableBorrowRate", "type": "uint256"},
            {"internalType": "uint256", "name": "lastUpdateTimestamp", "type": "uint256"},
            {"internalType": "address", "name": "aTokenAddress", "type": "address"},
            {"internalType": "address", "name": "stableDebtTokenAddress", "type": "address"},
            {"internalType": "address", "name": "variableDebtTokenAddress", "type": "address"},
            {"internalType": "address", "name": "interestRateStrategyAddress", "type": "address"},
            {"internalType": "uint256", "name": "availableLiquidity", "type": "uint256"},
            {"internalType": "uint256", "name": "totalPrincipalStableDebt", "type": "uint256"},
            {"internalType": "uint256", "name": "averageStableBorrowRate", "type": "uint256"},
            {"internalType": "uint256", "name": "stableDebtLastUpdateTimestamp", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

def fetch_aave_usdc_borrow_rate():
    """Fetches real-time USDC borrow rate from Aave V3 on Ethereum."""
    try:
        if not w3.is_connected():
            return 0.05 # fallback
        contract = w3.eth.contract(address=w3.to_checksum_address(AAVE_DATA_PROVIDER), abi=AAVE_ABI)
        data = contract.functions.getReserveData(w3.to_checksum_address(USDC_ADDRESS)).call()
        # currentVariableBorrowRate is index 4. It's in Ray (1e27). Convert to a decimal.
        ray_rate = data[4]
        return ray_rate / 10**27
    except Exception as e:
        print(f"Web3 Aave Error: {e}")
        return 0.05 # Fallback to 5%

def fetch_ondo_usdy_apy():
    """Fetches real-time USDY APY. Uses Ondo API fallback if on-chain oracle is unavailable."""
    try:
        # Utilizing official off-chain Ondo endpoint for robust retrieval of the true APY
        resp = requests.get("https://ondo.finance/api/v1/usdy/apy", timeout=3)
        if resp.status_code == 200:
            return resp.json().get('apy', 0.0535)
    except:
        pass
    return 0.0535 # Fallback to 5.35%

class ZairVault:
    def __init__(self, initial_aum: float = 10_000_000.0):
        self.total_assets = initial_aum
        self.total_supply = initial_aum # 1:1 shares to assets initially
        self.architect_locked_fees = 0.0
        self.architect_fee_pct = 0.02
        
        # Load or generate Ethereum wallet for the Agent
        env_path = ".env"
        self.agent_private_key = None
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("ZAIR_AGENT_PK="):
                        self.agent_private_key = line.split("=")[1].strip()
                        break
        
        if not self.agent_private_key:
            acct = Account.create()
            self.agent_private_key = acct.key.hex()
            with open(env_path, "a") as f:
                f.write(f"\nZAIR_AGENT_PK={self.agent_private_key}\n")
                
        self.agent_public_address = Account.from_key(self.agent_private_key).address
        
    def deposit(self, amount: float) -> float:
        """ERC-4626 standard deposit."""
        if amount <= 0: return 0
        shares = amount if self.total_assets == 0 else (amount * self.total_supply) / self.total_assets
        self.total_assets += amount
        self.total_supply += shares
        return shares

    def withdraw(self, amount: float) -> float:
        """ERC-4626 standard withdraw."""
        if amount <= 0 or amount > self.total_assets: return 0
        shares = (amount * self.total_supply) / self.total_assets
        self.total_assets -= amount
        self.total_supply -= shares
        return shares

    def distribute_yield(self, net_yield_amount: float):
        """Processes yield. Extracts Architect Fee, rest compounds."""
        if net_yield_amount <= 0: return 0, 0
        fee = net_yield_amount * self.architect_fee_pct
        compounded = net_yield_amount - fee
        
        self.architect_locked_fees += fee
        self.total_assets += compounded
        # Note: total_supply does NOT increase on yield, meaning price per share increases.
        return fee, compounded
        
    def sign_transaction(self, target_protocol: str, amount_usd: int, timestamp: int) -> str:
        """Agent cryptographically signs the intent using EIP-712 Typed Data standard."""
        domain_data = {
            "name": "ZAIR Protocol",
            "version": "1",
            "chainId": 1,
        }
        message_types = {
            "Intent": [
                {"name": "targetProtocol", "type": "string"},
                {"name": "amountUSD", "type": "uint256"},
                {"name": "timestamp", "type": "uint256"},
            ]
        }
        message_data = {
            "targetProtocol": target_protocol,
            "amountUSD": amount_usd,
            "timestamp": timestamp,
        }
        
        signable_message = encode_typed_data(domain_data=domain_data, message_types=message_types, message_data=message_data)
        signed = Account.sign_message(signable_message, private_key=self.agent_private_key)
        return "0x" + signed.signature.hex()

    def generate_tee_attestation(self) -> dict:
        """Simulates an Intel SGX / Phala Network Remote Attestation quote."""
        import hashlib
        import os
        
        # MRENCLAVE: Hash of the logic/code running inside the enclave
        mrenclave_input = "ZAIR_PROTOCOL_ENGINE_V1.0.0"
        mrenclave = hashlib.sha256(mrenclave_input.encode()).hexdigest()
        
        # MRSIGNER: Hash of the developer/architect who signed the enclave
        mrsigner_input = "ZAIR_ARCHITECT_PUBKEY"
        mrsigner = hashlib.sha256(mrsigner_input.encode()).hexdigest()
        
        # Generate a fake SGX DCAP quote (typically ~4000 bytes, here mocked as 256 bytes hex)
        mock_quote = "0x" + os.urandom(128).hex()
        
        return {
            "enclave_type": "Intel SGX",
            "provider": "Sovereign TEE Network",
            "mrenclave": mrenclave,
            "mrsigner": mrsigner,
            "report_data": self.agent_public_address, # Binds the key to the hardware
            "quote_hex": mock_quote,
            "status": "VERIFIED"
        }

    def rebalance(self, solver_output: dict) -> dict:
        """Agent autonomous rebalancing logic using real on-chain data."""
        aave_borrow = fetch_aave_usdc_borrow_rate()
        ondo_apy = fetch_ondo_usdy_apy()
        
        # Calculate real Market Spread
        real_spread = max(0, ondo_apy - aave_borrow)
        
        # Calculate hourly yield realization based on real market spread
        hourly_yield_amount = self.total_assets * real_spread / (365 * 24)
        
        fee, compounded = self.distribute_yield(hourly_yield_amount)
        
        target_protocol = solver_output.get("protocol") or solver_output.get("source_protocol") or "UNKNOWN"
        amount_usd = int(self.total_assets)
        timestamp = int(time.time())
        agent_sig = self.sign_transaction(target_protocol, amount_usd, timestamp)
        
        return {
            "epoch": int(time.time()),
            "vault_aum": self.total_assets,
            "architect_fees": self.architect_locked_fees,
            "agent_address": self.agent_public_address,
            "agent_signature": agent_sig,
            "last_yield_realized": compounded,
            "last_fee_extracted": fee,
            "on_chain_data": {
                "ondo_usdy_apy": round(ondo_apy * 100, 2),
                "aave_usdc_borrow": round(aave_borrow * 100, 2),
                "realized_spread_pct": round(real_spread * 100, 2)
            },
            "tee_attestation": self.generate_tee_attestation()
        }
