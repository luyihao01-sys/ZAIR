# 🏗️ Hive Mind Network — 系统架构与数据流

## 📊 高层架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ZENITH DASHBOARD (Web UI)                           │
│  (http://localhost:8000/status)                                             │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ LEFT PANEL                │ CENTER                │ RIGHT PANEL     │  │
│  │ ─────────────────         ─────────────────────   ─────────────────  │  │
│  │ • Treasury %              • Yield Spreads         • ZAIR Vault      │  │
│  │ • Risk Markers            • 24H Chart             • Fees            │  │
│  │ • Protocol Matrix         • Intent Proof          • Attestation     │  │
│  │                           • Audit Trail           • Sig Validators  │  │
│  │                                                                      │  │
│  │ NEW: Hive Mind Panel ┐                                              │  │
│  │ ├─ 5/5 Active Nodes │                                              │  │
│  │ ├─ 3,254 PHI Tokens │                                              │  │
│  │ └─ Node Cards        │                                              │  │
│  │    • Node_Dubai       │                                              │  │
│  │    • Node_WallStreet  │                                              │  │
│  │    • Node_Singapore   │                                              │  │
│  │    • Node_Frankfurt   │                                              │  │
│  │    • Node_Tokyo       │                                              │  │
│  │                       │                                              │  │
│  │ NEW: Dock Panels ─────┘                                              │  │
│  │ ├─ PHI Token Stats                                                  │  │
│  │ └─ Node Leaderboard (Top 5)                                         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │
                                    ▼
         ┌──────────────────────────────────────────────┐
         │     FastAPI (app.py) Server                  │
         │     http://localhost:8000                    │
         └──────────────────────────────────────────────┘
                        │
                        ├─ GET /api/pipeline
                        ├─ GET /api/monitor
                        ├─ GET /api/solve
                        ├─ GET /api/bridge
                        ├─ GET /api/tick
                        ├─ GET /api/audit-trail
                        │
                        ├─ 🆕 GET /api/hive/network-status
                        ├─ 🆕 GET /api/hive/leaderboard
                        ├─ 🆕 POST /api/hive/submit-asset
                        ├─ 🆕 GET /api/hive/training-dataset
                        └─ 🆕 GET /api/hive/node/{name}
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                   HIVE MIND PROTOCOL ENGINE                                   │
│               (hive_mind_network.py)                                          │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ HiveMindProtocol                                                        │ │
│  │                                                                         │ │
│  │  PHASE 1: Node Inference (Parallel)                                   │ │
│  │  ─────────────────────────────────────                                │ │
│  │      RWA Asset → │                                                     │ │
│  │                  ├─→ Node_Dubai          (Risk Assessment)            │ │
│  │                  ├─→ Node_WallStreet     (+ Regional Bias)           │ │
│  │                  ├─→ Node_Singapore      (+ Local Data Signals)      │ │
│  │                  ├─→ Node_Frankfurt                                   │ │
│  │                  └─→ Node_Tokyo                                       │ │
│  │                                                                        │ │
│  │             Each returns: RiskVector {                               │ │
│  │                 legal_risk (0-100)                                    │ │
│  │                 liquidity_risk                                        │ │
│  │                 smart_contract_risk                                  │ │
│  │                 counterparty_risk                                     │ │
│  │                 yield_sustainability                                  │ │
│  │                 composite_risk_score                                  │ │
│  │                 confidence_level                                      │ │
│  │                 regional_sentiment                                    │ │
│  │             }                                                         │ │
│  │                                                                       │ │
│  │  PHASE 2: Consensus Aggregation                                     │ │
│  │  ────────────────────────────────                                   │ │
│  │      Weighted Average (by cumulative_tokens):                       │ │
│  │      Consensus Risk = Σ(node_risk * weight)                         │ │
│  │                                                                       │ │
│  │      Returns: Consensus {                                           │ │
│  │          consensus_composite_risk                                    │ │
│  │          consensus_confidence                                        │ │
│  │          consensus_sentiment                                         │ │
│  │          threshold ("SAFE" / "RISKY")                               │ │
│  │      }                                                                │ │
│  │                                                                       │ │
│  │  PHASE 3: Proof of Alpha (PoA) Verification                        │ │
│  │  ─────────────────────────────────────────                         │ │
│  │      Compare node predictions vs actual_outcome                    │ │
│  │      Calculate accuracy for each node                              │ │
│  │      Determine reward tier                                          │ │
│  │                                                                      │ │
│  │      Reward Tiers:                                                  │ │
│  │      • Perfect Match (≥95%, correct prediction) → 100 PHI           │ │
│  │      • High Confidence (≥90%) → 75 PHI                              │ │
│  │      • Medium Confidence (≥75%) → 50 PHI                            │ │
│  │      • Low Confidence (≥50%) → 25 PHI                               │ │
│  │      • Consensus Miss (<50%) → 0 PHI                                │ │
│  │                                                                      │ │
│  │  PHASE 4: Model Recycling (RLHF)                                  │ │
│  │  ───────────────────────────────                                   │ │
│  │      Save to training_dataset.jsonl:                               │ │
│  │      {                                                               │ │
│  │          "asset_id": "RWA001",                                      │ │
│  │          "consensus_composite_risk": 33.74,                        │ │
│  │          "node_vectors": [...],      # All 5 local assessments    │ │
│  │          "rewards_distributed": [...],  # PoA rewards              │ │
│  │          "avg_accuracy_across_nodes": 96.27                        │ │
│  │      }                                                              │ │
│  │                                                                      │ │
│  │      → Aggregated "hive mind" collective knowledge                 │ │
│  │      → Ready for future model fine-tuning (RLHF)                   │ │
│  │                                                                      │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Individual Nodes (5x)                                               │  │
│  │                                                                     │  │
│  │  Node_Dubai                Node_WallStreet                         │  │
│  │  ├─ Region: Middle East     ├─ Region: North America             │  │
│  │  ├─ Timezone: GST           ├─ Timezone: EST                      │  │
│  │  ├─ Bias: Conservative      ├─ Bias: Aggressive                  │  │
│  │  ├─ Local Data:             ├─ Local Data:                        │  │
│  │  │  • UAE Legal             │  • SEC Filings                      │  │
│  │  │  • GCC Yields            │  • US Market Sentiment             │  │
│  │  ├─ cumulative_tokens: 729  ├─ cumulative_tokens: 766            │  │
│  │  └─ accuracy_history: 95.7% └─ accuracy_history: 95.7%           │  │
│  │                                                                     │  │
│  │  Node_Singapore            Node_Frankfurt                         │  │
│  │  ├─ Region: Asia-Pacific    ├─ Region: Europe                    │  │
│  │  ├─ Timezone: SGT           ├─ Timezone: CET                      │  │
│  │  ├─ Bias: Balanced          ├─ Bias: Balanced                    │  │
│  │  ├─ Local Data:             ├─ Local Data:                        │  │
│  │  │  • Crypto Sentiment      │  • MiCA Compliance                 │  │
│  │  │  • RWA Adoption          │  • ESG Metrics                     │  │
│  │  ├─ cumulative_tokens: 645  ├─ cumulative_tokens: 630            │  │
│  │  └─ accuracy_history: 98.4% └─ accuracy_history: 97.1%           │  │
│  │                                                                     │  │
│  │  Node_Tokyo                                                         │  │
│  │  ├─ Region: East Asia                                              │  │
│  │  ├─ Timezone: JST                                                  │  │
│  │  ├─ Bias: Tech-forward                                             │  │
│  │  ├─ Local Data:                                                    │  │
│  │  │  • Japan DeFi Adoption                                          │  │
│  │  │  • Institutional Flows                                          │  │
│  │  ├─ cumulative_tokens: 485                                         │  │
│  │  └─ accuracy_history: 96.7%                                        │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ PoA Reward Distribution                                             │  │
│  │                                                                     │  │
│  │  Perfect Match (100 PHI) ─────→ Node_WallStreet, Node_Singapore  │  │
│  │  High Confidence (75 PHI) ──→ Node_Dubai, Node_Tokyo             │  │
│  │  Medium Confidence (50 PHI) → (None in this cycle)                │  │
│  │  ...                                                               │  │
│  │                                                                    │  │
│  │  Total: 450 PHI Distributed ← Updates cumulative_tokens          │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────────┐
                    │ Persistent Storage          │
                    │                             │
                    ├─ training_dataset.jsonl    │
                    │  (Records: 3+)              │
                    │  • asset_id                 │
                    │  • consensus_risk           │
                    │  • node_vectors (5x)        │
                    │  • rewards (5x)             │
                    │  • avg_accuracy             │
                    │                             │
                    ├─ zair_audit.db            │
                    │  (Immutable audit trail)    │
                    │                             │
                    └─ solver_report.json        │
                       (Latest execution)        │
                    └─────────────────────────────┘
```

---

## 🔄 数据流完整示例

### 输入
```json
{
  "asset_id": "RWA001",
  "asset_name": "MakerDAO Real Estate Fund",
  "legal_risk": 35,
  "liquidity_risk": 40,
  "smart_contract_risk": 30,
  "counterparty_risk": 25,
  "yield_sustainability": 70,
  "actual_stability": true
}
```

### Phase 1: 节点推理 (并行)
```
Node_Dubai (Conservative Bias: +5-8%)
├─ legal_risk: 35 → 40.9
├─ liquidity_risk: 40 → 47.5
├─ smart_contract_risk: 30 → 25
├─ counterparty_risk: 25 → 33.5
├─ yield_sustainability: 70 → 64.5
└─ composite_risk: 39.9/100, sentiment: "neutral"

Node_WallStreet (Aggressive Bias: -5-8%)
├─ legal_risk: 35 → 30.6
├─ liquidity_risk: 40 → 34.1
├─ smart_contract_risk: 30 → 33.8
├─ counterparty_risk: 25 → 25.7
├─ yield_sustainability: 70 → 64.8
└─ composite_risk: 31.6/100, sentiment: "bullish"

Node_Singapore (Balanced Bias: ±0-5%)
├─ composite_risk: 34.7/100, sentiment: "bullish"

Node_Frankfurt (Balanced)
├─ composite_risk: 31.5/100, sentiment: "bullish"

Node_Tokyo (Tech-forward)
└─ composite_risk: 26.6/100, sentiment: "bullish"
```

### Phase 2: 共识聚合
```
Weights (by cumulative_tokens):
├─ Node_Dubai: 729 tokens (22%)
├─ Node_WallStreet: 766 tokens (23%)
├─ Node_Singapore: 645 tokens (20%)
├─ Node_Frankfurt: 630 tokens (19%)
└─ Node_Tokyo: 485 tokens (16%)

Weighted Consensus:
= (39.9 × 0.22) + (31.6 × 0.23) + (34.7 × 0.20) + (31.5 × 0.19) + (26.6 × 0.16)
= 8.78 + 7.27 + 6.94 + 5.99 + 4.26
= 33.74/100

Consensus Sentiment: BULLISH (4/5 nodes)
Status: SAFE (33.74 < 45 threshold)
Confidence: 60.04%
```

### Phase 3: PoA验证
```
Actual Outcome: asset_stability = TRUE ✓

Node Accuracy Calculations:
├─ Node_Dubai: |40.9 - 33.74| = 7.16 → accuracy 92.84% → 75 PHI ⭐
├─ Node_WallStreet: |31.6 - 33.74| = 2.14 → accuracy 97.86% → 100 PHI 🏆
├─ Node_Singapore: |34.7 - 33.74| = 0.96 → accuracy 99.04% → 100 PHI 🏆
├─ Node_Frankfurt: |31.5 - 33.74| = 2.24 → accuracy 97.76% → 100 PHI 🏆
└─ Node_Tokyo: |26.6 - 33.74| = 7.14 → accuracy 92.86% → 75 PHI ⭐

Average Accuracy: 96.27%
Total Tokens Distributed: 450 PHI
```

### Phase 4: RLHF保存
```jsonl
{
  "timestamp": "2026-05-17T21:36:37.840182+00:00",
  "asset_id": "RWA001",
  "asset_name": "MakerDAO Real Estate Fund",
  "consensus_composite_risk": 33.74,
  "consensus_confidence": 60.04,
  "consensus_sentiment": "bullish",
  "num_nodes_participated": 5,
  "node_vectors": [
    {"node_name": "Node_Dubai", "composite_risk_score": 39.9, ...},
    {"node_name": "Node_WallStreet", "composite_risk_score": 31.6, ...},
    {...},
    {...},
    {...}
  ],
  "rewards_distributed": [
    {"node_name": "Node_Dubai", "tokens_mined": 75, "reward_tier": "high_confidence"},
    {"node_name": "Node_WallStreet", "tokens_mined": 100, "reward_tier": "perfect_match"},
    {...},
    {...},
    {...}
  ],
  "avg_accuracy_across_nodes": 96.27
}
```

---

## 🎯 信息流总结

```
┌──────────────────────────────────────────────────────────────────┐
│ USER INPUT                                                       │
│ POST /api/hive/submit-asset with RWA asset parameters          │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 1: PARALLEL NODE INFERENCE                                │
│ • 5 nodes run local_inference() independently                   │
│ • Each applies regional bias to base risk components            │
│ • Each calculates composite_risk_score, confidence, sentiment   │
│ • All vectors collected by HiveMindProtocol                     │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 2: WEIGHTED CONSENSUS                                     │
│ • Weight each node by cumulative_tokens (meritocratic)         │
│ • Calculate weighted average of risk components                 │
│ • Determine consensus_sentiment (majority vote)                 │
│ • Assess threshold (SAFE if risk < 45)                         │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 3: PROOF OF ALPHA VERIFICATION                            │
│ • Compare each node_risk vs consensus_risk                      │
│ • Calculate accuracy percentage for each node                   │
│ • Verify prediction correctness vs actual_outcome               │
│ • Determine reward tier (perfect_match, high_conf, etc.)       │
│ • Allocate PHI tokens to nodes                                  │
│ • Update node.cumulative_tokens                                 │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 4: MODEL RECYCLING (RLHF)                                 │
│ • Append complete inference record to training_dataset.jsonl   │
│ • Record: all node vectors + rewards + avg accuracy            │
│ • Ready for future model fine-tuning                           │
│ • Represents aggregated "hive mind" collective knowledge        │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│ RETURN TO USER                                                   │
│ {                                                                │
│   "consensus": {...},              # Aggregated consensus      │
│   "node_vectors": {...},           # All 5 local assessments   │
│   "rewards": [...],                # PoA rewards for each node │
│   "total_tokens_distributed": 450  # Total PHI minted          │
│ }                                                                │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📈 Node Leaderboard Over Time

```
Time T=0 (Initial)
┌──────────────────┬─────────┬────────────┐
│ Node             │ PHI     │ Accuracy   │
├──────────────────┼─────────┼────────────┤
│ Node_WallStreet  │ 766.1   │ 95.7%      │ ← Higher tokens = higher weight
│ Node_Dubai       │ 729.2   │ 95.7%      │
│ Node_Singapore   │ 644.6   │ 98.4%      │ ← High accuracy attracts votes
│ Node_Frankfurt   │ 629.5   │ 97.1%      │
│ Node_Tokyo       │ 484.9   │ 96.7%      │
└──────────────────┴─────────┴────────────┘

Time T+1 (After 100 More Assets)
┌──────────────────┬─────────┬────────────┐
│ Node             │ PHI     │ Accuracy   │
├──────────────────┼─────────┼────────────┤
│ Node_Singapore   │ 1,200+  │ 98.5%      │ ← Winner: consistent accuracy
│ Node_WallStreet  │ 1,100   │ 96.2%      │
│ Node_Dubai       │ 950     │ 95.1%      │
│ Node_Frankfurt   │ 920     │ 97.0%      │
│ Node_Tokyo       │ 850     │ 96.8%      │
└──────────────────┴─────────┴────────────┘

Network Evolution:
• Accurate nodes accumulate tokens → higher voting weight
• Weight increases → more influence on consensus
• More influence → more predictions → more earning potential
• Self-reinforcing virtuous cycle of merit
```

---

## 🏆 PoA Reward Distribution Patterns

### Scenario A: Perfect Assets (Consensus Wrong!)
```
Consensus: 50/100 (RISKY)
Actual: SAFE

All nodes predicted RISKY
Nodes were unanimous but WRONG
Result: 0 PHI for all ✗
```

### Scenario B: Diverse Opinions (Consensus Right!)
```
Consensus: 35/100 (SAFE) ← Correct!

Node_Dubai:   40 (2% off) → 100 PHI 🏆
Node_WallSt:  31 (6% off) → 100 PHI 🏆
Node_Singap:  34 (1% off) → 100 PHI 🏆
Node_Frank:   36 (3% off) → 100 PHI 🏆
Node_Tokyo:   32 (3% off) → 100 PHI 🏆

Result: 500 PHI distributed to well-calibrated network
```

### Scenario C: Outlier Accuracy (Merit-based!)
```
Consensus: 40/100 (RISKY)
Actual: SAFE

Node_Dubai:   40 (0% off) → 100 PHI ✨ Best predictor!
Node_WallSt:  35 (5% off) → 100 PHI
Node_Singap:  42 (2% off) → 75 PHI
Node_Frank:   38 (2% off) → 75 PHI
Node_Tokyo:   45 (5% off) → 75 PHI

Result: High performer gets extra weight for next round
```

---

**System Design**: Trustless, Decentralized, Merit-Based
**Core Innovation**: Proof of Alpha + Model Recycling for continuous improvement

🐝 *Hive Mind Network — Where 1+1=3*
