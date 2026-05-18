# Zair Protocol API Specification

## Overview

The Zair Protocol API defines the interface for miners to submit risk assessments and validators to aggregate consensus. All submissions must include **EIP-712 cryptographic signatures** to ensure authenticity and prevent fraud.

**Base URL:** `https://api.zairprotocol.com`  
**Version:** 1.0.0

---

## Core Concepts

### 1. Risk Vector
A **Risk Vector** is the data structure miners submit to express their assessment of an asset's risk profile.

```json
{
  "node_name": "Node_Dubai",
  "timestamp": "2026-05-18T12:34:56Z",
  "asset_id": "RWA-001",
  "legal_risk": 35.5,
  "liquidity_risk": 42.0,
  "smart_contract_risk": 28.5,
  "counterparty_risk": 31.0,
  "yield_sustainability": 75.5,
  "composite_risk_score": 38.2,
  "confidence_level": 82.5,
  "regional_sentiment": "neutral",
  "local_data_signals": {
    "region": "MEA",
    "bias_type": "conservative",
    "data_sources": ["UAE_Legal_Docs", "GCC_Yield_Data"],
    "inference_id": "Node_Dubai_RWA-001_1"
  }
}
```

**Field Definitions:**
- `node_name` (string): Identifier of the mining node
- `timestamp` (ISO 8601): When the inference was generated
- `asset_id` (string): Unique identifier of the RWA asset
- `legal_risk` (0-100): Legal/regulatory compliance risk
- `liquidity_risk` (0-100): Market liquidity risk
- `smart_contract_risk` (0-100): Code audit/smart contract security risk
- `counterparty_risk` (0-100): Issuer creditworthiness risk
- `yield_sustainability` (0-100): Sustainability of promised yields (inverse: higher = better)
- `composite_risk_score` (0-100): Weighted average of all risks
- `confidence_level` (0-100): Miner's confidence in the assessment
- `regional_sentiment` (string): "bullish", "neutral", or "bearish"
- `local_data_signals` (object): Regional data sources and inference metadata

---

## Authentication: EIP-712 Signatures

All vector submissions must include an **EIP-712 compliant signature** to prove ownership and prevent tampering.

### EIP-712 Domain Structure

```json
{
  "name": "Zair Protocol",
  "version": "1",
  "chainId": 1,
  "verifyingContract": "0x0000000000000000000000000000000000000000"
}
```

### EIP-712 Message Structure

```json
{
  "types": {
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
  },
  "primaryType": "RiskVector",
  "domain": {...},
  "message": {
    "node_name": "Node_Dubai",
    "asset_id": "RWA-001",
    "composite_risk_score": 38,
    "confidence_level": 82,
    "timestamp": "2026-05-18T12:34:56Z"
  }
}
```

### Signing Process

1. **Load private key** from environment (`ETHEREUM_PRIVATE_KEY`)
2. **Create the EIP-712 message** structure above
3. **Encode the message** using eth_account
4. **Sign the encoded message** with the private key
5. **Convert signature to hex string** (64 bytes + recovery bit)

**Python Example:**
```python
from eth_account import Account
from eth_account.messages import encode_structured_data

# Load account
private_key = os.getenv("ETHEREUM_PRIVATE_KEY")
account = Account.from_key(private_key)

# Create and sign message
message = {...}  # EIP-712 structure above
encoded = encode_structured_data(message)
signed = account.sign_message(encoded)

signature = signed.signature.hex()  # e.g., "0xabc123..."
signer_address = account.address    # e.g., "0x742d35Cc6634C0532925a3b844Bc9e7595f42e"
```

---

## Endpoints

### 1. POST /submit_inference

**Submit a risk vector to the validator with signature.**

**URL:** `/submit_inference`  
**Method:** `POST`  
**Authentication:** EIP-712 signature validation  
**Status Code:** `202 Accepted` (on success), `400`/`401`/`500` (on error)

#### Request Body

```json
{
  "vector": {
    "node_name": "Node_Dubai",
    "timestamp": "2026-05-18T12:34:56Z",
    "asset_id": "RWA-001",
    "legal_risk": 35.5,
    "liquidity_risk": 42.0,
    "smart_contract_risk": 28.5,
    "counterparty_risk": 31.0,
    "yield_sustainability": 75.5,
    "composite_risk_score": 38.2,
    "confidence_level": 82.5,
    "regional_sentiment": "neutral",
    "local_data_signals": {
      "region": "MEA",
      "bias_type": "conservative",
      "data_sources": ["UAE_Legal_Docs", "GCC_Yield_Data"],
      "inference_id": "Node_Dubai_RWA-001_1"
    }
  },
  "signature": "0x1234567890abcdef...",
  "signer_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f42e",
  "submission_time": "2026-05-18T12:34:57Z"
}
```

#### Response (Success - 202)

```json
{
  "status": "accepted",
  "message": "Risk vector received and queued for consensus aggregation",
  "asset_id": "RWA-001",
  "node_name": "Node_Dubai",
  "timestamp": "2026-05-18T12:34:57Z"
}
```

#### Response (Signature Invalid - 401)

```json
{
  "status": "error",
  "message": "Invalid or fraudulent signature",
  "timestamp": "2026-05-18T12:34:57Z"
}
```

#### Response (Malformed Request - 400)

```json
{
  "status": "error",
  "message": "Missing required fields: signature, signer_address",
  "timestamp": "2026-05-18T12:34:57Z"
}
```

---

### 2. POST /process_asset

**Aggregate vectors for an asset and compute consensus.**

**URL:** `/process_asset`  
**Method:** `POST`  
**Query Parameters:**
- `asset_id` (string, required): Asset identifier
- `asset_name` (string, required): Human-readable asset name
- `actual_stability` (boolean, required): Ground truth outcome

#### Request Example

```
POST /process_asset?asset_id=RWA-001&asset_name=Dubai_Real_Estate_Fund&actual_stability=true
```

#### Response (Success - 200)

```json
{
  "asset_id": "RWA-001",
  "consensus": {
    "asset_id": "RWA-001",
    "timestamp": "2026-05-18T12:35:00Z",
    "consensus_composite_risk": 40.5,
    "consensus_confidence": 81.2,
    "consensus_sentiment": "neutral",
    "num_nodes_participated": 5,
    "is_safe": true
  },
  "num_nodes": 5,
  "node_vectors": [...],
  "rewards": [
    {
      "node_name": "Node_Dubai",
      "asset_id": "RWA-001",
      "predicted_risk": 38.2,
      "consensus_risk": 40.5,
      "accuracy_percentage": 94.3,
      "prediction_correct": true,
      "tokens_mined": 100.0,
      "reward_tier": "high_confidence"
    }
  ],
  "total_tokens_distributed": 450.0,
  "training_data_saved": true
}
```

---

### 3. GET /network_status

**Retrieve current network statistics.**

**URL:** `/network_status`  
**Method:** `GET`

#### Response (Success - 200)

```json
{
  "validators": 1,
  "miners_registered": 12,
  "nodes": [
    {
      "name": "Node_Dubai",
      "cumulative_tokens": 1250.5,
      "predictions": 15
    },
    {
      "name": "Node_Singapore",
      "cumulative_tokens": 980.0,
      "predictions": 12
    }
  ],
  "total_tokens_in_circulation": 8950.0,
  "assets_processed": 34,
  "training_dataset_records": 340
}
```

---

### 4. GET /leaderboard

**Retrieve top miners by reputation.**

**URL:** `/leaderboard`  
**Method:** `GET`  
**Query Parameters:**
- `top_n` (integer, optional, default=10): Number of top miners to return

#### Request Example

```
GET /leaderboard?top_n=5
```

#### Response (Success - 200)

```json
[
  {
    "rank": 1,
    "node_name": "Node_Dubai",
    "cumulative_tokens": 1250.5,
    "accuracy_percentage": 92.3,
    "total_predictions": 15
  },
  {
    "rank": 2,
    "node_name": "Node_Singapore",
    "cumulative_tokens": 980.0,
    "accuracy_percentage": 89.7,
    "total_predictions": 12
  }
]
```

---

### 5. GET /consensus/{asset_id}

**Retrieve consensus result for a specific asset.**

**URL:** `/consensus/{asset_id}`  
**Method:** `GET`  
**Path Parameters:**
- `asset_id` (string): Asset identifier

#### Request Example

```
GET /consensus/RWA-001
```

#### Response (Success - 200)

```json
{
  "asset_id": "RWA-001",
  "consensus_composite_risk": 40.5,
  "consensus_confidence": 81.2,
  "consensus_sentiment": "neutral",
  "num_nodes_participated": 5,
  "is_safe": true
}
```

#### Response (Not Found - 404)

```json
{
  "status": "error",
  "message": "No consensus found for asset RWA-001",
  "timestamp": "2026-05-18T12:35:00Z"
}
```

---

### 6. GET /health

**Health check endpoint.**

**URL:** `/health`  
**Method:** `GET`

#### Response (Success - 200)

```json
{
  "status": "healthy",
  "timestamp": "2026-05-18T12:35:00Z"
}
```

---

## Error Handling

All error responses follow a consistent format:

```json
{
  "status": "error",
  "message": "Description of the error",
  "timestamp": "2026-05-18T12:35:00Z"
}
```

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | GET /consensus/RWA-001 |
| 202 | Accepted (async processing) | POST /submit_inference |
| 400 | Bad Request | Missing required fields |
| 401 | Unauthorized | Invalid EIP-712 signature |
| 404 | Not Found | Asset not found |
| 500 | Internal Server Error | Database connection failed |

---

## Example Integration: Python Miner Client

```python
import requests
from eth_account import Account
from eth_account.messages import encode_structured_data
import json

# Load private key
private_key = "0x1234567890abcdef..."
account = Account.from_key(private_key)

# Create risk vector
vector = {
    "node_name": "Node_Dubai",
    "timestamp": "2026-05-18T12:34:56Z",
    "asset_id": "RWA-001",
    "legal_risk": 35.5,
    "liquidity_risk": 42.0,
    "smart_contract_risk": 28.5,
    "counterparty_risk": 31.0,
    "yield_sustainability": 75.5,
    "composite_risk_score": 38.2,
    "confidence_level": 82.5,
    "regional_sentiment": "neutral",
    "local_data_signals": {...}
}

# Create EIP-712 message
message = {
    "types": {
        "EIP712Domain": [...],
        "RiskVector": [...]
    },
    "primaryType": "RiskVector",
    "domain": {...},
    "message": {
        "node_name": vector["node_name"],
        "asset_id": vector["asset_id"],
        "composite_risk_score": int(vector["composite_risk_score"]),
        "confidence_level": int(vector["confidence_level"]),
        "timestamp": vector["timestamp"]
    }
}

# Sign the message
encoded = encode_structured_data(message)
signed = account.sign_message(encoded)

# Create submission payload
submission = {
    "vector": vector,
    "signature": signed.signature.hex(),
    "signer_address": account.address,
    "submission_time": "2026-05-18T12:34:57Z"
}

# Submit to validator
response = requests.post(
    "https://api.zairprotocol.com/submit_inference",
    json=submission,
    headers={"Content-Type": "application/json"}
)

print(response.json())
```

---

## Rate Limiting & Quotas

- **Submit Inference:** 100 requests/minute per IP
- **Get Consensus:** Unlimited
- **Get Leaderboard:** 10 requests/minute per IP

---

## Changelog

### v1.0.0 (2026-05-18)
- Initial release
- EIP-712 signature support
- Consensus aggregation
- PoA reward distribution

---

## Contact & Support

For integration questions or bug reports:
- **GitHub:** https://github.com/zairprotocol/validator
- **Discord:** https://discord.gg/zairprotocol
- **Email:** support@zairprotocol.com
