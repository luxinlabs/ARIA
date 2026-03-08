"""
Self-Improving Shared Decision Framework for ARIA Agents

This module implements a reinforcement learning-based decision framework
that allows agents to learn from outcomes and improve their strategies over time.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field

from pydantic import BaseModel, Field


@dataclass
class AgentDecision:
    """Represents a decision made by an agent."""
    agent_name: str
    decision_type: str  # hypothesis, creative, audience, budget, etc.
    decision_data: Dict[str, Any]
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionOutcome:
    """Tracks the outcome of a decision."""
    decision_id: str
    success: bool
    metrics: Dict[str, float]  # roas, ctr, cvr, etc.
    reward: float  # Calculated reward signal
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class AgentStrategy(BaseModel):
    """Learned strategy for an agent."""
    agent_name: str
    strategy_weights: Dict[str, float] = Field(default_factory=dict)
    success_rate: float = 0.0
    total_decisions: int = 0
    successful_decisions: int = 0
    average_reward: float = 0.0
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DecisionPattern(BaseModel):
    """Represents a learned pattern from past decisions."""
    pattern_id: str
    conditions: Dict[str, Any]  # Context conditions when pattern applies
    action: Dict[str, Any]  # What action to take
    success_rate: float = 0.0
    sample_size: int = 0
    confidence: float = 0.0
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SharedDecisionFramework:
    """
    Self-improving decision framework that learns from agent outcomes.
    
    Key Features:
    1. Tracks all agent decisions and their outcomes
    2. Calculates reward signals based on performance metrics
    3. Updates agent strategies using reinforcement learning
    4. Discovers and stores successful decision patterns
    5. Provides recommendations to agents based on learned knowledge
    """
    
    def __init__(self):
        self.agent_strategies: Dict[str, AgentStrategy] = {}
        self.decision_history: List[AgentDecision] = []
        self.outcome_history: List[DecisionOutcome] = []
        self.learned_patterns: List[DecisionPattern] = []
        
        # Learning parameters
        self.learning_rate = 0.1
        self.exploration_rate = 0.2  # Epsilon for epsilon-greedy
        self.discount_factor = 0.95  # Gamma for future rewards
        
        # Performance tracking
        self.performance_by_context: Dict[str, List[float]] = defaultdict(list)
        self.strategy_evolution: List[Dict[str, Any]] = []
        
    def record_decision(
        self,
        agent_name: str,
        decision_type: str,
        decision_data: Dict[str, Any],
        confidence: float,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record a decision made by an agent."""
        decision = AgentDecision(
            agent_name=agent_name,
            decision_type=decision_type,
            decision_data=decision_data,
            confidence=confidence,
            context=context or {}
        )
        self.decision_history.append(decision)
        
        # Initialize strategy if new agent
        if agent_name not in self.agent_strategies:
            self.agent_strategies[agent_name] = AgentStrategy(agent_name=agent_name)
        
        decision_id = f"{agent_name}_{len(self.decision_history)}"
        return decision_id
    
    def record_outcome(
        self,
        decision_id: str,
        success: bool,
        metrics: Dict[str, float]
    ) -> None:
        """Record the outcome of a decision and update learning."""
        # Calculate reward based on metrics
        reward = self._calculate_reward(metrics, success)
        
        outcome = DecisionOutcome(
            decision_id=decision_id,
            success=success,
            metrics=metrics,
            reward=reward
        )
        self.outcome_history.append(outcome)
        
        # Update agent strategy
        self._update_agent_strategy(decision_id, outcome)
        
        # Discover patterns
        self._discover_patterns(decision_id, outcome)
        
        # Track performance evolution
        self._track_performance_evolution()
    
    def _calculate_reward(self, metrics: Dict[str, float], success: bool) -> float:
        """
        Calculate reward signal from performance metrics.
        
        Reward function combines multiple metrics:
        - ROAS (primary)
        - CVR (conversion rate)
        - CTR (click-through rate)
        - Success flag (binary outcome)
        """
        reward = 0.0
        
        # ROAS contribution (weighted heavily)
        roas = metrics.get('roas', 0.0)
        reward += roas * 0.5
        
        # CVR contribution
        cvr = metrics.get('cvr', 0.0)
        reward += cvr * 100 * 0.3  # Scale CVR to similar magnitude
        
        # CTR contribution
        ctr = metrics.get('ctr', 0.0)
        reward += ctr * 100 * 0.1
        
        # Success bonus
        if success:
            reward += 1.0
        else:
            reward -= 0.5
        
        # CPA penalty (lower is better)
        cpa = metrics.get('cpa', 0.0)
        if cpa > 0:
            reward -= min(cpa / 100, 1.0) * 0.1
        
        return reward
    
    def _update_agent_strategy(
        self,
        decision_id: str,
        outcome: DecisionOutcome
    ) -> None:
        """Update agent strategy using reinforcement learning."""
        # Find the decision
        decision_idx = int(decision_id.split('_')[-1]) - 1
        if decision_idx >= len(self.decision_history):
            return
        
        decision = self.decision_history[decision_idx]
        agent_name = decision.agent_name
        
        if agent_name not in self.agent_strategies:
            return
        
        strategy = self.agent_strategies[agent_name]
        
        # Update statistics
        strategy.total_decisions += 1
        if outcome.success:
            strategy.successful_decisions += 1
        
        strategy.success_rate = (
            strategy.successful_decisions / strategy.total_decisions
            if strategy.total_decisions > 0 else 0.0
        )
        
        # Update average reward using exponential moving average
        alpha = self.learning_rate
        strategy.average_reward = (
            alpha * outcome.reward + (1 - alpha) * strategy.average_reward
        )
        
        # Update strategy weights based on decision features
        self._update_strategy_weights(strategy, decision, outcome)
        
        strategy.last_updated = datetime.now(UTC)
    
    def _update_strategy_weights(
        self,
        strategy: AgentStrategy,
        decision: AgentDecision,
        outcome: DecisionOutcome
    ) -> None:
        """Update strategy weights using Q-learning style updates."""
        # Extract features from decision
        features = self._extract_features(decision)
        
        for feature, value in features.items():
            current_weight = strategy.strategy_weights.get(feature, 0.0)
            
            # Q-learning update: Q(s,a) = Q(s,a) + α[r + γ*max(Q(s',a')) - Q(s,a)]
            # Simplified: weight = weight + learning_rate * (reward - weight)
            new_weight = current_weight + self.learning_rate * (outcome.reward - current_weight)
            
            strategy.strategy_weights[feature] = new_weight
    
    def _extract_features(self, decision: AgentDecision) -> Dict[str, float]:
        """Extract features from a decision for learning."""
        features = {}
        
        # Decision type feature
        features[f"type_{decision.decision_type}"] = 1.0
        
        # Confidence feature
        features["confidence"] = decision.confidence
        
        # Context features
        context = decision.context
        if "goal" in context:
            features[f"goal_{context['goal']}"] = 1.0
        
        if "budget_range" in context:
            features[f"budget_{context['budget_range']}"] = 1.0
        
        if "platform" in context:
            features[f"platform_{context['platform']}"] = 1.0
        
        # Decision-specific features
        data = decision.decision_data
        if "channel" in data:
            features[f"channel_{data['channel']}"] = 1.0
        
        if "creative_type" in data:
            features[f"creative_{data['creative_type']}"] = 1.0
        
        if "audience_segment" in data:
            features[f"audience_{data['audience_segment']}"] = 1.0
        
        return features
    
    def _discover_patterns(
        self,
        decision_id: str,
        outcome: DecisionOutcome
    ) -> None:
        """Discover successful patterns from decision outcomes."""
        decision_idx = int(decision_id.split('_')[-1]) - 1
        if decision_idx >= len(self.decision_history):
            return
        
        decision = self.decision_history[decision_idx]
        
        # Only learn from successful outcomes
        if not outcome.success or outcome.reward < 0.5:
            return
        
        # Create pattern from successful decision
        pattern_id = f"pattern_{len(self.learned_patterns) + 1}"
        
        pattern = DecisionPattern(
            pattern_id=pattern_id,
            conditions=decision.context.copy(),
            action=decision.decision_data.copy(),
            success_rate=1.0,  # Initial
            sample_size=1,
            confidence=decision.confidence
        )
        
        # Check if similar pattern exists
        similar_pattern = self._find_similar_pattern(pattern)
        
        if similar_pattern:
            # Update existing pattern
            similar_pattern.sample_size += 1
            similar_pattern.success_rate = (
                (similar_pattern.success_rate * (similar_pattern.sample_size - 1) + 1.0)
                / similar_pattern.sample_size
            )
            similar_pattern.confidence = min(
                similar_pattern.confidence + 0.05,
                0.99
            )
        else:
            # Add new pattern
            self.learned_patterns.append(pattern)
    
    def _find_similar_pattern(
        self,
        pattern: DecisionPattern
    ) -> Optional[DecisionPattern]:
        """Find a similar existing pattern."""
        for existing in self.learned_patterns:
            # Check if conditions match
            if self._patterns_similar(existing.conditions, pattern.conditions):
                if self._patterns_similar(existing.action, pattern.action):
                    return existing
        return None
    
    def _patterns_similar(
        self,
        dict1: Dict[str, Any],
        dict2: Dict[str, Any],
        threshold: float = 0.8
    ) -> bool:
        """Check if two dictionaries are similar."""
        if not dict1 or not dict2:
            return False
        
        common_keys = set(dict1.keys()) & set(dict2.keys())
        if len(common_keys) == 0:
            return False
        
        matches = sum(1 for k in common_keys if dict1[k] == dict2[k])
        similarity = matches / len(common_keys)
        
        return similarity >= threshold
    
    def _track_performance_evolution(self) -> None:
        """Track how performance evolves over time."""
        snapshot = {
            "timestamp": datetime.now(UTC).isoformat(),
            "total_decisions": len(self.decision_history),
            "total_outcomes": len(self.outcome_history),
            "patterns_discovered": len(self.learned_patterns),
            "agent_performance": {
                name: {
                    "success_rate": strategy.success_rate,
                    "average_reward": strategy.average_reward,
                    "total_decisions": strategy.total_decisions
                }
                for name, strategy in self.agent_strategies.items()
            }
        }
        self.strategy_evolution.append(snapshot)
    
    def get_recommendation(
        self,
        agent_name: str,
        decision_type: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get recommendation for an agent based on learned patterns.
        
        Uses epsilon-greedy strategy:
        - With probability epsilon: explore (return None for random choice)
        - With probability 1-epsilon: exploit (return best known pattern)
        """
        import random
        
        # Exploration: let agent make random choice
        if random.random() < self.exploration_rate:
            return None
        
        # Exploitation: find best matching pattern
        matching_patterns = [
            p for p in self.learned_patterns
            if self._context_matches(p.conditions, context)
            and p.success_rate > 0.6
        ]
        
        if not matching_patterns:
            return None
        
        # Sort by success rate and confidence
        best_pattern = max(
            matching_patterns,
            key=lambda p: p.success_rate * p.confidence
        )
        
        return {
            "action": best_pattern.action,
            "confidence": best_pattern.confidence,
            "success_rate": best_pattern.success_rate,
            "sample_size": best_pattern.sample_size,
            "pattern_id": best_pattern.pattern_id
        }
    
    def _context_matches(
        self,
        pattern_conditions: Dict[str, Any],
        current_context: Dict[str, Any]
    ) -> bool:
        """Check if current context matches pattern conditions."""
        if not pattern_conditions:
            return True
        
        for key, value in pattern_conditions.items():
            if key not in current_context:
                continue
            if current_context[key] != value:
                return False
        
        return True
    
    def get_agent_insights(self, agent_name: str) -> Dict[str, Any]:
        """Get insights about an agent's learning progress."""
        if agent_name not in self.agent_strategies:
            return {}
        
        strategy = self.agent_strategies[agent_name]
        
        # Find top performing features
        top_features = sorted(
            strategy.strategy_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "agent_name": agent_name,
            "success_rate": strategy.success_rate,
            "average_reward": strategy.average_reward,
            "total_decisions": strategy.total_decisions,
            "top_strategies": [
                {"feature": f, "weight": w}
                for f, w in top_features
            ],
            "learning_progress": self._calculate_learning_progress(agent_name)
        }
    
    def _calculate_learning_progress(self, agent_name: str) -> str:
        """Calculate learning progress stage."""
        strategy = self.agent_strategies.get(agent_name)
        if not strategy:
            return "not_started"
        
        if strategy.total_decisions < 5:
            return "exploring"
        elif strategy.total_decisions < 20:
            return "learning"
        elif strategy.success_rate > 0.7:
            return "optimized"
        else:
            return "adapting"
    
    def export_knowledge(self) -> Dict[str, Any]:
        """Export learned knowledge for persistence."""
        return {
            "agent_strategies": {
                name: strategy.model_dump(mode="json")
                for name, strategy in self.agent_strategies.items()
            },
            "learned_patterns": [
                p.model_dump(mode="json")
                for p in self.learned_patterns
            ],
            "performance_evolution": self.strategy_evolution,
            "total_decisions": len(self.decision_history),
            "total_outcomes": len(self.outcome_history)
        }
    
    def import_knowledge(self, knowledge: Dict[str, Any]) -> None:
        """Import previously learned knowledge."""
        # Import agent strategies
        for name, strategy_data in knowledge.get("agent_strategies", {}).items():
            self.agent_strategies[name] = AgentStrategy.model_validate(strategy_data)
        
        # Import learned patterns
        for pattern_data in knowledge.get("learned_patterns", []):
            self.learned_patterns.append(DecisionPattern.model_validate(pattern_data))
        
        # Import performance evolution
        self.strategy_evolution = knowledge.get("performance_evolution", [])


# Global shared decision framework instance
shared_framework = SharedDecisionFramework()
