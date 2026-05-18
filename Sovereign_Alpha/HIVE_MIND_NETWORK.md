# 🐝 Hive Mind Network — Federated Risk Intelligence

> **Transform ZAIR into a Web3 AI Collective**: A decentralized network of local AI nodes that run regional inference on off-chain data, submit risk assessments to the protocol, and earn **Proof of Alpha (PoA)** tokens for accurate predictions.

---

## 🌍 System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                   HIVE MIND PROTOCOL                        │
│  (Central aggregator + PoA reward distributor)              │
├──────────────┬──────────────┬──────────────┬──────────────┬─│
│              │              │              │              │ │
│ Node_Dubai   │Node_WallSt.  │Node_Singapore│Node_Frankfurt│...
│ (Middle East)│(North Amer.) │(Asia-Pacific)│(Europe)      │
│ Local Data:  │ Local Data:  │ Local Data:  │ Local Data:  │
│ • UAE Legal  │ • SEC Files  │ • Crypto     │ • MiCA       │
│ • GCC Yields │ • US Market  │ • RWA Adopt  │ • ESG        │
└──────────────┴──────────────┴──────────────┴──────────────┘
         ▼         ▼              ▼         ▼
    Risk_Vector  Risk_Vector  Risk_Vector  Risk_Vector
         └─────────────────────────┬────────────────────┘
                                  ▼
                        Consensus_Risk_Score
                                  ▼
                    ┌─────────────────────────┐
                    │  Verify against actual  │
                    │  asset stability       │
                    └─────────────────────────┘
                                  ▼
                    ┌─────────────────────────┐
                    │  Distribute PoA Rewards │
                    │  (PHI Tokens)           │
                    └─────────────────────────┘
                                  ▼
                    ┌─────────────────────────┐
                    │  Save to training_      │
                    │  dataset.jsonl (RLHF)   │
                    └─────────────────────────┘
```

---

## 🎯 Key Mechanisms

### 1. **Risk Vectors** — Local Node Inference
Each node runs local inference on regional data and submits a `RiskVector` containing:
- **5 Risk Components** (0-100 scale):
  - `legal_risk` — Jurisdiction/regulatory compliance
  - `liquidity_risk` — Market depth, TVL stability
  - `smart_contract_risk` — Audit quality, complexity
  - `counterparty_risk` — Issuer stability
  - `yield_sustainability` — Whether yield is sustainable

- **Composite Score**: Weighted average of above components
- **Confidence Level**: Node's confidence (based on historical accuracy)
- **Regional Sentiment**: "bullish", "neutral", or "bearish"

### 2. **Consensus Aggregation**
The protocol combines all node vectors using **weighted averaging**:
- Nodes with higher cumulative PHI tokens get higher weight
- **Wisdom of crowds** effect: More experienced nodes steer consensus
- Result: `consensus_composite_risk`, `consensus_sentiment`

### 3. **Proof of Alpha (PoA)** — Reward Mechanism
After an asset's actual stability is observed, nodes are rewarded based on accuracy:

| Tier | Criteria | PHI Reward |
|------|----------|-----------|
| **Perfect Match** | Accuracy ≥95% + Correct Prediction | **100 PHI** |
| **High Confidence** | Accuracy ≥90% | **75 PHI** |
| **Medium Confidence** | Accuracy ≥75% | **50 PHI** |
| **Low Confidence** | Accuracy ≥50% | **25 PHI** |
| **Consensus Miss** | Accuracy <50% | **0 PHI** |

### 4. **Model Recycling** — training_dataset.jsonl
The protocol saves every inference cycle to `training_dataset.jsonl`:
```jsonl
{
  "timestamp": "2026-05-18T12:00:00Z",
  "asset_id": "RWA001",
  "consensus_composite_risk": 33.74,
  "num_nodes_participated": 5,
  "node_vectors": [...],           // All local assessments
  "rewards_distributed": [...],    // PoA rewards
  "avg_accuracy_across_nodes": 96.27
}
```

**This becomes your fine-tuning dataset for future RLHF** — the aggregated "human/AI hive mind" collective knowledge.

---

## 5️⃣ Global Nodes

### Current Network

| Node | Region | Timezone | Bias | Regional Data Focus |
|------|--------|----------|------|---------------------|
| **Node_Dubai** | Middle East | GST | Conservative | UAE regulatory, GCC yields |
| **Node_WallStreet** | North America | EST | Aggressive | SEC filings, US market sentiment |
| **Node_Singapore** | Asia-Pacific | SGT | Balanced | Crypto sentiment, RWA adoption |
| **Node_Frankfurt** | Europe | CET | Balanced | EU MiCA compliance, ESG |
| **Node_Tokyo** | East Asia | JST | Tech-forward | Japan DeFi adoption, institutional flows |

Each node applies its regional **bias** to the base risk assessment:
- **Conservative**: Adds +5-8% to risk components
- **Aggressive**: Subtracts 5-8% from risk components
- **Balanced**: Minimal ±0-5% noise

---

## 🚀 API Endpoints

### Public Hive Mind APIs

#### 1. Get Network Status
```bash
GET /api/hive/network-status
```
Response:
```json
{
  "timestamp": "2026-05-18T12:00:00Z",
  "total_nodes": 5,
  "nodes_active": 5,
  "total_tokens_in_circulation": 3254.39,
  "nodes": {
    "Node_Dubai": {
      "cumulative_tokens": 729.2,
      "tokens_mined_24h": 150.0,
      "total_predictions": 3,
      "avg_accuracy": 95.7,
      "latest_reward_tier": "high_confidence"
    },
    ...
  },
  "training_dataset_records": 3
}
```

#### 2. Get Node Leaderboard
```bash
GET /api/hive/leaderboard
```
Response:
```json
{
  "token_symbol": "PHI",
  "leaderboard": [
    {
      "rank": 1,
      "node_name": "Node_WallStreet",
      "cumulative_tokens": 766.1,
      "avg_accuracy": 95.7%,
      "total_predictions": 3
    },
    ...
  ]
}
```

#### 3. Submit RWA Asset for Inference
```bash
POST /api/hive/submit-asset
```
Parameters:
- `asset_id` — Unique identifier
- `asset_name` — Display name
- `legal_risk` — 0-100 baseline
- `liquidity_risk` — 0-100 baseline
- `smart_contract_risk` — 0-100 baseline
- `counterparty_risk` — 0-100 baseline
- `yield_sustainability` — 0-100 baseline
- `actual_stability` — Boolean (true if asset proved stable)

Response: Complete inference result with node vectors, consensus, and rewards

#### 4. Get Training Dataset (Model Recycling)
```bash
GET /api/hive/training-dataset?limit=100
```
Response: JSONL records for fine-tuning

#### 5. Get Individual Node Stats
```bash
GET /api/hive/node/{node_name}
```
Response: Node performance, recent rewards, accuracy history

---

## 🎮 Dashboard Integration

### UI Panels

#### Panel 1: Decentralized Inference Network (Right Column)
Shows real-time network status:
- Active nodes count
- Total PHI tokens in circulation
- Per-node card with:
  - Region, timezone, bias
  - Cumulative tokens earned
  - Latest prediction accuracy
  - Most recent reward tier

#### Panel 2: Node Leaderboard (Dock)
Rankings by:
- PHI tokens (descending)
- Accuracy (%)
- Regional diversity

#### Panel 3: Token Mining Stats (Dock)
- Total PHI in circulation
- Active nodes
- Total inferences recorded

---

## 📊 Example Flow

### Step 1: Submit MakerDAO Real Estate Fund
```bash
curl -X POST "http://localhost:8000/api/hive/submit-asset?asset_id=RWA001&asset_name=MakerDAO%20Real%20Estate%20Fund&legal_risk=35&liquidity_risk=40&smart_contract_risk=30&counterparty_risk=25&yield_sustainability=70&actual_stability=true"
```

### Step 2: All 5 Nodes Run Inference
- Node_Dubai sees high legal_risk → adds +5% conservative bias → 40.9/100
- Node_WallStreet seeks yield → subtracts 5% aggressive bias → 31.6/100
- Node_Singapore balanced → minimal noise → 34.7/100
- etc.

### Step 3: Protocol Aggregates
```
Consensus Risk = (40.9*w1 + 31.6*w2 + 34.7*w3 + 31.5*w4 + 26.6*w5) = 33.74/100
Status: SAFE (< 45 threshold)
```

### Step 4: Verify & Reward
- Asset proved stable (actual_stability=true)
- Node_WallStreet was closest (31.6 vs 33.74) → 100 PHI (perfect_match)
- Node_Singapore close (34.7 vs 33.74) → 100 PHI (perfect_match)
- Node_Dubai farther (40.9 vs 33.74) → 75 PHI (high_confidence)

### Step 5: Save to training_dataset.jsonl
Append full record including all vectors, sentiment votes, rewards → future RLHF fine-tuning

---

## 💡 Use Cases

### 1. RWA Safety Assessments
Submit new tokenized real estate, bonds, or commodities → Get decentralized risk consensus instantly

### 2. Multi-Regional Compliance
Node_Frankfurt ensures MiCA compliance, Node_Dubai checks Sharia compliance, etc. → Holistic regulatory view

### 3. Token-Weighted Governance
Node votes weighted by accuracy + cumulative PHI tokens → Meritocratic network governance

### 4. RLHF Model Tuning
Collect 1000s of inference cycles → Fine-tune local LLM on aggregated dataset → Improve future predictions

### 5. Arbitrage Detection
If regional sentiment diverges sharply → Opportunity to arbitrage RWA pricing across regions

---

## 🔧 Configuration & Customization

### Add New Nodes
Edit `NODES` dict in `hive_mind_network.py`:
```python
NODES = {
    "Node_Dubai": {...},
    "Node_WallStreet": {...},
    "Node_London": {  # NEW
        "region": "Europe (UK)",
        "timezone": "GMT",
        "bias": "risk_regulatory",
        "local_data": ["FCA_guidance", "Bank_of_England_sentiment"],
    },
}
```

### Adjust Reward Tiers
Edit `POA_REWARD_TIERS`:
```python
POA_REWARD_TIERS = {
    "perfect_match": 200.0,      # Increased from 100
    "high_confidence": 100.0,    # Increased from 75
    ...
}
```

### Change Node Bias
Modify `run_local_inference()` logic in `HiveMindNode` class to adjust how regional biases are applied.

---

## 📈 Metrics & Analytics

### Key Metrics to Track

1. **Network Health**
   - Active nodes / Total nodes
   - Average consensus confidence
   - Network sentiment distribution (bullish/neutral/bearish %)

2. **Node Performance**
   - Cumulative PHI tokens per node
   - Accuracy trend (rolling 7-day, 30-day)
   - Prediction consistency

3. **Training Dataset Quality**
   - Number of records
   - Average num_nodes_participated
   - Average accuracy across all inferences

4. **PoA Economics**
   - Total PHI minted to date
   - Avg tokens per inference cycle
   - Token concentration (Herfindahl index)

---

## 🛠️ Integration with Sovereign Alpha

### Pipeline Flow
```
User Intent
    ↓
Sovereign Solver (intent → action)
    ↓
Hive Mind Network (risk consensus on RWA assets)
    ↓
Bridge Executor (on-chain execution)
    ↓
Audit Trail (immutable decision log)
```

### Cross-System Data Flow
1. **Monitor** collects RWA yields
2. **Solver** recommends allocation
3. **Hive Mind** validates asset safety independently
4. **Bridge** only executes if Hive consensus is "SAFE"
5. **Audit** logs both Solver decision AND Hive consensus

---

## 🚦 Running the System

### Demo Script
```bash
python hive_mind_network.py
```
Runs full pipeline with 3 sample RWA assets, displays leaderboard

### API Server
```bash
python app.py
# Server starts at http://localhost:8000
# Dashboard at http://localhost:8000/status
# Hive APIs available at /api/hive/*
```

### Real-Time Dashboard
Navigate to `http://localhost:8000/status` → See live node network panel with:
- Active nodes status
- PHI token mining in real-time
- Node leaderboard
- Regional sentiment breakdown

---

## 📝 File Structure

```
Sovereign_Alpha/
├── hive_mind_network.py          # Core Hive Mind engine
├── app.py                        # FastAPI + Hive endpoints
├── templates/
│   └── status.html               # UI with Hive Mind panel
├── training_dataset.jsonl        # Aggregated inference records (grows daily)
├── sovereign_intent_solver.py    # Original solver
├── sovereign_yield_monitor.py    # Original monitor
├── sovereign_executor_bridge.py  # Original bridge
└── HIVE_MIND_NETWORK.md         # This file
```

---

## 🎓 Future Enhancements

1. **Dynamic Node Addition** — Protocol-governed vote to add new regional nodes
2. **Slashing Mechanism** — Penalize nodes that consistently miss consensus
3. **Staking Pools** — Allow users to stake PHI for node rewards
4. **Cross-Chain Oracles** — Connect to Chainlink, Pyth for real-time verification
5. **Multi-Model Inference** — Different models per node type (ML vs statistical vs rule-based)
6. **DAO Governance** — PHI token holders vote on reward schedules, node parameters
7. **RLHF Pipeline** — Auto fine-tune models monthly using training_dataset.jsonl

---

## 📞 Support & Questions

For issues, feature requests, or to add new regional nodes:
- Check `/api/hive/network-status` for health
- Review `training_dataset.jsonl` for prediction quality
- Audit node accuracy via `/api/hive/leaderboard`

---

**Built with 🐝 collective intelligence for RWA markets**
