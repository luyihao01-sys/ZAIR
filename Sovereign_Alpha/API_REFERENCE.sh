#!/usr/bin/env bash
# Quick API Reference Card - Copy/Paste Ready Commands

BASE_URL="http://localhost:8000"

# ═══════════════════════════════════════════════════════════════
# 1. GET NETWORK STATUS
# ═══════════════════════════════════════════════════════════════
# Real-time Hive Mind network health, all nodes, PHI tokens in circulation

curl -s "$BASE_URL/api/hive/network-status" | jq .

# ───────────────────────────────────────────────────────────────

# 2. GET LEADERBOARD
# ───────────────────────────────────────────────────────────────
# Ranked nodes by PHI tokens and accuracy

curl -s "$BASE_URL/api/hive/leaderboard" | jq .

# ───────────────────────────────────────────────────────────────

# 3. SUBMIT ASSET FOR INFERENCE (POST)
# ───────────────────────────────────────────────────────────────
# All 5 nodes run local inference, aggregate consensus, distribute PoA rewards

# Example: MakerDAO Real Estate Fund
curl -s -X POST "$BASE_URL/api/hive/submit-asset\
?asset_id=RWA001\
&asset_name=MakerDAO%20Real%20Estate%20Fund\
&legal_risk=35\
&liquidity_risk=40\
&smart_contract_risk=30\
&counterparty_risk=25\
&yield_sustainability=70\
&actual_stability=true" | jq .

# Example: Untested DeFi Protocol (Risky)
curl -s -X POST "$BASE_URL/api/hive/submit-asset\
?asset_id=RWA003\
&asset_name=Untested%20DeFi%20Protocol\
&legal_risk=75\
&liquidity_risk=85\
&smart_contract_risk=90\
&counterparty_risk=70\
&yield_sustainability=45\
&actual_stability=false" | jq .

# ───────────────────────────────────────────────────────────────

# 4. GET TRAINING DATASET
# ───────────────────────────────────────────────────────────────
# JSONL records for RLHF fine-tuning (limit=100 default)

curl -s "$BASE_URL/api/hive/training-dataset?limit=10" | jq .

# Get all records
curl -s "$BASE_URL/api/hive/training-dataset?limit=1000" | jq . > training_export.json

# ───────────────────────────────────────────────────────────────

# 5. GET INDIVIDUAL NODE STATS
# ───────────────────────────────────────────────────────────────
# Node performance, recent rewards, accuracy history

# Dubai Node
curl -s "$BASE_URL/api/hive/node/Node_Dubai" | jq .

# WallStreet Node
curl -s "$BASE_URL/api/hive/node/Node_WallStreet" | jq .

# Singapore Node
curl -s "$BASE_URL/api/hive/node/Node_Singapore" | jq .

# Frankfurt Node
curl -s "$BASE_URL/api/hive/node/Node_Frankfurt" | jq .

# Tokyo Node
curl -s "$BASE_URL/api/hive/node/Node_Tokyo" | jq .

# ═══════════════════════════════════════════════════════════════
# PYTHON EXAMPLES
# ═══════════════════════════════════════════════════════════════

cat > test_hive_api.py << 'EOF'
import requests
import json

BASE_URL = "http://localhost:8000"

# 1. Get network status
print("=== Network Status ===")
resp = requests.get(f"{BASE_URL}/api/hive/network-status")
data = resp.json()
print(f"Active Nodes: {data['nodes_active']}/{data['total_nodes']}")
print(f"Total PHI: {data['total_tokens_in_circulation']:.2f}")
print()

# 2. Get leaderboard
print("=== Top 3 Nodes ===")
resp = requests.get(f"{BASE_URL}/api/hive/leaderboard")
data = resp.json()
for entry in data['leaderboard'][:3]:
    print(f"{entry['rank']}. {entry['node_name']:20} | "
          f"PHI: {entry['cumulative_tokens']:.1f} | "
          f"Accuracy: {entry['avg_accuracy']:.1f}%")
print()

# 3. Submit asset
print("=== Submitting BlackRock Treasury ETF ===")
resp = requests.post(
    f"{BASE_URL}/api/hive/submit-asset",
    params={
        "asset_id": "RWA002",
        "asset_name": "BlackRock Treasury ETF",
        "legal_risk": 15,
        "liquidity_risk": 20,
        "smart_contract_risk": 40,
        "counterparty_risk": 10,
        "yield_sustainability": 80,
        "actual_stability": True,
    }
)
result = resp.json()
consensus = result['consensus']
print(f"Consensus Risk: {consensus['consensus_composite_risk']:.2f}/100")
print(f"Status: {consensus['consensus_threshold'].upper()}")
print(f"Sentiment: {consensus['consensus_sentiment'].upper()}")
print(f"Total PHI Distributed: {result['total_tokens_distributed']:.1f}")
print()

# 4. Get training dataset
print("=== Training Dataset (RLHF) ===")
resp = requests.get(f"{BASE_URL}/api/hive/training-dataset?limit=1")
data = resp.json()
print(f"Total Records: {data['total_records']}")
if data['records']:
    rec = data['records'][0]
    print(f"Latest: {rec['asset_name']} - Accuracy: {rec['avg_accuracy_across_nodes']:.2f}%")
print()

# 5. Get node stats
print("=== Node_WallStreet Stats ===")
resp = requests.get(f"{BASE_URL}/api/hive/node/Node_WallStreet")
data = resp.json()
print(f"Region: {data['region']}")
print(f"PHI Tokens: {data['cumulative_tokens']:.2f}")
print(f"Accuracy: {data['avg_accuracy']:.2f}%")
print(f"Predictions: {data['total_predictions']}")
EOF

# Run Python example
python test_hive_api.py

# ═══════════════════════════════════════════════════════════════
# REAL-TIME MONITORING (bash loop)
# ═══════════════════════════════════════════════════════════════

# Monitor network every 10 seconds
watch -n 10 'curl -s http://localhost:8000/api/hive/network-status | jq "{nodes_active: .nodes_active, total_tokens: .total_tokens_in_circulation, records: .training_dataset_records}"'

# ═══════════════════════════════════════════════════════════════
# BULK TEST - Submit Multiple Assets
# ═══════════════════════════════════════════════════════════════

cat > bulk_test.sh << 'EOFBULK'
#!/bin/bash

# Array of test assets
assets=(
  "RWA001|MakerDAO Real Estate Fund|35|40|30|25|70|true"
  "RWA002|BlackRock Treasury ETF|15|20|40|10|80|true"
  "RWA003|Centrifuge CFG|45|50|35|40|60|true"
  "RWA004|Untested DeFi Protocol|75|85|90|70|45|false"
  "RWA005|Tokenized Gold|25|30|20|15|75|true"
)

for asset in "${assets[@]}"; do
  IFS='|' read -r id name lr lir scr cr ys stability <<< "$asset"
  
  echo "Submitting: $name"
  curl -s -X POST "http://localhost:8000/api/hive/submit-asset\
?asset_id=$id\
&asset_name=$(echo $name | sed 's/ /%20/g')\
&legal_risk=$lr\
&liquidity_risk=$lir\
&smart_contract_risk=$scr\
&counterparty_risk=$cr\
&yield_sustainability=$ys\
&actual_stability=$stability" | jq '.consensus | {risk: .consensus_composite_risk, status: .consensus_threshold, sentiment: .consensus_sentiment}'
  
  sleep 1
done

echo "All assets processed!"
EOFBULK

chmod +x bulk_test.sh
./bulk_test.sh

# ═══════════════════════════════════════════════════════════════
# EXPORT DATA FOR ANALYSIS
# ═══════════════════════════════════════════════════════════════

# Export all training records to CSV
curl -s "http://localhost:8000/api/hive/training-dataset?limit=1000" | jq -r '.records[] | [.timestamp, .asset_id, .asset_name, .consensus_composite_risk, .avg_accuracy_across_nodes, .num_nodes_participated] | @csv' > hive_training_data.csv

# Export leaderboard to JSON
curl -s "http://localhost:8000/api/hive/leaderboard" | jq '.leaderboard' > node_leaderboard.json

# Export all node stats to JSON
curl -s "http://localhost:8000/api/hive/network-status" | jq '.nodes' > all_nodes_stats.json

# ═══════════════════════════════════════════════════════════════
# ANALYZE TRAINING DATA
# ═══════════════════════════════════════════════════════════════

python << 'EOFPYTHON'
import json
import requests
from statistics import mean, stdev

BASE = "http://localhost:8000"

# Get training data
resp = requests.get(f"{BASE}/api/hive/training-dataset?limit=1000")
data = resp.json()

if data['records']:
    records = data['records']
    
    print("═" * 60)
    print("HIVE MIND TRAINING DATA ANALYSIS")
    print("═" * 60)
    print(f"Total Records: {len(records)}")
    print()
    
    # Risk distribution
    risks = [r['consensus_composite_risk'] for r in records]
    print(f"Risk Scores: min={min(risks):.2f}, max={max(risks):.2f}, avg={mean(risks):.2f}")
    if len(risks) > 1:
        print(f"            stdev={stdev(risks):.2f}")
    print()
    
    # Accuracy distribution
    accs = [r['avg_accuracy_across_nodes'] for r in records]
    print(f"Accuracy:    min={min(accs):.2f}%, max={max(accs):.2f}%, avg={mean(accs):.2f}%")
    if len(accs) > 1:
        print(f"            stdev={stdev(accs):.2f}%")
    print()
    
    # Sentiment distribution
    sentiments = {}
    for r in records:
        sent = r['consensus_sentiment']
        sentiments[sent] = sentiments.get(sent, 0) + 1
    print("Sentiment Distribution:")
    for sent, count in sentiments.items():
        pct = (count / len(records)) * 100
        print(f"  {sent.upper():10} {count:3} records ({pct:5.1f}%)")
    print()
    
    # Asset distribution
    assets = {}
    for r in records:
        asset_name = r['asset_name']
        assets[asset_name] = assets.get(asset_name, 0) + 1
    print("Top Assets Evaluated:")
    for asset, count in sorted(assets.items(), key=lambda x: -x[1])[:10]:
        print(f"  {asset:40} {count} inferences")

EOFPYTHON

# ═══════════════════════════════════════════════════════════════
# INTERACTIVE PYTHON SHELL
# ═══════════════════════════════════════════════════════════════

python << 'EOFSHELL'
import requests
import json

BASE = "http://localhost:8000"

print("""
╔════════════════════════════════════════════════════╗
║  🐝 HIVE MIND INTERACTIVE SHELL                   ║
╚════════════════════════════════════════════════════╝

Commands:
  status()         - Get network status
  leaderboard()    - Show top nodes
  submit(asset)    - Submit new asset (dict)
  training(n)      - Get last N training records
  node(name)       - Get node stats

Example:
  >>> submit({
  ...   'asset_id': 'TEST001',
  ...   'asset_name': 'Test Asset',
  ...   'legal_risk': 50,
  ...   'liquidity_risk': 50,
  ...   'smart_contract_risk': 50,
  ...   'counterparty_risk': 50,
  ...   'yield_sustainability': 50,
  ...   'actual_stability': True
  ... })

""")

def status():
    resp = requests.get(f"{BASE}/api/hive/network-status")
    return resp.json()

def leaderboard():
    resp = requests.get(f"{BASE}/api/hive/leaderboard")
    return resp.json()['leaderboard']

def submit(asset_dict):
    resp = requests.post(f"{BASE}/api/hive/submit-asset", params=asset_dict)
    return resp.json()

def training(n=5):
    resp = requests.get(f"{BASE}/api/hive/training-dataset?limit={n}")
    return resp.json()['records']

def node(name):
    resp = requests.get(f"{BASE}/api/hive/node/{name}")
    return resp.json() if resp.status_code == 200 else {"error": "Node not found"}

# Start interactive shell
import code
code.InteractiveConsole(globals()).interact(banner="")

EOFSHELL
