"""
⚖️ Zair Validator API — FastAPI Server for Risk Vector Validation & Aggregation

Endpoints:
- POST /submit_inference: Miners submit risk vectors with EIP-712 signatures
- GET /consensus/{asset_id}: Retrieve consensus for an asset
- GET /leaderboard: Get node leaderboard
- GET /network_status: Get current network status
"""

from web3 import Web3
from eth_keys.exceptions import BadSignature
from eth_account import Account
from eth_account.messages import encode_defunct

from .validator import (
    HiveMindValidator, SubmittedVector, ConsensusResult,
    PoAReward
)
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import logging
import json
import os
from dotenv import load_dotenv

# Import validator logic
import sys
sys.path.insert(0, os.path.dirname(__file__))

# Ethereum signature verification

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Zair Protocol Validator API",
    description="Consensus aggregation and PoA reward distribution for RWA risk assessment",
    version="1.0.0"
)

# Initialize validator
validator = HiveMindValidator()


# ============================================================================
# Pydantic Models for API Requests/Responses
# ============================================================================

class LocalDataSignals(BaseModel):
    """Local data signals from a mining node"""
    region: str
    bias_type: str
    data_sources: List[str]
    inference_id: str


class RiskVectorPayload(BaseModel):
    """Risk vector submitted by a miner"""
    node_name: str
    timestamp: str
    asset_id: str
    legal_risk: float
    liquidity_risk: float
    smart_contract_risk: float
    counterparty_risk: float
    yield_sustainability: float
    composite_risk_score: float
    confidence_level: float
    regional_sentiment: str
    local_data_signals: Dict[str, Any]


class SignedSubmission(BaseModel):
    """Complete signed submission from a miner"""
    vector: RiskVectorPayload
    signature: str = Field(..., description="EIP-712 signature hex string")
    signer_address: str = Field(...,
                                description="Ethereum address of the signer")
    submission_time: str


class SubmissionResponse(BaseModel):
    """Response to a vector submission"""
    status: str
    message: str
    asset_id: str
    node_name: str
    timestamp: str


class ConsensusResponse(BaseModel):
    """Consensus result for an asset"""
    asset_id: str
    consensus_composite_risk: float
    consensus_confidence: float
    consensus_sentiment: str
    num_nodes_participated: int
    is_safe: bool


class LeaderboardEntry(BaseModel):
    """Leaderboard entry for a node"""
    rank: int
    node_name: str
    cumulative_tokens: float
    accuracy_percentage: float
    total_predictions: int


# ============================================================================
# Signature Verification
# ============================================================================

class EIP712Verifier:
    """Verify EIP-712 signatures from miners"""

    @staticmethod
    def verify_signature(
        vector_data: Dict[str, Any],
        signature: str,
        claimed_signer: str
    ) -> bool:
        """
        Verify that a signature was created by the claimed signer

        Args:
            vector_data: The data that was signed
            signature: The EIP-712 signature hex string
            claimed_signer: The address that claims to have signed

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Prepare the domain for EIP-712
            domain = {
                "name": "Zair Protocol",
                "version": "1",
                "chainId": int(os.getenv("NETWORK_CHAIN_ID", "1")),
                "verifyingContract": "0x0000000000000000000000000000000000000000"
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

            # Create the message in JSON format
            message_json = json.dumps({
                "node_name": vector_data.get("node_name"),
                "asset_id": vector_data.get("asset_id"),
                "composite_risk_score": int(vector_data.get("composite_risk_score", 0)),
                "confidence_level": int(vector_data.get("confidence_level", 0)),
                "timestamp": vector_data.get("timestamp")
            }, sort_keys=True)

            # Encode as EIP-191 message
            encoded = encode_defunct(text=message_json)
            recovered_address = Account.recover_message(
                encoded, signature=signature)

            # Normalize addresses for comparison (case-insensitive)
            claimed_normalized = Web3.to_checksum_address(claimed_signer)
            recovered_normalized = Web3.to_checksum_address(recovered_address)

            is_valid = claimed_normalized.lower() == recovered_normalized.lower()

            logger.info(f"Signature verification: {is_valid}")
            logger.info(f"  Claimed: {claimed_normalized}")
            logger.info(f"  Recovered: {recovered_normalized}")

            return is_valid

        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False


# ============================================================================
# API Endpoints
# ============================================================================

@app.post(
    "/submit_inference",
    response_model=SubmissionResponse,
    summary="Submit risk vector with EIP-712 signature",
    status_code=202
)
async def submit_inference(submission: SignedSubmission) -> SubmissionResponse:
    """
    Submit a Risk Vector to the Validator with EIP-712 signature.

    The signature must be valid and match the provided signer address.
    The vector data will be queued for consensus aggregation.

    **Request Body:**
    - `vector`: RiskVectorPayload with all risk scores and metadata
    - `signature`: EIP-712 compliant signature hex string
    - `signer_address`: Ethereum address of the signing miner
    - `submission_time`: ISO 8601 timestamp

    **Response:**
    - `status`: "accepted" if signature is valid, "error" otherwise
    - `message`: Details about the submission
    - `asset_id`: The asset being assessed
    - `node_name`: The miner node name
    """
    try:
        logger.info(f"📥 Received submission from {submission.signer_address}")

        # Verify EIP-712 signature
        vector_dict = submission.vector.dict()
        is_valid = EIP712Verifier.verify_signature(
            vector_dict,
            submission.signature,
            submission.signer_address
        )

        if not is_valid:
            logger.error(
                f"❌ Invalid signature from {submission.signer_address}")
            raise HTTPException(
                status_code=401,
                detail="Invalid or fraudulent signature"
            )

        # Create SubmittedVector for aggregation
        submitted_vector_dict = vector_dict.copy()
        submitted_vector_dict["full_vector"] = vector_dict

        # Receive vector (queuing for aggregation)
        result = await validator.receive_vector(submitted_vector_dict)

        logger.info(f"✓ Vector accepted for {submission.vector.asset_id}")

        return SubmissionResponse(
            status="accepted",
            message=f"Risk vector received and queued for consensus aggregation",
            asset_id=submission.vector.asset_id,
            node_name=submission.vector.node_name,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing submission: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing submission: {str(e)}"
        )


@app.post(
    "/process_asset",
    summary="Process an asset and aggregate consensus",
    response_model=Dict
)
async def process_asset(
    asset_id: str,
    asset_name: str,
    actual_stability: bool
) -> Dict:
    """
    Process all vectors for an asset and compute consensus.

    This endpoint:
    1. Aggregates vectors from all miners
    2. Computes weighted consensus
    3. Verifies accuracy against ground truth
    4. Distributes PoA rewards
    5. Records training data

    **Query Parameters:**
    - `asset_id`: Asset identifier
    - `asset_name`: Human-readable asset name
    - `actual_stability`: Ground truth outcome (true=safe, false=risky)
    """
    try:
        logger.info(f"🔄 Processing asset {asset_id}...")

        result = await validator.process_asset(asset_id, asset_name, actual_stability)

        logger.info(f"✓ Asset processing complete for {asset_id}")
        return result

    except Exception as e:
        logger.error(f"Error processing asset: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing asset: {str(e)}"
        )


@app.get(
    "/network_status",
    summary="Get current network status",
    response_model=Dict
)
async def get_network_status() -> Dict:
    """
    Retrieve current network statistics.

    Returns:
    - Number of registered miners
    - Total tokens in circulation
    - Number of assets processed
    - Training dataset size
    """
    try:
        status = validator.get_network_status()
        return status
    except Exception as e:
        logger.error(f"Error getting network status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving network status: {str(e)}"
        )


@app.get(
    "/leaderboard",
    summary="Get miner leaderboard",
    response_model=List[LeaderboardEntry]
)
async def get_leaderboard(top_n: int = 10) -> List[Dict]:
    """
    Retrieve the top miners by reputation (cumulative tokens).

    **Query Parameters:**
    - `top_n`: Number of top miners to return (default: 10)

    Returns list of top miners with their stats and accuracy.
    """
    try:
        leaderboard = validator.get_leaderboard(top_n)
        return leaderboard
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving leaderboard: {str(e)}"
        )


@app.get(
    "/consensus/{asset_id}",
    summary="Get consensus for an asset",
    response_model=ConsensusResponse
)
async def get_consensus(asset_id: str) -> Dict:
    """
    Retrieve the consensus result for a specific asset.

    **Path Parameters:**
    - `asset_id`: Asset identifier

    Returns the aggregated consensus and safety assessment.
    """
    try:
        if asset_id not in validator.processed_assets:
            raise HTTPException(
                status_code=404,
                detail=f"No consensus found for asset {asset_id}"
            )

        result = validator.processed_assets[asset_id]
        consensus = result.get("consensus")

        return ConsensusResponse(
            asset_id=consensus["asset_id"],
            consensus_composite_risk=consensus["consensus_composite_risk"],
            consensus_confidence=consensus["consensus_confidence"],
            consensus_sentiment=consensus["consensus_sentiment"],
            num_nodes_participated=consensus["num_nodes_participated"],
            is_safe=consensus["consensus_composite_risk"] < 45.0
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting consensus: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving consensus: {str(e)}"
        )


@app.get("/health", summary="Health check")
async def health_check() -> Dict[str, str]:
    """Check if the validator is running."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with JSON response"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("VALIDATOR_PORT", 8001))
    logger.info(f"Starting Zair Validator API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
