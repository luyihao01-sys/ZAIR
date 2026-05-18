# Zair Protocol Integration Guide

## 🎯 Overview

This guide explains how to integrate real-world AI inference (Ollama/vLLM) and Ethereum-based EIP-712 cryptographic signing into the Zair Protocol mining and validation system.

---

## 📋 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ZAIR PROTOCOL NETWORK                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────┐          ┌──────────────────────┐  │
│  │   MINING NODE        │          │   VALIDATOR SERVER   │  │
│  │  (zair-miner)        │          │ (zair-validator)     │  │
│  │                      │          │                      │  │
│  │ 1. Ollama AI         │─────────▶│ 1. Verify EIP-712    │  │
│  │    Inference ──────┐ │          │    Signature         │  │
│  │                    │ │          │                      │  │
│  │ 2. EIP-712         │ │          │ 2. Aggregate Risk    │  │
│  │    Signing ────────┤ │          │    Vectors           │  │
│  │                    │ │          │                      │  │
│  │ 3. Submit to API ◀─┘ │          │ 3. Distribute PoA    │  │
│  │    (/submit_      │  │          │    Rewards           │  │
│  │     inference)    │  │          │                      │  │
│  └──────────────────────┘          │ 4. Record Training   │  │
│         (Multiple)                  │    Data              │  │
│                                     └──────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **Ollama** (for local AI inference)
3. **Ethereum wallet** (for private key)

### Setup

#### 1. Install Ollama

```bash
# macOS
brew install ollama

# Ubuntu
curl https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai
```

#### 2. Download and Run a Model

```bash
# Start Ollama daemon
ollama serve

# In another terminal, pull a model
ollama pull llama3
# Or: ollama pull hermes

# List available models
ollama list
```

Ollama will run at `http://localhost:11434` by default.

#### 3. Generate an Ethereum Private Key

**Option A: Using web3.py**
```python
from eth_account import Account
account = Account.create()
print(account.key.hex())      # Private key
print(account.address)         # Public address
```

**Option B: Use existing MetaMask key**
- Export from MetaMask > Settings > Security & Privacy > Export Account
- **⚠️ NEVER share private keys! Only use for testing!**

#### 4. Configure Environment

**For Miner:**
```bash
cd zair-miner
cp .env.example .env

# Edit .env and set:
ETHEREUM_PRIVATE_KEY=0x1234567890abcdef...
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3
VALIDATOR_URL=http://localhost:8001
```

**For Validator:**
```bash
cd zair-validator
cp .env.example .env

# Edit .env and set:
NETWORK_CHAIN_ID=1
VALIDATOR_PORT=8001
```

#### 5. Install Dependencies

```bash
# Miner
cd zair-miner
pip install -r requirements.txt

# Validator
cd zair-validator
pip install -r requirements.txt
```

---

## 🤖 Real AI Inference (Ollama)

### How It Works

1. **Miner receives asset data** (legal risk, liquidity, yield, etc.)
2. **Constructs prompt** with structured RWA information
3. **Calls Ollama API** to get risk assessment from language model
4. **Parses JSON response** with risk scores (0-100 for each dimension)
5. **Validates and normalizes** the response

### API Call to Ollama

```python
import requests
import json
import re

def call_ollama(asset_data):
    """Call Ollama for risk assessment"""
    
    prompt = f"""Analyze this RWA and provide risk assessment in JSON:

Asset Data:
{json.dumps(asset_data, indent=2)}

Return ONLY valid JSON:
{{
  "legal_risk": <0-100>,
  "liquidity_risk": <0-100>,
  "smart_contract_risk": <0-100>,
  "counterparty_risk": <0-100>,
  "yield_sustainability": <0-100>
}}"""
    
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False,
            "temperature": 0.3
        },
        timeout=60
    )
    
    # Extract JSON from response
    text = response.json()["response"]
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    return json.loads(json_match.group())
```

### Testing Ollama

```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "prompt": "What is the composite risk of a real estate fund?",
    "stream": false,
    "temperature": 0.3
  }'
```

---

## 🔐 EIP-712 Cryptographic Signing

### What is EIP-712?

**EIP-712** is an Ethereum standard for signing structured data. It ensures:
- Data **hasn't been tampered with**
- Signer's **identity is verified**
- **No replay attacks** across chains

### How Zair Uses EIP-712

```
Miner creates Risk Vector
        ↓
Hash using EIP-712 domain (chain-specific)
        ↓
Sign with private key
        ↓
Send to Validator with signature + public address
        ↓
Validator recovers signer's address from signature
        ↓
Verify recovered address matches claimed address
        ↓
Accept/Reject vector
```

### Signature Generation

```python
from eth_account import Account
from eth_account.messages import encode_structured_data

def sign_risk_vector(vector, private_key):
    """Sign a risk vector with EIP-712"""
    
    account = Account.from_key(private_key)
    
    # EIP-712 domain
    domain = {
        "name": "Zair Protocol",
        "version": "1",
        "chainId": 1,  # Ethereum mainnet
        "verifyingContract": "0x0000000000000000000000000000000000000000"
    }
    
    # Message types
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
    
    # Create message
    message = {
        "types": types,
        "primaryType": "RiskVector",
        "domain": domain,
        "message": {
            "node_name": vector["node_name"],
            "asset_id": vector["asset_id"],
            "composite_risk_score": int(vector["composite_risk_score"]),
            "confidence_level": int(vector["confidence_level"]),
            "timestamp": vector["timestamp"]
        }
    }
    
    # Sign
    encoded = encode_structured_data(message)
    signed = account.sign_message(encoded)
    
    return {
        "signature": signed.signature.hex(),
        "signer_address": account.address
    }
```

### Signature Verification (Validator)

```python
from eth_account import Account
from eth_account.messages import encode_structured_data

def verify_signature(vector_data, signature, claimed_signer):
    """Verify EIP-712 signature"""
    
    # Recreate the exact message that was signed
    message = {
        "types": {...},  # Same types as above
        "primaryType": "RiskVector",
        "domain": {...},  # Same domain as above
        "message": {
            "node_name": vector_data["node_name"],
            "asset_id": vector_data["asset_id"],
            "composite_risk_score": int(vector_data["composite_risk_score"]),
            "confidence_level": int(vector_data["confidence_level"]),
            "timestamp": vector_data["timestamp"]
        }
    }
    
    # Recover signer's address from signature
    encoded = encode_structured_data(message)
    recovered_address = Account.recover_message(encoded, signature=signature)
    
    # Compare with claimed address
    return recovered_address.lower() == claimed_signer.lower()
```

---

## 📤 API Integration

### Endpoint: POST /submit_inference

**Request:**
```json
{
  "vector": {
    "node_name": "Node_Dubai",
    "asset_id": "RWA-001",
    "timestamp": "2026-05-18T12:34:56Z",
    "legal_risk": 35.5,
    "liquidity_risk": 42.0,
    "smart_contract_risk": 28.5,
    "counterparty_risk": 31.0,
    "yield_sustainability": 75.5,
    "composite_risk_score": 38.2,
    "confidence_level": 82.5,
    "regional_sentiment": "neutral",
    "local_data_signals": {...}
  },
  "signature": "0x1234567890abcdef...",
  "signer_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f42e",
  "submission_time": "2026-05-18T12:34:57Z"
}
```

**Response (202 Accepted):**
```json
{
  "status": "accepted",
  "message": "Risk vector received and queued for consensus aggregation",
  "asset_id": "RWA-001",
  "node_name": "Node_Dubai",
  "timestamp": "2026-05-18T12:34:57Z"
}
```

**Response (401 Unauthorized - Invalid Signature):**
```json
{
  "status": "error",
  "message": "Invalid or fraudulent signature",
  "timestamp": "2026-05-18T12:34:57Z"
}
```

---

## 🧪 Testing

### Test Integration Script

Run the comprehensive test:

```bash
python test_integration.py
```

This script:
1. ✅ Tests Ollama connection and AI inference
2. ✅ Generates EIP-712 signature
3. ✅ Creates submission payload
4. ✅ Submits to validator API (if running)
5. ✅ Validates entire flow

### Manual Testing

**Start Ollama:**
```bash
ollama serve
ollama pull llama3
```

**Start Validator:**
```bash
cd zair-validator
python -m uvicorn src.api:app --reload --port 8001
```

**Start Miner:**
```bash
cd zair-miner
python src/miner.py --node-name Node_Dubai --region MEA --mode auto
```

**Test with curl:**
```bash
# Health check
curl http://localhost:8001/health

# Get leaderboard
curl http://localhost:8001/leaderboard?top_n=5

# Get network status
curl http://localhost:8001/network_status
```

---

## 🔍 Debugging

### Ollama Issues

**Error: "Connection refused"**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

**Error: "Model not found"**
```bash
# List available models
ollama list

# Download if missing
ollama pull llama3
```

### Signature Issues

**"Invalid signature"**
- Ensure private key format is correct (0x prefix)
- Verify key hasn't been modified
- Check domain and types match exactly

**"Address mismatch"**
- Ensure you're signing with the correct private key
- Verify claimed_signer matches derived public address
- Check for case sensitivity issues

### Validator Issues

**"Vector not accepted"**
- Check signature is valid
- Verify EIP-712 message structure
- Check all required fields are present
- Ensure timestamp is ISO 8601 format

---

## 📊 Consensus Aggregation

### How It Works

```
5 Miners submit vectors for same asset:
  Node_Dubai:    composite_risk=38.2, confidence=82.5
  Node_Singapore: composite_risk=39.1, confidence=85.0
  Node_London:   composite_risk=37.9, confidence=80.0
  Node_NewYork:  composite_risk=40.5, confidence=83.0
  Node_Tokyo:    composite_risk=38.8, confidence=81.5
        ↓
Weighted Average (by reputation/tokens):
  Consensus Risk = 38.8/100
  Consensus Confidence = 82.5%
  Consensus Sentiment = NEUTRAL
        ↓
Reward Distribution:
  Node_Dubai:    accuracy=94.3% → 100 PHI tokens
  Node_Singapore: accuracy=95.8% → 100 PHI tokens
  Node_London:   accuracy=93.1% → 75 PHI tokens
  Node_NewYork:  accuracy=91.5% → 75 PHI tokens
  Node_Tokyo:    accuracy=94.0% → 100 PHI tokens
```

---

## 🎓 Production Checklist

Before going live:

- [ ] **Ollama**
  - [ ] Running on stable server (not localhost)
  - [ ] Model size adequate for latency requirements
  - [ ] Automatic restart on failure
  - [ ] Monitoring/alerting configured

- [ ] **Private Keys**
  - [ ] Stored in secure .env files
  - [ ] Never committed to git
  - [ ] Rotated regularly
  - [ ] Backed up securely

- [ ] **Validator API**
  - [ ] HTTPS enabled (TLS/SSL)
  - [ ] Rate limiting configured
  - [ ] Request validation strict
  - [ ] Monitoring/logging enabled
  - [ ] Database backups automated

- [ ] **Signature Verification**
  - [ ] Domain and chain ID correct
  - [ ] Message types immutable
  - [ ] Recovery always verified
  - [ ] No replay attack vectors

- [ ] **Consensus**
  - [ ] Reputation system audited
  - [ ] Reward distribution fair
  - [ ] Sybil attack prevention
  - [ ] Consensus threshold appropriate

---

## 📚 Resources

- [EIP-712 Specification](https://eips.ethereum.org/EIPS/eip-712)
- [eth-account Documentation](https://eth-account.readthedocs.io)
- [Ollama Documentation](https://ollama.ai)
- [Zair Protocol Whitepaper](./WHITEPAPER.md)

---

## 🤝 Support

- **Issues:** https://github.com/zairprotocol/validator/issues
- **Discord:** https://discord.gg/zairprotocol
- **Email:** support@zairprotocol.com

---

## 📄 License

Apache 2.0 - See LICENSE file
