# ZAIR: Zenith Autonomous Intent Relay
## Decentralized RWA Risk Intelligence Network

> **Transform Real World Assets from a Trust Problem into a Math Problem**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-testnet-green.svg)](https://github.com/zairprotocol/validator)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![Ethereum](https://img.shields.io/badge/ethereum-EIP--712-purple.svg)](https://eips.ethereum.org/EIPS/eip-712)

---

## 🎯 The Vision

**The Problem:** RWA (Real World Asset) markets are frozen at $2.5T when they should be $100T+. Why? Because risk assessment is *centralized*. You trust one entity to tell you if that Dubai real estate fund is safe. One auditor. One risk model. One point of failure.

**The Solution:** ZAIR democratizes risk intelligence through **federated local AI**. 

Imagine thousands of nodes worldwide, each running their own language models, each assessing the same asset from their regional perspective. They sign their assessments with Ethereum private keys. They submit cryptographically-verified predictions. The validator aggregates their wisdom into mathematical consensus. Accurate predictors earn tokens. Malicious ones get filtered out.

**No gatekeepers. No blackboxes. Pure math. Pure transparency.**

```
Centralized RWA Risk Today:    │    ZAIR Future:
                                │
Auditor (1 entity)             │    10,000 Miners
    ↓                           │         ↓
Risk Report                     │    Local AI Inferences
    ↓                           │         ↓
Price Impact                    │    Cryptographic Consensus
    ↓                           │         ↓
You Pay 10x Premium             │    Fair Market Price
                                │    + Proof of Work
```

---

## ⚡ What Makes ZAIR Different

### 🤖 Federated AI Inference
- Every miner runs their own language model (Ollama, vLLM)
- No centralized model governs risk perception
- Regional bias reveals truth through diversity
- Language models capture nuance that traditional models miss

### 🔐 Cryptographic Accountability
- Every prediction signed with EIP-712 (Ethereum standard)
- Impossible to fake, spam, or manipulate signatures
- Signer address recovered and verified by validator
- Tamper-proof audit trail on-chain

### 🏛️ Meritocratic Consensus
- Voting power = past prediction accuracy (reputation)
- Accurate miners accumulate tokens → higher voting power
- Malicious miners diluted by democratic consensus
- No way to game the system without predicting correctly

### 💰 Proof of Alpha (PoA) Rewards
- Miners earn **PHI tokens** for accurate predictions
- Reward tiers: Perfect (100), High (75), Medium (50), Low (25)
- Tokens liquid and tradeable (future: DEX listing)
- Can stake for validator role in DAO

### 📊 RLHF Training Data Loop
- Every consensus outcome feeds back into model training
- Language models improve with every round
- Creates virtuous cycle: accuracy ↑ → token value ↑ → more miners ↑ → better consensus ↑
- Open-source datasets for community model training

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
```bash
# Check Python version
python --version  # Must be 3.8+

# Install Ollama (macOS/Linux)
curl https://ollama.ai/install.sh | sh

# Windows users: Download from https://ollama.ai
```

### Step 1: Clone & Setup (1 min)
```bash
# Clone the repository
git clone https://github.com/zairprotocol/validator.git
cd validator

# Create Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Verify Ollama is running
curl http://localhost:11434/api/tags  # Should return {"models": [...]}

# If not running, in a new terminal:
ollama serve
```

### Step 2: Start the Validator (1 min)
```bash
# Install validator dependencies
cd zair-validator
pip install -r requirements.txt
cp .env.example .env

# Start the validator server
python -m uvicorn src.api:app --reload --port 8001

# You should see:
# INFO:     Started server process [12345]
# INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Step 3: Start Your First Miner (2 min)
```bash
# In a new terminal
cd zair-miner
pip install -r requirements.txt
cp .env.example .env

# CRITICAL: Generate and add your Ethereum private key
python -c "
from eth_account import Account
account = Account.create()
print(f'Private Key: {account.key.hex()}')
print(f'Address: {account.address}')
print('^ Copy the private key above and paste into .env')
"

# Edit .env and set ETHEREUM_PRIVATE_KEY
nano .env  # (or use your editor)

# Download the AI model
ollama pull llama3

# Start mining
python src/miner.py --node-name MyNode_Dubai --region MEA
```

### Step 4: Submit Your First Cryptographically-Signed Inference (1 min)

Your miner will automatically:
1. ✅ Load your Ethereum private key
2. ✅ Connect to Ollama and run llama3
3. ✅ Analyze a sample RWA asset
4. ✅ Create an EIP-712 signature (proof you created it)
5. ✅ Submit to the validator with signature
6. ✅ Validator verifies your signature and accepts it

Watch the logs:
```
🐝 Starting Zair Miner: MyNode_Dubai
✓ Ethereum account loaded: 0x742d35Cc6634C0532925a3b844Bc9e7595f42e
✓ Connected to Ollama (llama3)
🤖 Calling Ollama for risk assessment...
✓ Ollama inference completed: {'legal_risk': 35, ...}
✓ Message signed successfully
✓ Vector submitted successfully with signature
```

### Step 5: Test the Entire Flow
```bash
# In a new terminal, run the integration test
python test_integration.py

# Output shows:
# [STEP 1] Testing Real AI Inference with Ollama ✓
# [STEP 2] Generating EIP-712 Signature ✓
# [STEP 3] Creating Validator Submission ✓
# [STEP 4] Submitting to Validator API ✓
```

---

## 📊 Real-World Example

### What Happens When You Mine

**You (Miner):**
```bash
python src/miner.py
```

**Behind the scenes:**
```
1. Receive asset: "Dubai Real Estate Fund ($250M)"
   
2. Call Ollama llama3:
   "Analyze this RWA and provide risk assessment..."
   
3. Model outputs:
   {
     "legal_risk": 35,
     "liquidity_risk": 42,
     "smart_contract_risk": 28,
     "counterparty_risk": 31,
     "yield_sustainability": 75
   }
   
4. Calculate composite risk:
   Composite = 35*0.25 + 42*0.20 + 28*0.20 + 31*0.20 + (100-75)*0.15
             = 38.2/100 (SAFE)
   
5. Sign with Ethereum private key (EIP-712):
   signature = sign(payload, private_key)
   signer_address = recover(signature)
   
6. Submit to validator:
   POST /submit_inference {
     "vector": {..., "composite_risk_score": 38.2, ...},
     "signature": "0x1234567890abcdef...",
     "signer_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f42e"
   }
```

**Validator receives:**
```
1. Verify signature is valid for claimed address
   recovered_address = recover_signature(payload, signature)
   assert recovered_address == 0x742d35Cc6634C0532925a3b844Bc9e7595f42e ✓
   
2. Queue vector for aggregation
   
3. Wait for 5+ miners to submit (same asset)
   
4. Compute weighted consensus:
   weight[node] = past_accuracy[node] / sum(all_past_accuracies)
   consensus = Σ(vector[i] * weight[i])
   
5. Compare to ground truth (after asset settles):
   actual_risk = did_asset_default? no → SAFE
   your_prediction = 38.2 < 45 → SAFE ✓ CORRECT!
   
6. Award tokens:
   accuracy = 100 - |38.2 - consensus| = 94.3%
   tier = HIGH_CONFIDENCE
   tokens_earned = 75 PHI
   
7. Update your reputation:
   cumulative_tokens += 75
   (higher tokens = more voting power next round)
```

---

## 🔐 Why Cryptographic Signing Matters

Traditional centralized platforms:
```
You: "My prediction is risk=38"
Platform: "OK, we believe you."
→ Platform can fake predictions, censor miners, manipulate consensus
```

ZAIR with EIP-712:
```
You: "My prediction is risk=38" [SIGNED: 0x1234567890abcdef...]
Validator: 1. Recover who signed this
           2. Check recovered == claimed_address
           3. Impossible to forge (would need your private key)
           4. Impossible to fake (cryptographically proven)
→ Pure math, no trust needed
```

Every single submission is cryptographically verified. Spam attacks = impossible (would need thousands of private keys). Sybil attacks = impossible (reputation = past accuracy, not quantity).

---

## 💰 Tokenomics & Rewards

### PHI Token Economy

| Event | PHI Earned | Requirement |
|-------|-----------|------------|
| Perfect Prediction | 100 PHI | ≥95% accuracy + correct outcome |
| High Confidence | 75 PHI | ≥90% accuracy + correct outcome |
| Medium Confidence | 50 PHI | ≥75% accuracy + correct outcome |
| Low Confidence | 25 PHI | ≥50% accuracy + correct outcome |
| Consensus Miss | 0 PHI | <50% accuracy or wrong outcome |

### Reputation System
```
Total PHI Accumulated = Voting Power for Next Round

Mining Round 1:
  You: 100 accurate predictions → 7,500 PHI
  
Mining Round 2:
  Your voting weight = 7,500 / total_network_tokens
  Higher weight = your vote counts more in consensus
  → Better predictions have more influence
```

### Staking & DAO (Roadmap)
```
Future: Stake PHI tokens to become a Validator
  - Earn transaction fees
  - Participate in governance votes
  - Propose new asset categories
  - Shape protocol evolution
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  ZAIR NETWORK LAYER                       │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────┐      ┌─────────────┐    ┌──────────┐   │
│  │   MINERS    │      │   MINERS    │    │  MINERS  │   │
│  │  (Global)   │      │  (Global)   │    │ (Global) │   │
│  ├─────────────┤      ├─────────────┤    ├──────────┤   │
│  │ Ollama AI   │      │ Ollama AI   │    │Ollama AI │   │
│  │ llama3      │      │ mistral     │    │  hermes  │   │
│  │             │      │             │    │          │   │
│  │ Eth Signing │      │ Eth Signing │    │Eth Sign. │   │
│  └──────┬──────┘      └──────┬──────┘    └────┬─────┘   │
│         │                    │                │         │
│         └────────────────────┼────────────────┘         │
│                              │                          │
│                    HTTP (EIP-712 Signed)               │
│                              │                          │
│              ┌───────────────▼───────────────┐         │
│              │  VALIDATOR SERVER (FastAPI)   │         │
│              ├───────────────────────────────┤         │
│              │ • Verify EIP-712 Signatures   │         │
│              │ • Aggregate Consensus         │         │
│              │ • Verify Accuracy (PoA)       │         │
│              │ • Distribute PHI Rewards      │         │
│              │ • Record Training Data        │         │
│              └───────────┬───────────────────┘         │
│                          │                             │
│          ┌───────────────┼───────────────┐            │
│          ▼               ▼               ▼            │
│      Leaderboard    Consensus Results  RLHF Dataset   │
│                                                        │
└──────────────────────────────────────────────────────────┘
```

---

## � Documentation

- **[API_SPECIFICATION.md](API_SPECIFICATION.md)** - Full OpenAPI spec with EIP-712 signing format
- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - Deep dive on Ollama + Ethereum integration
- **[MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md)** - What changed from mocks to production
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command reference & troubleshooting
- **[openapi.yaml](openapi.yaml)** - OpenAPI 3.0 spec for API clients

---

## 🔥 Key Features Explained

### Real AI, Not Synthetic Data
```python
# Before (Centralized):
risk_score = model.predict(asset)  # Black box, can't verify

# ZAIR (Decentralized):
risk_scores = []
for miner in network:
    score = miner.ollama_llm.analyze(asset)  # Transparent
    signature = sign(score, miner.private_key)  # Verified
    risk_scores.append((score, signature, miner.address))

consensus = weighted_average(risk_scores)  # Math-based
```

### Consensus from Diversity
- 🇦🇪 Dubai Node: Sees Shariah compliance as advantage
- 🇸🇬 Singapore Node: Sees regulatory clarity as strength
- 🇬🇧 London Node: Sees institutional backing as safety
- Result: Consensus captures global perspective

### Tamper-Proof Records
```
Every prediction is permanently associated with:
✓ Miner's Ethereum address
✓ Cryptographic signature (proof of ownership)
✓ Timestamp (when it was made)
✓ Accuracy score (how right they were)
✓ Tokens earned (reward for accuracy)

→ Impossible to fake, edit, or deny
```

---

## 🎯 Use Cases

### 1. **Tokenized Real Estate**
Dubai $10M penthouse → Tokenized → 1M tokens @ $10 each
- ZAIR provides real-time risk consensus
- Price reflects actual risk, not dealer markup
- Liquidity flows to fairly-priced assets

### 2. **Green Bonds Assessment**
Green bond claim: "100% of $500M goes to solar"
- ZAIR miners analyze supply chain → estimate real impact
- Consensus rewards accurate assessments
- Fraudulent green bonds exposed quickly

### 3. **Supply Chain Finance**
Chinese textile factory needs bridge financing
- ZAIR miners analyze factory data + regional economics
- Consensus risk score determines interest rate
- No arbitrary gatekeeping

### 4. **Institutional Adoption**
Hedge fund needs RWA exposure
- Traditional: Pay $500K to boutique PE firm for due diligence
- ZAIR: Query consensus for $100 fee, get 10,000 expert perspectives
- 10,000x more eyes, 5x cheaper

---

## 🚀 Roadmap

### ✅ Phase 1: Foundation (Current - Q3 2026)
- [x] Federated mining with real AI (Ollama)
- [x] EIP-712 cryptographic signing
- [x] Consensus aggregation
- [x] PoA reward distribution
- [x] RLHF training data recording

### 🔨 Phase 2: Smart Contracts (Q4 2026 - Q1 2027)
- [ ] PHI token smart contract (ERC-20)
- [ ] Automated reward distribution on-chain
- [ ] Staking contract for validators
- [ ] Treasury for protocol development
- [ ] Governance token launch (ZAI)

### 🌍 Phase 3: Scaling (Q2 2027 - Q3 2027)
- [ ] Layer 2 deployment (Arbitrum, Optimism)
- [ ] Cross-chain signature verification
- [ ] Multi-asset categories (RealEstate, Commodities, Bonds)
- [ ] Institutional validator tier
- [ ] Enterprise API (premium features)

### 🎓 Phase 4: Autonomous DAO (Q4 2027+)
- [ ] DAO governance contracts
- [ ] Community model training (fine-tune LLMs)
- [ ] Decentralized dispute resolution
- [ ] Protocol parameters voted by token holders
- [ ] Fully autonomous network

---

## 🤝 How to Contribute

### Developers
```bash
# Fix bugs, add features
git clone https://github.com/zairprotocol/validator.git
# See CONTRIBUTING.md for guidelines
```

### Miners
```bash
# Join the network and earn PHI
python src/miner.py --node-name Your_Node_Name
# See QUICK_REFERENCE.md for setup
```

### Researchers
- Fine-tune language models on RLHF datasets
- Optimize consensus algorithms
- Analyze protocol security
- Publish improvements

### Business Partnerships
- Integrations with RWA platforms
- Institutional validator nodes
- Asset-specific mining pools
- Contact: partnerships@zairprotocol.com

---

## ⚠️ Risk Disclaimer

ZAIR is experimental technology. Be aware:
- Ethereum network fees apply to signature verification
- PHI token value subject to market forces
- Smart contracts not yet audited (Phase 2)
- Always verify predictions independently
- Do not use for risk-on investment decisions (yet)

---

## 🔒 Security

### Audits (Planned)
- Q1 2027: Smart contract security audit
- Q2 2027: Cryptographic protocol review
- Q3 2027: Penetration testing

### Bug Bounty
Find a vulnerability?
- Report to security@zairprotocol.com
- Confidential disclosure
- Rewards available

### Private Key Safety
```bash
# NEVER do this:
git add .env  # ❌ WRONG

# DO this:
echo ".env" >> .gitignore  # ✓ RIGHT
export ETHEREUM_PRIVATE_KEY=0x...  # ✓ Use env var
```

---

## 📈 Metrics & Monitoring

### Real-Time Dashboard
```bash
# Check network health
curl http://localhost:8001/network_status

{
  "miners_registered": 1247,
  "total_tokens_distributed": 1523000,
  "assets_processed": 342,
  "avg_consensus_accuracy": 91.7,
  "training_records": 3420
}
```

### Join the Community
- **Discord:** https://discord.gg/52xtBC8vk
- **Twitter:** @ZAIRProtocol
- **GitHub:** https://discord.gg/52xtBC8vk
- **Telegram:** https://t.me/zairprotocol

---

## 📜 License

Apache License 2.0

**Permissions:** Commercial use, modification, distribution  
**Conditions:** License and copyright notice  
**Limitations:** Liability, warranty

See [LICENSE](LICENSE) for full text.

---

## 🙏 Acknowledgments

Built on the shoulders of giants:
- **Ollama** for making local LLMs accessible
- **Ethereum** for EIP-712 standard
- **Web3.py** for cryptographic utilities
- **FastAPI** for robust API framework
- **Open-source community** for inspiration

---

## 🌟 The Future of RWA Finance

Today: Centralized gatekeepers control RWA access  
Tomorrow: Decentralized AI consensus unlocks $100T market

**Join us in building it.**

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                            ┃
┃  "The best way to predict the future is to invent it."   ┃
┃                            — Alan Kay                     ┃
┃                                                            ┃
┃  ZAIR invents it with 10,000 miners, real AI, and       ┃
┃  cryptographic proof of honesty.                         ┃
┃                                                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

---

**Ready to revolutionize RWA risk intelligence?**

- 👉 **[Quick Start](#-quick-start-5-minutes)** - Get mining in 5 minutes
- 📖 **[Full Docs](INTEGRATION_GUIDE.md)** - Deep technical guide
- 🤖 **[Run Test](test_integration.py)** - See it in action
- 💬 **[Join Discord](https://discord.gg/52xtBC8vk)** - Meet the community
- ⭐ **[Star on GitHub](https://github.com/zairprotocol/validator)** - Show your support
