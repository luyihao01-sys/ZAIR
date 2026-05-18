"""
🐝 Zair Miner — Local Client for Federated Risk Intelligence Network

Each participant runs this to:
1. Subscribe to global RWA assets
2. Run LOCAL inference on regional data
3. Submit Risk Vectors to validator
4. Earn PHI tokens based on accuracy (Proof of Alpha)
5. Participate in decentralized governance

Usage:
    python miner.py --node-name Node_Dubai --region MEA --mode auto
"""

import asyncio
import json
import requests
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import random
from enum import Enum
import os
from dotenv import load_dotenv
import ollama
from eth_account import Account
from eth_account.messages import encode_structured_data
from eth_typing import HexStr
from web3 import Web3

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RegionType(Enum):
    """Supported regions for mining nodes"""
    MEA = "Middle East & Africa"
    NAM = "North America"
    APAC = "Asia-Pacific"
    EU = "Europe"
    EA = "East Asia"


class BiasType(Enum):
    """Regional/institutional bias in risk assessment"""
    CONSERVATIVE = "conservative"      # +5-8% to risks
    AGGRESSIVE = "aggressive"          # -5-8% from risks
    BALANCED = "balanced"              # ±0-5% minimal bias
    TECH_FORWARD = "tech_forward"      # Tech-native lens
    REGULATORY = "regulatory_focus"    # Compliance-first


@dataclass
class RiskVector:
    """Local inference output from a mining node"""
    node_name: str
    timestamp: str
    asset_id: str

    # Five-dimensional risk assessment
    legal_risk: float              # 0-100: Legal/regulatory risk
    liquidity_risk: float          # 0-100: Market liquidity risk
    smart_contract_risk: float     # 0-100: Code/audit risk
    counterparty_risk: float       # 0-100: Issuer creditworthiness
    yield_sustainability: float    # 0-100: Yield durability (inverse risk)

    # Metadata
    composite_risk_score: float    # Weighted avg of above
    confidence_level: float        # 0-100: How confident in this assessment
    regional_sentiment: str        # "bullish" / "neutral" / "bearish"
    local_data_signals: Dict       # Regional data signals used


@dataclass
class MinerConfig:
    """Configuration for a mining node"""
    node_name: str
    region: RegionType
    bias: BiasType
    timezone: str
    validator_url: str             # URL of validator server
    data_sources: List[str]        # Regional data sources to subscribe
    auto_submit: bool = True       # Auto-submit after inference
    batch_size: int = 10           # Process N assets per cycle


class EIP712Signer:
    """Handles EIP-712 signing for Risk Vector submissions"""

    def __init__(self):
        private_key = os.getenv("ETHEREUM_PRIVATE_KEY")
        if not private_key:
            raise ValueError("ETHEREUM_PRIVATE_KEY not set in .env file")

        # Ensure private key has 0x prefix
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key

        self.account = Account.from_key(private_key)
        self.address = self.account.address
        logger.info(f"✓ Ethereum account loaded: {self.address}")

    def sign_risk_vector(self, vector: RiskVector) -> str:
        """
        Sign a RiskVector using EIP-712

        Returns the signature as a hex string
        """
        # Prepare the domain for EIP-712
        domain = {
            "name": "Zair Protocol",
            "version": "1",
            "chainId": int(os.getenv("NETWORK_CHAIN_ID", "1")),
            "verifyingContract": "0x0000000000000000000000000000000000000000"  # Placeholder
        }

        # Define the structure types
        types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"}
            ],
            "RiskVector": [
                {"name": "node_name", "type": "string"},
                {"name": "asset_id", "type": "string"},
                {"name": "composite_risk_score", "type": "uint256"},
                {"name": "confidence_level", "type": "uint256"},
                {"name": "timestamp", "type": "string"}
            ]
        }

        # Create the message to sign
        message = {
            "types": types,
            "primaryType": "RiskVector",
            "domain": domain,
            "message": {
                "node_name": vector.node_name,
                "asset_id": vector.asset_id,
                "composite_risk_score": int(vector.composite_risk_score),
                "confidence_level": int(vector.confidence_level),
                "timestamp": vector.timestamp
            }
        }

        try:
            # Encode and sign the message
            encoded = encode_structured_data(message)
            signed_message = self.account.sign_message(encoded)

            logger.info(
                f"✓ Vector signed: {signed_message.signature.hex()[:20]}...")
            return signed_message.signature.hex()

        except Exception as e:
            logger.error(f"Failed to sign vector: {e}")
            raise

    def get_signer_address(self) -> str:
        """Return the signer's Ethereum address"""
        return self.address


class LocalInferenceEngine:
    """Simulates local risk assessment on regional data"""

    def __init__(self, node_name: str, region: RegionType, bias: BiasType):
        self.node_name = node_name
        self.region = region
        self.bias = bias
        self.inference_count = 0
        self.base_risk_cache = {}

    def run_inference(self, asset_id: str, asset_data: Dict[str, Any]) -> RiskVector:
        """
        Run local inference on RWA asset using Ollama or vLLM

        Args:
            asset_id: Unique identifier for RWA asset
            asset_data: Dict with asset parameters (legal_risk, liquidity_risk, etc.)

        Returns:
            RiskVector with local assessment
        """
        self.inference_count += 1

        # Integrate real-world AI inference using Ollama or vLLM
        try:
            # Example: Replace with actual Ollama/vLLM API call
            inference_result = self._call_ai_inference(asset_data)
            legal_risk = inference_result.get('legal_risk', 50)
            liquidity_risk = inference_result.get('liquidity_risk', 50)
            smart_contract_risk = inference_result.get(
                'smart_contract_risk', 50)
            counterparty_risk = inference_result.get('counterparty_risk', 50)
            yield_sustainability = inference_result.get(
                'yield_sustainability', 50)
        except Exception as e:
            logger.error(f"AI inference failed: {e}")
            # Fallback to default values
            legal_risk = liquidity_risk = smart_contract_risk = counterparty_risk = yield_sustainability = 50

        # Calculate composite risk and confidence
        composite_risk = (
            legal_risk * 0.25 +
            liquidity_risk * 0.20 +
            smart_contract_risk * 0.20 +
            counterparty_risk * 0.20 +
            (100 - yield_sustainability) * 0.15
        )
        confidence = self._calculate_confidence(asset_data)

        # Collect local data signals used
        local_signals = {
            "region": self.region.value,
            "bias_type": self.bias.value,
            "data_sources": self._get_active_data_sources(),
            "inference_id": f"{self.node_name}_{asset_id}_{self.inference_count}"
        }

        return RiskVector(
            node_name=self.node_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            asset_id=asset_id,
            legal_risk=round(legal_risk, 2),
            liquidity_risk=round(liquidity_risk, 2),
            smart_contract_risk=round(smart_contract_risk, 2),
            counterparty_risk=round(counterparty_risk, 2),
            yield_sustainability=round(yield_sustainability, 2),
            composite_risk_score=round(composite_risk, 2),
            confidence_level=round(confidence, 2),
            regional_sentiment="neutral",  # Placeholder
            local_data_signals=local_signals
        )

    def _call_ai_inference(self, asset_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Call external AI inference engine (Ollama/vLLM)

        Sends asset data to local Ollama instance to get real risk assessment
        """
        try:
            ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            model_name = os.getenv("OLLAMA_MODEL", "llama3")

            # Prepare prompt for the model
            asset_summary = json.dumps(asset_data, indent=2)
            prompt = f"""Analyze this RWA (Real World Asset) and provide risk assessment in JSON format.

Asset Data:
{asset_summary}

Provide your assessment as a valid JSON object with exactly these fields (no markdown, just JSON):
{{
  "legal_risk": <0-100>,
  "liquidity_risk": <0-100>,
  "smart_contract_risk": <0-100>,
  "counterparty_risk": <0-100>,
  "yield_sustainability": <0-100>
}}

Base your assessment on:
1. Legal compliance and regulatory status
2. Market liquidity conditions
3. Code audit and smart contract security
4. Issuer creditworthiness
5. Sustainability of promised yields

Return ONLY valid JSON, no other text."""

            # Call Ollama via HTTP
            response = requests.post(
                f"{ollama_host}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3  # Lower temperature for more consistent results
                },
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"Ollama error: {response.status_code}")
                raise Exception(f"Ollama API error: {response.status_code}")

            # Parse response
            result = response.json()
            generated_text = result.get("response", "")

            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
            if not json_match:
                logger.error(
                    f"Could not find JSON in Ollama response: {generated_text}")
                raise Exception("Invalid Ollama response format")

            risk_assessment = json.loads(json_match.group())

            # Validate and normalize values
            validated = {
                "legal_risk": max(0, min(100, float(risk_assessment.get("legal_risk", 50)))),
                "liquidity_risk": max(0, min(100, float(risk_assessment.get("liquidity_risk", 50)))),
                "smart_contract_risk": max(0, min(100, float(risk_assessment.get("smart_contract_risk", 50)))),
                "counterparty_risk": max(0, min(100, float(risk_assessment.get("counterparty_risk", 50)))),
                "yield_sustainability": max(0, min(100, float(risk_assessment.get("yield_sustainability", 50))))
            }

            logger.info(f"✓ Ollama inference completed: {validated}")
            return validated

        except Exception as e:
            logger.error(f"❌ Ollama inference failed: {e}")
            # Fallback: return neutral assessment
            return {
                "legal_risk": 50,
                "liquidity_risk": 50,
                "smart_contract_risk": 50,
                "counterparty_risk": 50,
                "yield_sustainability": 50
            }

    def _get_bias_adjustment(self) -> float:
        """Regional bias adjustment to risk assessment"""
        bias_map = {
            # More risk-averse
            BiasType.CONSERVATIVE: random.uniform(5, 8),
            # More risk-taking
            BiasType.AGGRESSIVE: random.uniform(-8, -5),
            BiasType.BALANCED: random.uniform(-3, 3),         # Neutral
            BiasType.TECH_FORWARD: random.uniform(-2, 2),     # Tech-friendly
            BiasType.REGULATORY: random.uniform(
                3, 6)         # Compliance-focused
        }
        return bias_map.get(self.bias, 0)

    def _assess_regional_sentiment(self, asset_id: str) -> str:
        """Assess regional sentiment based on available data"""
        # Simulated sentiment from regional market data
        sentiment_dist = {
            "bullish": 0.45,
            "neutral": 0.35,
            "bearish": 0.20
        }
        return random.choices(
            list(sentiment_dist.keys()),
            weights=list(sentiment_dist.values()),
            k=1
        )[0]

    def _calculate_confidence(self, asset_data: Dict) -> float:
        """Calculate confidence based on data completeness"""
        required_fields = [
            'legal_risk', 'liquidity_risk', 'smart_contract_risk',
            'counterparty_risk', 'yield_sustainability'
        ]
        available = sum(1 for f in required_fields if f in asset_data)
        base_confidence = (available / len(required_fields)) * 100

        # Add randomness representing data source lag
        return max(50, base_confidence + random.uniform(-10, 10))

    def _get_active_data_sources(self) -> List[str]:
        """Return regional data sources being used"""
        sources_map = {
            RegionType.MEA: ["UAE_Legal_Docs", "GCC_Yield_Data", "Shariah_Compliance"],
            RegionType.NAM: ["SEC_Filings", "US_Market_Sentiment", "Treasury_Yields"],
            RegionType.APAC: ["Crypto_Sentiment", "RWA_Adoption_Metrics", "Singapore_MAS"],
            RegionType.EU: ["MiCA_Compliance", "ESG_Metrics", "ECB_Rates"],
            RegionType.EA: ["Japan_DeFi",
                            "Institutional_Flows", "Bank_Sentiment"]
        }
        return sources_map.get(self.region, [])


class MinerClient:
    """Main mining client that manages inference, submission, and rewards"""

    def __init__(self, config: MinerConfig):
        self.config = config
        self.inference_engine = LocalInferenceEngine(
            config.node_name, config.region, config.bias
        )
        self.submitted_vectors: List[RiskVector] = []
        self.earned_tokens: int = 0
        self.accuracy_history: List[float] = []
        self.last_submission_time: Optional[datetime] = None

    async def start(self):
        """Start the mining client"""
        logger.info(f"🐝 Starting Zair Miner: {self.config.node_name}")
        logger.info(f"  Region: {self.config.region.value}")
        logger.info(f"  Bias: {self.config.bias.value}")
        logger.info(f"  Validator: {self.config.validator_url}")

        # Subscribe to asset stream
        while True:
            try:
                # In production: subscribe to WebSocket stream of new RWA assets
                # For now: simulate by polling validator
                assets = await self._fetch_pending_assets()

                if assets:
                    logger.info(f"📊 Processing {len(assets)} assets...")
                    for asset in assets:
                        await self._process_asset(asset)

                # Wait before next cycle (in production: real-time via WebSocket)
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"❌ Error in mining cycle: {e}")
                await asyncio.sleep(60)

    async def _fetch_pending_assets(self) -> List[Dict]:
        """Fetch pending RWA assets from validator"""
        try:
            # TODO: Connect to validator API endpoint
            # response = requests.get(
            #     f"{self.config.validator_url}/api/pending-assets",
            #     params={"batch_size": self.config.batch_size}
            # )
            # return response.json() if response.ok else []

            # Simulation
            return []

        except Exception as e:
            logger.warning(f"Could not fetch assets from validator: {e}")
            return []

    async def _process_asset(self, asset: Dict[str, Any]):
        """Process single RWA asset through inference engine"""
        try:
            asset_id = asset.get('asset_id')
            if not isinstance(asset_id, str):
                raise ValueError(
                    "Invalid asset_id: must be a non-empty string")

            logger.info(f"  → Inferencing {asset_id}...")

            # Ensure asset data is passed as Dict[str, Any]
            risk_vector = self.inference_engine.run_inference(asset_id, asset)
            self.submitted_vectors.append(risk_vector)

            # Auto-submit to validator
            if self.config.auto_submit:
                await self._submit_vector(risk_vector)

            logger.info(
                f"    ✓ Vector submitted: {risk_vector.composite_risk_score}/100")

        except Exception as e:
            logger.error(f"  ✗ Failed to process {asset.get('asset_id')}: {e}")

    async def _submit_vector(self, vector: RiskVector):
        """Submit Risk Vector to validator for aggregation with EIP-712 signature"""
        try:
            # Sign the vector with EIP-712
            signer = EIP712Signer()
            signature = signer.sign_risk_vector(vector)

            # Convert dataclass to dict for JSON serialization
            vector_dict = asdict(vector)

            # Create submission payload with signature
            submission = {
                "vector": vector_dict,
                "signature": signature,
                "signer_address": signer.get_signer_address(),
                "submission_time": datetime.now(timezone.utc).isoformat()
            }

            # Submit to validator
            validator_url = self.config.validator_url
            try:
                response = requests.post(
                    f"{validator_url}/submit_inference",
                    json=submission,
                    timeout=10,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    logger.info(
                        f"✓ Vector submitted successfully with signature")
                    self.last_submission_time = datetime.now(timezone.utc)
                else:
                    logger.error(
                        f"Failed to submit vector: {response.status_code} - {response.text}")

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Could not reach validator at {validator_url}: {e}")
                logger.debug(
                    f"[OFFLINE] Would submit: {json.dumps(submission, indent=2)}")
                self.last_submission_time = datetime.now(timezone.utc)

        except Exception as e:
            logger.error(f"Failed to submit vector: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get miner statistics"""
        return {
            "node_name": self.config.node_name,
            "region": self.config.region.value,
            "inferences": self.inference_engine.inference_count,
            "vectors_submitted": len(self.submitted_vectors),
            "earned_tokens": self.earned_tokens,
            "accuracy": sum(self.accuracy_history) / len(self.accuracy_history) if self.accuracy_history else 0,
            "last_submission": self.last_submission_time.isoformat() if self.last_submission_time else None
        }


def main():
    """Demo: Local miner running inference"""

    # Create miner configuration
    config = MinerConfig(
        node_name="Node_Dubai",
        region=RegionType.MEA,
        bias=BiasType.CONSERVATIVE,
        timezone="GST",
        validator_url="http://localhost:8001",
        data_sources=["UAE_Legal_Docs", "GCC_Yield_Data"],
        auto_submit=True,
        batch_size=10
    )

    # Create miner client
    miner = MinerClient(config)

    # Demo: Run inference on sample asset
    logger.info("=" * 60)
    logger.info("🐝 ZAIR MINER — LOCAL INFERENCE DEMO")
    logger.info("=" * 60)

    sample_asset = {
        "asset_id": "RWA001",
        "asset_name": "MakerDAO Real Estate Fund",
        "legal_risk": 35,
        "liquidity_risk": 40,
        "smart_contract_risk": 30,
        "counterparty_risk": 25,
        "yield_sustainability": 70
    }

    # Run inference 5 times to show variation
    for i in range(5):
        vector = miner.inference_engine.run_inference(
            sample_asset["asset_id"],
            sample_asset
        )

        logger.info(f"\n[Inference {i+1}]")
        logger.info(f"  Asset: {vector.asset_id}")
        logger.info(f"  Legal Risk: {vector.legal_risk}/100")
        logger.info(f"  Liquidity Risk: {vector.liquidity_risk}/100")
        logger.info(f"  Smart Contract Risk: {vector.smart_contract_risk}/100")
        logger.info(f"  Counterparty Risk: {vector.counterparty_risk}/100")
        logger.info(
            f"  Yield Sustainability: {vector.yield_sustainability}/100")
        logger.info(f"  → Composite: {vector.composite_risk_score}/100")
        logger.info(f"  → Confidence: {vector.confidence_level}%")
        logger.info(f"  → Sentiment: {vector.regional_sentiment}")

    logger.info("\n" + "=" * 60)
    logger.info("✓ Demo complete!")
    logger.info("=" * 60)

    # Show stats
    logger.info(f"\nMiner Stats:")
    stats = miner.get_stats()
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")


if __name__ == "__main__":
    main()
