# Self-Improving Shared Decision Framework

## Overview

ARIA implements a **reinforcement learning-based shared decision framework** that enables all agents to learn from outcomes and continuously improve their strategies. This creates a self-improving system where agents get better over time through experience.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│           Shared Decision Framework (Global)                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Agent Strategies (Learned Weights)                    │ │
│  │  - Strategist: hypothesis_generation → 0.87 success    │ │
│  │  - Creative: variant_generation → 0.79 success         │ │
│  │  - Audience: segment_optimization → 0.82 success       │ │
│  │  - Budget: allocation_strategy → 0.91 success          │ │
│  │  - Evaluate: outcome_prediction → 0.85 success         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Decision History (All Agent Actions)                  │ │
│  │  - Decision ID, Agent, Type, Data, Confidence, Context │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Outcome History (Performance Results)                 │ │
│  │  - Decision ID, Success, Metrics (ROAS, CTR, CVR, CPA) │ │
│  │  - Calculated Reward Signal                            │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Learned Patterns (Discovered Knowledge)               │ │
│  │  - Conditions → Actions with Success Rates             │ │
│  │  - Pattern ID, Sample Size, Confidence                 │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↕
        ┌───────────────────────────────────────┐
        │  Agent Collaboration via LangGraph    │
        │                                       │
        │  Observe → Strategist → Creative →   │
        │  Audience → Budget → Execute →        │
        │  Evaluate → Learn → Notify            │
        └───────────────────────────────────────┘
```

## How It Works

### 1. Decision Recording

When an agent makes a decision, it's recorded in the shared framework:

```python
decision_id = shared_framework.record_decision(
    agent_name="strategist",
    decision_type="hypothesis_generation",
    decision_data={
        "hypotheses": ["Trust beats discount", "Stories > Search"],
        "channel_mix": ["meta", "google"],
        "angle": "trust_social_proof"
    },
    confidence=0.87,
    context={
        "goal": "purchases",
        "budget_range": "high",
        "meta_roas": 3.8,
        "google_roas": 2.9
    }
)
```

**What's Tracked:**
- Agent name and decision type
- Decision data (what was chosen)
- Confidence level
- Context (market conditions, budget, goals)

### 2. Outcome Recording

After experiments run, outcomes are recorded with performance metrics:

```python
shared_framework.record_outcome(
    decision_id=decision_id,
    success=True,  # Hypothesis confirmed
    metrics={
        "roas": 4.2,
        "ctr": 0.035,
        "cvr": 0.028,
        "cpa": 23.50
    }
)
```

**Reward Calculation:**
The framework calculates a reward signal combining multiple metrics:

```
Reward = (ROAS × 0.5) + (CVR × 100 × 0.3) + (CTR × 100 × 0.1) 
         + Success_Bonus(1.0) - CPA_Penalty(0.1)
```

### 3. Strategy Updates (Reinforcement Learning)

The framework uses **Q-learning** style updates to improve agent strategies:

```
New_Weight = Current_Weight + Learning_Rate × (Reward - Current_Weight)
```

**Learning Parameters:**
- Learning Rate (α): 0.1 - How quickly to adapt
- Exploration Rate (ε): 0.2 - Balance exploration vs exploitation
- Discount Factor (γ): 0.95 - Value of future rewards

### 4. Pattern Discovery

Successful decisions are analyzed to discover reusable patterns:

```python
pattern = {
    "conditions": {
        "goal": "purchases",
        "budget_range": "high",
        "meta_roas": "> 3.0"
    },
    "action": {
        "angle": "trust_social_proof",
        "channel_mix": ["meta", "google"],
        "primary_platform": "meta"
    },
    "success_rate": 0.87,
    "sample_size": 12,
    "confidence": 0.92
}
```

### 5. Recommendation System

Agents query the framework for recommendations before making decisions:

```python
recommendation = shared_framework.get_recommendation(
    agent_name="strategist",
    decision_type="hypothesis_generation",
    context=current_context
)

if recommendation:
    # Use learned best practice (exploit)
    use_pattern(recommendation['action'])
else:
    # Explore new strategies
    generate_novel_hypothesis()
```

**Epsilon-Greedy Strategy:**
- 80% of time: Use best known pattern (exploit)
- 20% of time: Try new approaches (explore)

## Agent Integration

### Growth Strategist Agent

**Before (Static):**
```python
def growth_strategist_agent(state):
    # Always generates same type of hypotheses
    hypotheses = generate_hypotheses(brand_info)
    return hypotheses
```

**After (Self-Improving):**
```python
def growth_strategist_agent(state):
    # Check for learned recommendations
    context = extract_context(state)
    recommendation = shared_framework.get_recommendation(
        agent_name="strategist",
        decision_type="hypothesis_generation",
        context=context
    )
    
    # Enhance AI prompt with learned insights
    if recommendation:
        prompt += f"Learned insights (success rate: {recommendation['success_rate']}):\n"
        prompt += json.dumps(recommendation['action'])
    
    hypotheses = generate_hypotheses(prompt)
    
    # Record decision for learning
    decision_id = shared_framework.record_decision(
        agent_name="strategist",
        decision_type="hypothesis_generation",
        decision_data=hypotheses,
        confidence=0.87,
        context=context
    )
    
    return hypotheses, decision_id
```

### Experiment Evaluation Agent

**Records Outcomes:**
```python
def experiment_evaluation_agent(state):
    verdict = evaluate_experiment(state)
    
    # Record outcome in framework
    if "strategist_decision_id" in state:
        metrics = extract_metrics(state)
        success = verdict.outcome == "CONFIRMED"
        
        shared_framework.record_outcome(
            decision_id=state["strategist_decision_id"],
            success=success,
            metrics=metrics
        )
    
    return verdict
```

## Learning Progression

### Stage 1: Exploring (0-5 decisions)
- Agents try various strategies
- No patterns yet discovered
- High exploration rate
- Building initial knowledge

### Stage 2: Learning (5-20 decisions)
- Patterns start emerging
- Success rates calculated
- Strategy weights updated
- Balancing exploration/exploitation

### Stage 3: Optimized (20+ decisions, >70% success)
- Strong patterns established
- High confidence recommendations
- Consistent performance
- Fine-tuning strategies

### Stage 4: Adapting (20+ decisions, <70% success)
- Market conditions changed
- Re-exploring strategies
- Updating patterns
- Continuous improvement

## API Endpoints

### Get Learning Insights

```bash
GET /aria/learning/insights
```

**Response:**
```json
{
  "agent_insights": {
    "strategist": {
      "agent_name": "strategist",
      "success_rate": 0.87,
      "average_reward": 2.34,
      "total_decisions": 15,
      "top_strategies": [
        {"feature": "type_hypothesis_generation", "weight": 2.1},
        {"feature": "goal_purchases", "weight": 1.8},
        {"feature": "channel_meta", "weight": 1.6}
      ],
      "learning_progress": "optimized"
    }
  },
  "total_decisions": 45,
  "total_outcomes": 38,
  "patterns_discovered": 12,
  "learning_enabled": true,
  "top_patterns": [
    {
      "pattern_id": "pattern_5",
      "success_rate": 0.92,
      "sample_size": 8,
      "confidence": 0.89
    }
  ]
}
```

### Export Knowledge

```bash
GET /aria/learning/export
```

Exports all learned knowledge for:
- Backup/restore
- Analysis
- Transfer to other instances

## Performance Tracking

### Metrics Tracked

1. **Agent Success Rates**
   - Percentage of successful decisions per agent
   - Trend over time

2. **Average Rewards**
   - Exponential moving average of rewards
   - Indicates overall performance improvement

3. **Pattern Discovery Rate**
   - Number of patterns discovered per 10 decisions
   - Shows learning velocity

4. **Strategy Evolution**
   - How strategy weights change over time
   - Identifies effective features

### Visualization

The framework tracks performance evolution:

```python
{
  "timestamp": "2026-03-07T15:30:00Z",
  "total_decisions": 45,
  "patterns_discovered": 12,
  "agent_performance": {
    "strategist": {
      "success_rate": 0.87,
      "average_reward": 2.34,
      "total_decisions": 15
    }
  }
}
```

## Benefits

### 1. Continuous Improvement
- Agents get better with each cycle
- No manual tuning required
- Adapts to changing market conditions

### 2. Knowledge Accumulation
- Successful patterns preserved
- Failed strategies avoided
- Institutional memory built

### 3. Context-Aware Decisions
- Recommendations based on current conditions
- Patterns matched to similar situations
- Personalized to brand/goal/budget

### 4. Explainable AI
- Clear decision tracking
- Success rates visible
- Pattern conditions documented

### 5. Risk Management
- Exploration ensures innovation
- Exploitation leverages proven strategies
- Balanced approach prevents stagnation

## Example Learning Scenario

### Iteration 1: Initial Exploration
```
Strategist Decision: "Discount hook beats testimonial"
Context: {goal: "purchases", budget: "low"}
Outcome: REJECTED (ROAS: 2.1)
Reward: -0.3
Learning: Discount doesn't work for this brand
```

### Iteration 2: Adaptation
```
Strategist Decision: "Testimonial hook beats discount"
Context: {goal: "purchases", budget: "low"}
Outcome: CONFIRMED (ROAS: 3.8)
Reward: +2.4
Learning: Trust signals effective
Pattern Discovered: trust_over_discount
```

### Iteration 3: Exploitation
```
Strategist receives recommendation:
  Pattern: trust_over_discount
  Success Rate: 100%
  Confidence: 0.85

Strategist Decision: "Social proof testimonial variant"
Context: {goal: "purchases", budget: "medium"}
Outcome: CONFIRMED (ROAS: 4.2)
Reward: +2.8
Pattern Updated: success_rate → 100%, confidence → 0.92
```

### Iteration 4: Generalization
```
Framework recognizes pattern applies to:
- All purchase goals
- Medium/high budgets
- B2C brands
- Trust-seeking audiences

Recommendation now available for similar contexts
```

## Advanced Features

### 1. Transfer Learning
Export knowledge from one ARIA instance and import to another:

```python
# Export from production
knowledge = shared_framework.export_knowledge()

# Import to new instance
new_framework.import_knowledge(knowledge)
```

### 2. A/B Testing Strategies
Compare learning-enabled vs static agents:

```python
# Group A: Learning enabled
framework_a.exploration_rate = 0.2

# Group B: Pure exploitation
framework_b.exploration_rate = 0.0

# Compare performance after 50 decisions
```

### 3. Custom Reward Functions
Tailor reward calculation to business goals:

```python
def custom_reward(metrics, success):
    # Prioritize CVR over ROAS
    return metrics['cvr'] * 200 + (1.0 if success else -0.5)

framework.calculate_reward = custom_reward
```

## Best Practices

### 1. Sufficient Sample Size
- Need 10+ decisions per pattern for confidence
- Don't trust patterns with sample_size < 5

### 2. Context Consistency
- Use consistent context keys across decisions
- Enables pattern matching

### 3. Regular Exports
- Export knowledge weekly for backup
- Prevents loss of learning

### 4. Monitor Exploration Rate
- Too high (>0.3): Slow learning
- Too low (<0.1): Stagnation risk
- Optimal: 0.15-0.25

### 5. Reward Tuning
- Adjust weights based on business priorities
- Test reward function changes carefully

## Future Enhancements

- [ ] Multi-armed bandit algorithms
- [ ] Contextual bandits for better recommendations
- [ ] Deep Q-learning for complex state spaces
- [ ] Meta-learning across multiple brands
- [ ] Automated hyperparameter tuning
- [ ] Real-time performance dashboards
- [ ] Pattern similarity clustering
- [ ] Causal inference for decision impact

## Conclusion

The self-improving shared decision framework transforms ARIA from a static agent system into a **continuously learning AI** that gets smarter with every campaign. By recording decisions, tracking outcomes, and discovering patterns, all agents collaborate through a shared knowledge base that improves over time.

**Key Achievement:** ARIA now has true **institutional memory** and **self-improvement capabilities**, making it a genuinely autonomous advertising intelligence system.
