"""
⚖️ Zair Validator — Consensus Aggregation & PoA Reward Distribution

Central hub that:
1. Collects Risk Vectors from all miners
2. Aggregates into consensus via weighted voting
3. Verifies accuracy (Proof of Alpha) when asset outcome is known
4. Distributes PHI tokens to accurate miners
5. Records training data for RLHF

Runs as persistent server (FastAPI).

Usage:
    python validator.py --port 8001
"""

import json
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from enum import Enum
import statistics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RewardTier(Enum):
    """PHI token reward tiers based on accuracy"""
    PERFECT_MATCH = 100.0      # ≥95% accuracy, correct prediction
    HIGH_CONFIDENCE = 75.0     # ≥90% accuracy
    MEDIUM_CONFIDENCE = 50.0   # ≥75% accuracy
    LOW_CONFIDENCE = 25.0      # ≥50% accuracy
    CONSENSUS_MISS = 0.0       # <50% accuracy


@dataclass
class SubmittedVector:
    """A Risk Vector submitted by a mining node"""
    node_name: str
    asset_id: str
    composite_risk_score: float
    confidence_level: float
    regional_sentiment: str
    timestamp: str
    full_vector: Dict


@dataclass
class PoAReward:
    """Proof of Alpha reward for a mining node"""
    node_name: str
    asset_id: str
    timestamp: str

    # Accuracy calculation
    predicted_risk: float        # Node's composite_risk_score
    consensus_risk: float        # Aggregated consensus
    accuracy_percentage: float   # How close (0-100)

    # Verification
    actual_stability: Optional[bool]  # Ground truth (if known)
    prediction_correct: Optional[bool]  # Node predicted correctly

    # Reward
    tokens_mined: float         # PHI tokens earned
    reward_tier: str            # Tier name


@dataclass
class ConsensusResult:
    """Aggregated consensus for an asset"""
    asset_id: str
    timestamp: str

    # Consensus values
    consensus_composite_risk: float
    consensus_confidence: float
    consensus_sentiment: str
    num_nodes_participated: int

    # Safety assessment
    risk_threshold: float = 45.0  # Safe if < threshold
    is_safe: bool = field(init=False)

    def __post_init__(self):
        self.is_safe = self.consensus_composite_risk < self.risk_threshold


@dataclass
class TrainingDataRecord:
    """Single record for RLHF training dataset"""
    timestamp: str
    asset_id: str
    asset_name: str

    # Consensus
    consensus_composite_risk: float
    consensus_confidence: float
    consensus_sentiment: str
    num_nodes_participated: int

    # Raw node data
    node_vectors: List[Dict]

    # Reward distribution
    rewards_distributed: List[Dict]

    # Performance metrics
    avg_accuracy_across_nodes: float
    total_tokens_distributed: float


class ConsensusAggregator:
    """Aggregates Risk Vectors into weighted consensus"""

    def __init__(self):
        self.node_reputation = {}  # node_name -> cumulative_tokens
        self.reputation_history = {}  # node_name -> [tokens over time]

    def aggregate(self, vectors: List[SubmittedVector]) -> ConsensusResult:
        """
        Aggregate multiple Risk Vectors into consensus

        Uses weighted averaging where weight = node's cumulative_tokens
        (More accurate nodes get higher voting power)

        Args:
            vectors: List of RiskVector submissions from miners

        Returns:
            ConsensusResult with aggregated assessment
        """
        if not vectors:
            raise ValueError("No vectors to aggregate")

        # Calculate weights based on node reputation
        weights = self._calculate_weights([v.node_name for v in vectors])

        # Weighted average of composite risk
        weighted_risks = [
            v.composite_risk_score *
            weights.get(v.node_name, 1.0 / len(vectors))
            for v in vectors
        ]
        consensus_risk = sum(weighted_risks)

        # Average confidence
        avg_confidence = statistics.mean([v.confidence_level for v in vectors])

        # Majority vote on sentiment
        sentiments = [v.regional_sentiment for v in vectors]
        consensus_sentiment = max(set(sentiments), key=sentiments.count)

        # Create consensus result
        asset_id = vectors[0].asset_id
        return ConsensusResult(
            asset_id=asset_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            consensus_composite_risk=round(consensus_risk, 2),
            consensus_confidence=round(avg_confidence, 2),
            consensus_sentiment=consensus_sentiment,
            num_nodes_participated=len(vectors)
        )

    def _calculate_weights(self, node_names: List[str]) -> Dict[str, float]:
        """
        Calculate voting weights based on cumulative tokens

        Meritocratic: accurate nodes accumulate more tokens → more voting power
        """
        # Initialize if needed
        for node in node_names:
            if node not in self.node_reputation:
                self.node_reputation[node] = 500.0  # Bootstrap reputation

        # Get reputation scores
        scores = {node: self.node_reputation[node] for node in node_names}
        total_score = sum(scores.values())

        # Normalize to weights
        return {node: score / total_score for node, score in scores.items()}

    def update_reputation(self, node_name: str, tokens_earned: float):
        """Update node's cumulative token reputation"""
        if node_name not in self.node_reputation:
            self.node_reputation[node_name] = 500.0

        self.node_reputation[node_name] += tokens_earned

        # Track history for analytics
        if node_name not in self.reputation_history:
            self.reputation_history[node_name] = []
        self.reputation_history[node_name].append(
            self.node_reputation[node_name])


class PoAVerifier:
    """Verifies accuracy and distributes Proof of Alpha rewards"""

    def verify_and_reward(
        self,
        vectors: List[SubmittedVector],
        consensus: ConsensusResult,
        actual_stability: bool
    ) -> List[PoAReward]:
        """
        Verify nodes' predictions against ground truth
        Distribute PHI tokens based on accuracy

        Args:
            vectors: All submitted Risk Vectors
            consensus: Aggregated consensus
            actual_stability: Ground truth outcome

        Returns:
            List of PoAReward for each node
        """
        rewards = []

        for vector in vectors:
            # Calculate accuracy: how close was prediction to consensus?
            accuracy = self._calculate_accuracy(
                vector.composite_risk_score,
                consensus.consensus_composite_risk
            )

            # Was prediction correct? (≤45 = SAFE, >45 = RISKY)
            predicted_safe = vector.composite_risk_score <= 45.0
            actual_safe = actual_stability
            prediction_correct = predicted_safe == actual_safe

            # Determine reward tier
            reward_tier, tokens = self._determine_reward(
                accuracy, prediction_correct
            )

            reward = PoAReward(
                node_name=vector.node_name,
                asset_id=vector.asset_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                predicted_risk=vector.composite_risk_score,
                consensus_risk=consensus.consensus_composite_risk,
                accuracy_percentage=round(accuracy, 2),
                actual_stability=actual_stability,
                prediction_correct=prediction_correct,
                tokens_mined=tokens,
                reward_tier=reward_tier
            )
            rewards.append(reward)

        return rewards

    def _calculate_accuracy(self, predicted: float, consensus: float) -> float:
        """
        Calculate accuracy as inverse of error
        100% = perfect prediction (0% error)
        50% = 50 point error (max tolerable)
        """
        error = abs(predicted - consensus)
        accuracy = max(0, 100 - error)  # Capped at 0
        return min(100, accuracy)  # Capped at 100

    def _determine_reward(self, accuracy: float, prediction_correct: bool) -> Tuple[str, float]:
        """Determine reward tier and token amount"""
        if not prediction_correct:
            return "consensus_miss", 0.0

        if accuracy >= 95:
            return "perfect_match", RewardTier.PERFECT_MATCH.value
        elif accuracy >= 90:
            return "high_confidence", RewardTier.HIGH_CONFIDENCE.value
        elif accuracy >= 75:
            return "medium_confidence", RewardTier.MEDIUM_CONFIDENCE.value
        elif accuracy >= 50:
            return "low_confidence", RewardTier.LOW_CONFIDENCE.value
        else:
            return "consensus_miss", 0.0


class HiveMindValidator:
    """Main validator orchestrator"""

    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = Path(
            workspace_dir) if workspace_dir else Path(".")
        self.aggregator = ConsensusAggregator()
        self.verifier = PoAVerifier()
        self.training_data_path = self.workspace_dir / "training_dataset.jsonl"
        self.processing_queue = {}  # asset_id -> [vectors]
        self.processed_assets = {}  # asset_id -> result

    async def receive_vector(self, vector_dict: Dict) -> Dict:
        """
        Receive and queue a Risk Vector from mining node

        Returns acknowledgment
        """
        asset_id = vector_dict.get('asset_id')
        node_name = vector_dict.get('node_name')

        logger.info(f"📥 Received vector from {node_name} for {asset_id}")

        # Create SubmittedVector
        vector = SubmittedVector(
            node_name=node_name,
            asset_id=asset_id,
            composite_risk_score=vector_dict.get('composite_risk_score', 50),
            confidence_level=vector_dict.get('confidence_level', 50),
            regional_sentiment=vector_dict.get(
                'regional_sentiment', 'neutral'),
            timestamp=vector_dict.get(
                'timestamp', datetime.now(timezone.utc).isoformat()),
            full_vector=vector_dict
        )

        # Queue for this asset
        if asset_id not in self.processing_queue:
            self.processing_queue[asset_id] = []
        self.processing_queue[asset_id].append(vector)

        return {
            "status": "received",
            "asset_id": asset_id,
            "node_name": node_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def process_asset(
        self,
        asset_id: str,
        asset_name: str,
        actual_stability: bool
    ) -> Dict:
        """
        Process all vectors for an asset
        Aggregate consensus → verify accuracy → distribute rewards → save training data

        Args:
            asset_id: RWA asset identifier
            asset_name: Human-readable asset name
            actual_stability: Ground truth (outcome after settlement)

        Returns:
            Complete processing result
        """
        logger.info(f"🔄 Processing asset {asset_id}...")

        # Get vectors for this asset
        vectors = self.processing_queue.get(asset_id, [])

        if not vectors:
            logger.warning(f"⚠️  No vectors for {asset_id}")
            return {"error": f"No vectors received for {asset_id}"}

        # Step 1: Aggregate consensus
        consensus = self.aggregator.aggregate(vectors)
        logger.info(
            f"✓ Consensus: {consensus.consensus_composite_risk}/100 ({consensus.consensus_sentiment})")

        # Step 2: Verify and reward
        rewards = self.verifier.verify_and_reward(
            vectors, consensus, actual_stability)
        logger.info(f"✓ Rewards: {len(rewards)} nodes rewarded")

        # Step 3: Update node reputation
        total_tokens = 0
        for reward in rewards:
            self.aggregator.update_reputation(
                reward.node_name, reward.tokens_mined)
            total_tokens += reward.tokens_mined
            logger.info(
                f"  {reward.node_name}: {reward.tokens_mined} PHI "
                f"(accuracy: {reward.accuracy_percentage}%)"
            )

        # Step 4: Save training data
        await self._save_training_data(
            asset_id, asset_name, consensus, vectors, rewards, total_tokens
        )

        result = {
            "asset_id": asset_id,
            "consensus": asdict(consensus),
            "num_nodes": len(vectors),
            "node_vectors": [asdict(v) for v in vectors],
            "rewards": [asdict(r) for r in rewards],
            "total_tokens_distributed": total_tokens,
            "training_data_saved": True
        }

        self.processed_assets[asset_id] = result
        logger.info(f"✓ Processing complete for {asset_id}\n")

        return result

    async def _save_training_data(
        self,
        asset_id: str,
        asset_name: str,
        consensus: ConsensusResult,
        vectors: List[SubmittedVector],
        rewards: List[PoAReward],
        total_tokens: float
    ):
        """Save complete inference cycle to RLHF training dataset"""

        # Calculate average accuracy
        accuracies = [r.accuracy_percentage for r in rewards]
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0

        # Create training record
        record = TrainingDataRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            asset_id=asset_id,
            asset_name=asset_name,
            consensus_composite_risk=consensus.consensus_composite_risk,
            consensus_confidence=consensus.consensus_confidence,
            consensus_sentiment=consensus.consensus_sentiment,
            num_nodes_participated=consensus.num_nodes_participated,
            node_vectors=[asdict(v.full_vector) for v in vectors],
            rewards_distributed=[asdict(r) for r in rewards],
            avg_accuracy_across_nodes=round(avg_accuracy, 2),
            total_tokens_distributed=total_tokens
        )

        # Append to JSONL file
        try:
            with open(self.training_data_path, 'a') as f:
                f.write(json.dumps(asdict(record)) + '\n')
            logger.info(
                f"💾 Training data saved to {self.training_data_path.name}")
        except Exception as e:
            logger.error(f"Failed to save training data: {e}")

    def get_network_status(self) -> Dict:
        """Get current network status"""
        return {
            "validators": 1,
            "miners_registered": len(self.aggregator.node_reputation),
            "nodes": [
                {
                    "name": name,
                    "cumulative_tokens": tokens,
                    "predictions": len(self.reputation_history.get(name, []))
                }
                for name, tokens in self.aggregator.node_reputation.items()
            ],
            "total_tokens_in_circulation": sum(self.aggregator.node_reputation.values()),
            "assets_processed": len(self.processed_assets),
            "training_dataset_records": self._count_training_records()
        }

    def get_leaderboard(self, top_n: int = 10) -> List[Dict]:
        """Get node leaderboard by reputation"""
        sorted_nodes = sorted(
            self.aggregator.node_reputation.items(),
            key=lambda x: x[1],
            reverse=True
        )

        leaderboard = []
        for rank, (name, tokens) in enumerate(sorted_nodes[:top_n], 1):
            history = self.reputation_history.get(name, [])
            predictions = len(history)
            accuracy = self._calculate_node_accuracy(name)

            leaderboard.append({
                "rank": rank,
                "node_name": name,
                "cumulative_tokens": round(tokens, 2),
                "accuracy_percentage": round(accuracy, 2),
                "total_predictions": predictions
            })

        return leaderboard

    def _calculate_node_accuracy(self, node_name: str) -> float:
        """Calculate average accuracy for a node across all assets"""
        accuracies = []
        for result in self.processed_assets.values():
            for reward in result.get('rewards', []):
                if reward['node_name'] == node_name:
                    accuracies.append(reward['accuracy_percentage'])

        return sum(accuracies) / len(accuracies) if accuracies else 0

    def _count_training_records(self) -> int:
        """Count JSONL training records"""
        try:
            if self.training_data_path.exists():
                with open(self.training_data_path, 'r') as f:
                    return sum(1 for _ in f)
        except:
            pass
        return 0


def main():
    """Demo: Validator processing assets"""

    logger.info("=" * 60)
    logger.info("⚖️  ZAIR VALIDATOR — PoA VERIFICATION DEMO")
    logger.info("=" * 60)

    validator = HiveMindValidator()

    # Simulate 5 miners submitting vectors
    miners = [
        {"node_name": "Node_Dubai", "composite_risk": 40.9},
        {"node_name": "Node_WallStreet", "composite_risk": 31.6},
        {"node_name": "Node_Singapore", "composite_risk": 34.7},
        {"node_name": "Node_Frankfurt", "composite_risk": 31.5},
        {"node_name": "Node_Tokyo", "composite_risk": 26.6},
    ]

    # Step 1: Receive vectors
    logger.info("\n1️⃣  RECEIVING VECTORS FROM MINERS")
    logger.info("-" * 60)

    for miner in miners:
        vector = {
            "node_name": miner["node_name"],
            "asset_id": "RWA001",
            "composite_risk_score": miner["composite_risk"],
            "confidence_level": 60 + (hash(miner["node_name"]) % 20),
            "regional_sentiment": "bullish",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        asyncio.run(validator.receive_vector(vector))

    # Step 2: Process asset
    logger.info("\n2️⃣  PROCESSING ASSET & AGGREGATING CONSENSUS")
    logger.info("-" * 60)

    result = asyncio.run(validator.process_asset(
        asset_id="RWA001",
        asset_name="MakerDAO Real Estate Fund",
        actual_stability=True  # Asset was stable
    ))

    logger.info("\n3️⃣  RESULT SUMMARY")
    logger.info("-" * 60)
    logger.info(
        f"Consensus Risk: {result['consensus']['consensus_composite_risk']}/100")
    logger.info(
        f"Network Sentiment: {result['consensus']['consensus_sentiment']}")
    logger.info(f"Nodes Participated: {result['num_nodes']}")
    logger.info(
        f"Total Tokens Distributed: {result['total_tokens_distributed']} PHI")

    logger.info("\n4️⃣  LEADERBOARD")
    logger.info("-" * 60)
    leaderboard = validator.get_leaderboard()
    for entry in leaderboard:
        logger.info(
            f"  #{entry['rank']}: {entry['node_name']} "
            f"| {entry['cumulative_tokens']} PHI "
            f"| {entry['accuracy_percentage']}% accuracy"
        )

    logger.info("\n" + "=" * 60)
    logger.info("✓ Demo complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
