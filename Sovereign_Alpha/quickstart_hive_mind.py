#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║    QUICK START: Hive Mind Network — Federated Risk Intelligence     ║
║                                                                    ║
║  This script demonstrates the complete Hive Mind Network in action.║
║  Run this to see:                                                  ║
║  - 5 decentralized nodes submitting risk assessments               ║
║  - Consensus aggregation with weighted voting                      ║
║  - Proof of Alpha (PoA) reward distribution                        ║
║  - Training dataset generation for RLHF                           ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import requests
import json
import time
import sys

# API Base URL
BASE_URL = "http://localhost:8000"


def print_section(title):
    """Pretty print section headers."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def check_server():
    """Check if server is running."""
    try:
        resp = requests.get(f"{BASE_URL}/api/health", timeout=2)
        if resp.status_code == 200:
            print(f"✓ Server is running at {BASE_URL}")
            return True
    except:
        pass
    print(f"✗ Server not running at {BASE_URL}")
    print(f"  Start it with: python app.py")
    return False


def demo_1_network_status():
    """Demo 1: Check network status."""
    print_section("DEMO 1: Network Status")

    resp = requests.get(f"{BASE_URL}/api/hive/network-status")
    data = resp.json()

    print(f"Active Nodes: {data['nodes_active']}/{data['total_nodes']}")
    print(f"Total PHI Tokens: {data['total_tokens_in_circulation']:.2f}")
    print(f"Training Records: {data['training_dataset_records']}\n")

    print("Node Details:")
    for node_name, node_data in data['nodes'].items():
        print(f"  {node_name:20} | PHI: {node_data['cumulative_tokens']:>7.1f} | "
              f"Accuracy: {node_data['avg_accuracy']:>6.1f}%")

    return data


def demo_2_leaderboard():
    """Demo 2: View leaderboard."""
    print_section("DEMO 2: Node Leaderboard")

    resp = requests.get(f"{BASE_URL}/api/hive/leaderboard")
    data = resp.json()

    print(f"Symbol: {data['token_symbol']}\n")
    print("Rank | Node Name           | PHI Tokens | Accuracy")
    print("-" * 60)
    for entry in data['leaderboard'][:5]:
        print(f"{entry['rank']:>4} | {entry['node_name']:18} | "
              f"{entry['cumulative_tokens']:>10.1f} | {entry['avg_accuracy']:>6.1f}%")


def demo_3_submit_asset():
    """Demo 3: Submit RWA asset for inference."""
    print_section("DEMO 3: Submit Asset for Decentralized Inference")

    print("Submitting: MakerDAO Real Estate Fund\n")

    # Submit asset
    resp = requests.post(
        f"{BASE_URL}/api/hive/submit-asset",
        params={
            "asset_id": "RWA001",
            "asset_name": "MakerDAO Real Estate Fund",
            "legal_risk": 35,
            "liquidity_risk": 40,
            "smart_contract_risk": 30,
            "counterparty_risk": 25,
            "yield_sustainability": 70,
            "actual_stability": True,
        }
    )

    result = resp.json()
    consensus = result['consensus']

    print(
        f"Consensus Risk Score: {consensus['consensus_composite_risk']:.2f}/100")
    print(f"Confidence Level: {consensus['consensus_confidence']:.1f}%")
    print(f"Network Sentiment: {consensus['consensus_sentiment'].upper()}")
    print(f"Status: {consensus['consensus_threshold'].upper()}")
    print(f"Total Nodes Participated: {consensus['num_nodes']}")

    print(f"\nNode Submissions:")
    for node_name, vector in result['node_vectors'].items():
        print(f"  {node_name:20} | Risk: {vector['composite_risk_score']:>6.1f} | "
              f"Confidence: {vector['confidence_level']:>5.1f}%")

    print(f"\nRewards Distributed:")
    total_tokens = 0
    for reward in result['rewards']:
        print(f"  {reward['node_name']:20} | Tier: {reward['reward_tier']:20} | "
              f"PHI: {reward['tokens_mined']:>6.1f}")
        total_tokens += reward['tokens_mined']
    print(f"\nTotal Tokens Distributed: {total_tokens:.1f} PHI")

    return result


def demo_4_training_dataset():
    """Demo 4: View training dataset."""
    print_section("DEMO 4: Training Dataset (Model Recycling)")

    resp = requests.get(f"{BASE_URL}/api/hive/training-dataset?limit=5")
    data = resp.json()

    print(f"Total Records: {data['total_records']}")
    print(f"File: {data['file_path']}\n")

    if data['records']:
        for i, record in enumerate(data['records'][:2], 1):
            print(f"Record {i}: {record['asset_name']} ({record['asset_id']})")
            print(
                f"  Consensus Risk: {record['consensus_composite_risk']:.2f}")
            print(f"  Nodes: {record['num_nodes_participated']}")
            print(
                f"  Avg Accuracy: {record['avg_accuracy_across_nodes']:.2f}%")
            print()


def demo_5_node_stats():
    """Demo 5: Individual node statistics."""
    print_section("DEMO 5: Individual Node Statistics")

    node_name = "Node_WallStreet"
    print(f"Fetching stats for: {node_name}\n")

    resp = requests.get(f"{BASE_URL}/api/hive/node/{node_name}")
    if resp.status_code == 404:
        print(f"Node '{node_name}' not found. Available nodes:")
        status_resp = requests.get(f"{BASE_URL}/api/hive/network-status")
        status = status_resp.json()
        for n in status['nodes'].keys():
            print(f"  - {n}")
        return

    data = resp.json()

    print(f"Region: {data['region']}")
    print(f"Timezone: {data['timezone']}")
    print(f"Cumulative Tokens: {data['cumulative_tokens']:.2f} PHI")
    print(f"24h Tokens Mined: {data['tokens_mined_24h']:.2f} PHI")
    print(f"Total Predictions: {data['total_predictions']}")
    print(f"Average Accuracy: {data['avg_accuracy']:.2f}%")
    print(f"Latest Reward Tier: {data['latest_reward_tier'].upper()}\n")

    if data['recent_rewards']:
        print("Recent Rewards:")
        for reward in data['recent_rewards'][-3:]:
            print(f"  {reward['asset_id']}: {reward['reward_tier']:20} | "
                  f"Accuracy: {reward['accuracy_score']:.1f}% | "
                  f"PHI: {reward['tokens_mined']:.1f}")


def main():
    """Run all demos."""
    print("\n" + "="*70)
    print("  🐝 HIVE MIND NETWORK — Quick Start Guide")
    print("="*70)

    # Check server
    if not check_server():
        print("\nTo start the server, run in another terminal:")
        print("  cd e:\\Sovereign_Alpha")
        print("  python app.py")
        sys.exit(1)

    time.sleep(1)

    # Run demos
    try:
        demo_1_network_status()
        time.sleep(1)

        demo_2_leaderboard()
        time.sleep(1)

        demo_3_submit_asset()
        time.sleep(1)

        demo_4_training_dataset()
        time.sleep(1)

        demo_5_node_stats()

        print_section("✓ All Demos Complete!")
        print("\nNext Steps:")
        print("  1. Open browser: http://localhost:8000/status")
        print("  2. Check 'DECENTRALIZED INFERENCE NETWORK' panel on right")
        print("  3. View node leaderboard in dock")
        print("  4. Try submitting different assets via:")
        print(f"     {BASE_URL}/api/hive/submit-asset?...")
        print("  5. Review training_dataset.jsonl for RLHF fine-tuning")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
