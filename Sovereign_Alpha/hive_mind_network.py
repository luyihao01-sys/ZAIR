#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║          HIVE MIND NETWORK — Federated Risk Intelligence            ║
║    Decentralized AI Nodes + Proof of Alpha (PoA) + Model Recycling  ║
║                                                                    ║
║  Inspired by Bittensor & Hermes AI: Local nodes run regional        ║
║  inference on off-chain data (legal PDFs, sentiment) → submit       ║
║  Risk_Vector_Scores → Central protocol aggregates → PoA rewards     ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import sys
import time
import random
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict, field

# ---------------------------------------------------------------------------
#  Windows console UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

NODES = {
    "Node_Dubai": {
        "region": "Middle East",
        "timezone": "GST",
        "bias": "risk_conservative",  # Dubai prefers stable, compliant assets
        "local_data": ["UAE_regulatory_sentiment", "GCC_yield_feeds"],
    },
    "Node_WallStreet": {
        "region": "North America",
        "timezone": "EST",
        "bias": "risk_aggressive",  # Wall Street seeks high-yield opportunities
        "local_data": ["SEC_filings", "US_market_sentiment", "treasury_curve"],
    },
    "Node_Singapore": {
        "region": "Asia-Pacific",
        "timezone": "SGT",
        "bias": "risk_balanced",  # Singapore balances growth + stability
        "local_data": ["Asia_regulatory_news", "crypto_sentiment", "RWA_adoption"],
    },
    "Node_Frankfurt": {
        "region": "Europe",
        "timezone": "CET",
        "bias": "risk_balanced",  # EU regulatory-focused
        "local_data": ["EU_MiCA_compliance", "ESG_metrics", "DeFi_sentiment"],
    },
    "Node_Tokyo": {
        "region": "East Asia",
        "timezone": "JST",
        "bias": "risk_tech_forward",  # Japan tech-savvy, institutional
        "local_data": ["Japan_DeFi_adoption", "institutional_flows", "tech_sentiment"],
    },
}

# Proof of Alpha reward tiers
POA_REWARD_TIERS = {
    "perfect_match": 100.0,      # Node vector matches consensus perfectly
    "high_confidence": 75.0,     # Within 10% of consensus
    "medium_confidence": 50.0,   # Within 25% of consensus
    "low_confidence": 25.0,      # Within 50% of consensus
    "consensus_miss": 0.0,       # Outside consensus range
}

PROTOCOL_TOKENS_SYMBOL = "PHI"  # Protocol Hive Intelligence tokens
TRAINING_DATASET_FILE = "training_dataset.jsonl"

# ---------------------------------------------------------------------------
#  Risk Vector Model
# ---------------------------------------------------------------------------


@dataclass
class RiskVector:
    """
    Local node's assessment of an RWA asset's risk profile.
    """
    node_name: str
    timestamp: str
    asset_id: str
    asset_name: str

    # Risk components (0-100 scale)
    legal_risk: float          # Jurisdiction/regulatory compliance
    liquidity_risk: float      # Market depth, TVL stability
    smart_contract_risk: float  # Audit quality, complexity
    counterparty_risk: float   # Issuer stability, track record
    yield_sustainability: float  # Whether yield is sustainable

    # Composite scores
    composite_risk_score: float  # Weighted average of above
    confidence_level: float      # Node's confidence (0-100)

    # Regional sentiment
    regional_sentiment: str      # "bullish", "neutral", "bearish"
    local_data_signals: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PoAReward:
    """
    Proof of Alpha reward granted to a node for accurate predictions.
    """
    node_name: str
    timestamp: str
    asset_id: str
    accuracy_score: float        # How close node was to consensus (0-100)
    predicted_stability: bool    # Did node correctly predict asset stability?
    tokens_mined: float          # PHI tokens earned
    reward_tier: str             # Tier name (perfect_match, etc.)


class HiveMindNode:
    """
    Individual AI node in the federated network.
    Simulates local inference on regional data.
    """

    def __init__(self, node_name: str, config: dict):
        self.node_name = node_name
        self.region = config["region"]
        self.timezone = config["timezone"]
        self.bias = config["bias"]
        self.local_data = config["local_data"]
        self.cumulative_tokens = random.uniform(100, 500)  # Starting tokens
        self.historical_rewards: List[PoAReward] = []
        self.accuracy_history: List[float] = []

    def run_local_inference(self, asset: dict) -> RiskVector:
        """
        Simulate local inference on regional off-chain data.
        Each node has a different bias based on its region.
        """
        asset_id = asset.get("id", "unknown")
        asset_name = asset.get("name", "Unknown")

        # Base risk from asset fundamentals
        base_legal_risk = asset.get("legal_risk", 50)
        base_liquidity_risk = asset.get("liquidity_risk", 50)
        base_smart_contract_risk = asset.get("smart_contract_risk", 50)
        base_counterparty_risk = asset.get("counterparty_risk", 50)
        base_yield_sustainability = asset.get("yield_sustainability", 50)

        # Apply regional bias
        if self.bias == "risk_conservative":
            # Conservative nodes see higher risk
            legal_risk = min(100, base_legal_risk + random.gauss(5, 8))
            liquidity_risk = min(100, base_liquidity_risk + random.gauss(3, 6))
            smart_contract_risk = min(
                100, base_smart_contract_risk + random.gauss(5, 8))
            counterparty_risk = min(
                100, base_counterparty_risk + random.gauss(3, 7))
            yield_sustainability = max(
                0, base_yield_sustainability - random.gauss(5, 8))
            regional_sentiment = "bearish" if base_legal_risk > 60 else "neutral"

        elif self.bias == "risk_aggressive":
            # Aggressive nodes see lower risk
            legal_risk = max(0, base_legal_risk - random.gauss(5, 8))
            liquidity_risk = max(0, base_liquidity_risk - random.gauss(3, 6))
            smart_contract_risk = max(
                0, base_smart_contract_risk - random.gauss(5, 8))
            counterparty_risk = max(
                0, base_counterparty_risk - random.gauss(3, 7))
            yield_sustainability = min(
                100, base_yield_sustainability + random.gauss(5, 8))
            regional_sentiment = "bullish" if base_yield_sustainability > 60 else "neutral"

        else:  # balanced or tech_forward
            # Balanced nodes add small random noise
            legal_risk = max(0, min(100, base_legal_risk + random.gauss(0, 5)))
            liquidity_risk = max(
                0, min(100, base_liquidity_risk + random.gauss(0, 4)))
            smart_contract_risk = max(
                0, min(100, base_smart_contract_risk + random.gauss(0, 5)))
            counterparty_risk = max(
                0, min(100, base_counterparty_risk + random.gauss(0, 4)))
            yield_sustainability = max(
                0, min(100, base_yield_sustainability + random.gauss(0, 5)))
            regional_sentiment = "neutral"
            if base_yield_sustainability > 65:
                regional_sentiment = "bullish"
            elif base_legal_risk > 65:
                regional_sentiment = "bearish"

        # Composite score: weighted average (lower is safer)
        composite_risk_score = (
            legal_risk * 0.25 +
            liquidity_risk * 0.20 +
            smart_contract_risk * 0.20 +
            counterparty_risk * 0.20 +
            (100 - yield_sustainability) * 0.15
        )

        # Confidence varies by node; experienced nodes (high tokens) are more confident
        confidence_level = min(
            95, 40 + (self.cumulative_tokens / 500) * 30 + random.gauss(0, 5))

        # Local data signals
        local_signals = random.sample(
            self.local_data, k=min(2, len(self.local_data)))

        return RiskVector(
            node_name=self.node_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            asset_id=asset_id,
            asset_name=asset_name,
            legal_risk=max(0, min(100, legal_risk)),
            liquidity_risk=max(0, min(100, liquidity_risk)),
            smart_contract_risk=max(0, min(100, smart_contract_risk)),
            counterparty_risk=max(0, min(100, counterparty_risk)),
            yield_sustainability=max(0, min(100, yield_sustainability)),
            composite_risk_score=max(0, min(100, composite_risk_score)),
            confidence_level=max(0, min(100, confidence_level)),
            regional_sentiment=regional_sentiment,
            local_data_signals=local_signals,
        )

    def receive_reward(self, reward: PoAReward):
        """Record a reward received from the protocol."""
        self.historical_rewards.append(reward)
        self.cumulative_tokens += reward.tokens_mined
        self.accuracy_history.append(reward.accuracy_score)

    def get_stats(self) -> dict:
        """Get node performance statistics."""
        avg_accuracy = (
            sum(self.accuracy_history) / len(self.accuracy_history)
            if self.accuracy_history else 0
        )
        return {
            "node_name": self.node_name,
            "region": self.region,
            "timezone": self.timezone,
            "bias": self.bias,
            "cumulative_tokens": round(self.cumulative_tokens, 2),
            "tokens_mined_24h": round(sum(
                r.tokens_mined for r in self.historical_rewards
                if (datetime.fromisoformat(r.timestamp) >
                    datetime.now(timezone.utc) - timedelta(hours=24))
            ), 2),
            "total_predictions": len(self.accuracy_history),
            "avg_accuracy": round(avg_accuracy, 2),
            "latest_reward_tier": (
                self.historical_rewards[-1].reward_tier
                if self.historical_rewards else "none"
            ),
        }


class HiveMindProtocol:
    """
    Central protocol that:
    1. Collects Risk_Vectors from nodes
    2. Aggregates them to consensus
    3. Verifies predictions against actual outcomes
    4. Distributes PoA rewards
    5. Saves inference data to training_dataset.jsonl
    """

    def __init__(self, workspace_dir: str = "."):
        self.nodes: Dict[str, HiveMindNode] = {}
        self.workspace_dir = workspace_dir
        self.training_dataset_path = os.path.join(
            workspace_dir, TRAINING_DATASET_FILE)
        self.inference_history: List[dict] = []

        # Initialize nodes
        for node_name, config in NODES.items():
            self.nodes[node_name] = HiveMindNode(node_name, config)

    def submit_node_vectors(self, asset: dict) -> Dict[str, RiskVector]:
        """
        Have all nodes submit their Risk_Vectors for an asset.
        Returns: {node_name: RiskVector}
        """
        vectors = {}
        for node_name, node in self.nodes.items():
            risk_vector = node.run_local_inference(asset)
            vectors[node_name] = risk_vector
        return vectors

    def aggregate_consensus(
        self,
        vectors: Dict[str, RiskVector]
    ) -> dict:
        """
        Aggregate Risk_Vectors into a consensus score.
        Uses weighted average (nodes with higher cumulative_tokens get higher weight).
        """
        if not vectors:
            return {}

        total_weight = sum(
            self.nodes[name].cumulative_tokens for name in vectors.keys())

        weighted_composite = 0.0
        weighted_confidence = 0.0
        sentiment_votes = {"bullish": 0, "neutral": 0, "bearish": 0}

        for node_name, vector in vectors.items():
            weight = self.nodes[node_name].cumulative_tokens / total_weight
            weighted_composite += vector.composite_risk_score * weight
            weighted_confidence += vector.confidence_level * weight
            sentiment_votes[vector.regional_sentiment] += weight

        # Majority sentiment
        consensus_sentiment = max(sentiment_votes, key=sentiment_votes.get)

        return {
            "asset_id": list(vectors.values())[0].asset_id,
            "asset_name": list(vectors.values())[0].asset_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "consensus_composite_risk": round(weighted_composite, 2),
            "consensus_confidence": round(weighted_confidence, 2),
            "consensus_sentiment": consensus_sentiment,
            "num_nodes": len(vectors),
            "consensus_threshold": "safe" if weighted_composite < 45 else "risky",
        }

    def verify_and_reward(
        self,
        consensus: dict,
        vectors: Dict[str, RiskVector],
        # e.g., {"asset_stability": True, "yield_achieved": 5.2}
        actual_outcome: dict,
    ) -> List[PoAReward]:
        """
        Compare node predictions against actual outcomes.
        Distribute PoA rewards based on accuracy.
        """
        rewards = []

        consensus_risk = consensus["consensus_composite_risk"]
        actual_stability = actual_outcome.get("asset_stability", True)

        for node_name, vector in vectors.items():
            # Calculate accuracy: how close node was to consensus
            risk_diff = abs(vector.composite_risk_score - consensus_risk)
            accuracy = max(0, 100 - risk_diff)

            # Did node predict stability correctly?
            node_predicted_safe = vector.composite_risk_score < 45
            prediction_correct = (node_predicted_safe == actual_stability)

            # Determine reward tier
            if accuracy >= 95 and prediction_correct:
                reward_tier = "perfect_match"
                tokens = POA_REWARD_TIERS["perfect_match"]
            elif accuracy >= 90:
                reward_tier = "high_confidence"
                tokens = POA_REWARD_TIERS["high_confidence"]
            elif accuracy >= 75:
                reward_tier = "medium_confidence"
                tokens = POA_REWARD_TIERS["medium_confidence"]
            elif accuracy >= 50:
                reward_tier = "low_confidence"
                tokens = POA_REWARD_TIERS["low_confidence"]
            else:
                reward_tier = "consensus_miss"
                tokens = POA_REWARD_TIERS["consensus_miss"]

            reward = PoAReward(
                node_name=node_name,
                timestamp=datetime.now(timezone.utc).isoformat(),
                asset_id=consensus["asset_id"],
                accuracy_score=round(accuracy, 2),
                predicted_stability=prediction_correct,
                tokens_mined=tokens,
                reward_tier=reward_tier,
            )

            rewards.append(reward)
            self.nodes[node_name].receive_reward(reward)

        return rewards

    def save_training_data(
        self,
        consensus: dict,
        vectors: Dict[str, RiskVector],
        rewards: List[PoAReward],
    ):
        """
        Save aggregated inference data to training_dataset.jsonl for future RLHF.
        This represents the 'aggregated human/AI hive mind' collective knowledge.
        """
        training_record = {
            "timestamp": consensus["timestamp"],
            "asset_id": consensus["asset_id"],
            "asset_name": consensus["asset_name"],
            "consensus_composite_risk": consensus["consensus_composite_risk"],
            "consensus_confidence": consensus["consensus_confidence"],
            "consensus_sentiment": consensus["consensus_sentiment"],
            "num_nodes_participated": consensus["num_nodes"],
            "node_vectors": [v.to_dict() for v in vectors.values()],
            "rewards_distributed": [asdict(r) for r in rewards],
            "avg_accuracy_across_nodes": round(
                sum(r.accuracy_score for r in rewards) / len(rewards),
                2
            ) if rewards else 0,
        }

        # Append to JSONL file
        try:
            with open(self.training_dataset_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(training_record) + "\n")
        except Exception as e:
            print(f"Error saving training data: {e}")

    def process_asset(
        self,
        asset: dict,
        actual_outcome: Optional[dict] = None,
    ) -> dict:
        """
        Complete pipeline: submit → aggregate → verify → reward → save.
        """
        # 1. Submit vectors
        vectors = self.submit_node_vectors(asset)

        # 2. Aggregate consensus
        consensus = self.aggregate_consensus(vectors)

        # 3. Verify and reward (if actual outcome provided)
        rewards = []
        if actual_outcome:
            rewards = self.verify_and_reward(
                consensus, vectors, actual_outcome)

        # 4. Save training data
        self.save_training_data(consensus, vectors, rewards)

        # 5. Record in history
        self.inference_history.append({
            "consensus": consensus,
            "node_vectors": {k: v.to_dict() for k, v in vectors.items()},
            "rewards": [asdict(r) for r in rewards],
        })

        return {
            "consensus": consensus,
            "node_vectors": {k: v.to_dict() for k, v in vectors.items()},
            "rewards": [asdict(r) for r in rewards],
            "total_tokens_distributed": sum(r.tokens_mined for r in rewards),
        }

    def get_network_status(self) -> dict:
        """
        Get real-time status of the entire hive mind network.
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_nodes": len(self.nodes),
            "nodes_active": len([n for n in self.nodes.values() if n.cumulative_tokens > 0]),
            "nodes": {
                node_name: node.get_stats()
                for node_name, node in self.nodes.items()
            },
            "total_tokens_in_circulation": round(
                sum(n.cumulative_tokens for n in self.nodes.values()),
                2
            ),
            "training_dataset_records": len(self.inference_history),
            "training_dataset_file": self.training_dataset_path,
        }

    def get_leaderboard(self) -> List[dict]:
        """
        Get ranked leaderboard of nodes by performance.
        """
        leaderboard = []
        for node_name, node in self.nodes.items():
            stats = node.get_stats()
            leaderboard.append({
                "rank": 0,  # Will be set
                **stats,
            })

        # Sort by cumulative_tokens (descending)
        leaderboard.sort(key=lambda x: x["cumulative_tokens"], reverse=True)
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1

        return leaderboard


# ---------------------------------------------------------------------------
#  Demonstration / CLI Usage
# ---------------------------------------------------------------------------

def demo():
    """Demonstrate the Hive Mind Network."""
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║     HIVE MIND NETWORK — Federated Risk Intelligence    ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    # Initialize protocol
    protocol = HiveMindProtocol()

    # Sample RWA assets to evaluate
    assets = [
        {
            "id": "RWA001",
            "name": "MakerDAO Real Estate Fund",
            "legal_risk": 35,
            "liquidity_risk": 40,
            "smart_contract_risk": 30,
            "counterparty_risk": 25,
            "yield_sustainability": 70,
        },
        {
            "id": "RWA002",
            "name": "BlackRock Treasury ETF",
            "legal_risk": 15,
            "liquidity_risk": 20,
            "smart_contract_risk": 40,
            "counterparty_risk": 10,
            "yield_sustainability": 80,
        },
        {
            "id": "RWA003",
            "name": "Untested DeFi Protocol",
            "legal_risk": 75,
            "liquidity_risk": 85,
            "smart_contract_risk": 90,
            "counterparty_risk": 70,
            "yield_sustainability": 45,
        },
    ]

    # Process each asset
    for asset in assets:
        print(f"\n📊 Processing: {asset['name']} ({asset['id']})")
        print("─" * 60)

        # Simulate actual outcome
        actual_outcome = {
            "asset_stability": asset["legal_risk"] < 50,
            "yield_achieved": random.uniform(3, 8),
        }

        # Run full pipeline
        result = protocol.process_asset(asset, actual_outcome)

        # Display consensus
        consensus = result["consensus"]
        print(
            f"  Consensus Risk Score: {consensus['consensus_composite_risk']:.2f}/100")
        print(f"  Confidence Level: {consensus['consensus_confidence']:.1f}%")
        print(
            f"  Network Sentiment: {consensus['consensus_sentiment'].upper()}")
        print(f"  Status: {consensus['consensus_threshold'].upper()}")
        print(
            f"  Total Tokens Distributed: {result['total_tokens_distributed']:.1f} PHI")

        # Display node details
        print(f"\n  Node Submissions:")
        for node_name, vector in result["node_vectors"].items():
            node = protocol.nodes[node_name]
            print(f"    • {node_name} ({node.region})")
            print(f"      Risk Score: {vector['composite_risk_score']:.1f} | "
                  f"Confidence: {vector['confidence_level']:.1f}% | "
                  f"Sentiment: {vector['regional_sentiment']}")

    # Display network status
    print(f"\n\n═══════════════════════════════════════════════════════════")
    print("              HIVE MIND NETWORK STATUS")
    print("═══════════════════════════════════════════════════════════\n")

    status = protocol.get_network_status()
    print(
        f"Total Nodes Active: {status['nodes_active']}/{status['total_nodes']}")
    print(
        f"Total PHI Tokens in Circulation: {status['total_tokens_in_circulation']:.2f}\n")

    # Leaderboard
    print("🏆 NODE LEADERBOARD:")
    print("─" * 60)
    for entry in protocol.get_leaderboard():
        print(f"  {entry['rank']}. {entry['node_name']:<20} | "
              f"PHI: {entry['cumulative_tokens']:>8.1f} | "
              f"Accuracy: {entry['avg_accuracy']:>6.1f}% | "
              f"Predictions: {entry['total_predictions']:>3}")

    print(f"\n✅ Training dataset saved: {status['training_dataset_file']}")
    print(f"   Records: {status['training_dataset_records']}")


if __name__ == "__main__":
    demo()
