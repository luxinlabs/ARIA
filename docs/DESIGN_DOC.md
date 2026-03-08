# ARIA System Design Document

## Executive Summary

ARIA (Autonomous Revenue Intelligence Agent) is an AI-powered advertising optimization system that autonomously manages multi-platform ad campaigns through continuous experimentation, learning, and adaptation. The system uses LangGraph orchestration to coordinate specialized agents that observe signals, generate strategies, create content, optimize audiences, allocate budgets, execute campaigns, and evaluate results.

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React/Vite)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Dashboard   │  │  Comparison  │  │  Live Feed   │      │
│  │    View      │  │     Lab      │  │  (WebSocket) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                    HTTP/WebSocket
                            │
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI/Python)                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              REST API Routes (/aria/*)                │  │
│  │  init, status, memory, strategy, compare, step, etc. │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            InMemoryRuntime (State Manager)            │  │
│  │  - Multiple ARIAState sessions keyed by run_id        │  │
│  │  - Active-session selection + per-session operations  │  │
│  │  - Event broadcasting                                 │  │
│  │  - Concurrency control (asyncio.Lock)                │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         LangGraph Orchestration (graph.py)            │  │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  │  │
│  │  │Signal│→│Strat │→│Create│→│Audit │→│Budget│  │  │
│  │  │ Obs  │  │egist │  │ive  │  │ience │  │Alloc │  │  │
│  │  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘  │  │
│  │      ↓         ↓         ↓         ↓         ↓       │  │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  │  │
│  │  │Exec  │→│Eval  │→│Learn │→│Notify│→│Memory│  │  │
│  │  │ution │  │uation│  │      │  │      │  │Write │  │  │
│  │  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              OpenAI API Integration                   │  │
│  │  - Strategy generation (init_run)                     │  │
│  │  - Agent reasoning (GPT-4o)                           │  │
│  │  - Platform comparison analysis                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                    External APIs
                            │
┌─────────────────────────────────────────────────────────────┐
│              Ad Platforms (via Composio)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Google Ads  │  │   Meta Ads   │  │  TikTok Ads  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Frontend (`/frontend`)

**Technology Stack:**

- React 18.3.1
- Vite 6.1.1 (build tool)
- React Router 6.22.0 (navigation)
- Framer Motion 11.0.0 (animations)
- Lucide React 0.344.0 (icons)
- Project-native CSS (`src/styles.css`)

**Key Files:**

- `src/main.jsx` - Application entry point with routing
- `src/App.jsx` - Main dashboard component
- `src/components/PlatformComparison3D.jsx` - Platform comparison lab
- `src/components/MemoryView.jsx` - Shared memory page
- `src/components/AgentLogs.jsx` - Agent log timeline page
- `src/api.js` - Backend API wrapper

**Routes:**

- `/` - Main ARIA dashboard
- `/compare` - Platform comparison lab
- `/memory` - Shared memory viewer/editor surface
- `/logs` - Agent execution logs and active-agent status

**Features:**

- Real-time event feed via WebSocket (`/aria/live`)
- Interactive initialization form
- Session selector for multiple concurrent runs
- Agent status monitoring
- Hypothesis and experiment tracking
- Performance metrics visualization
- Budget allocation comparison tool
- Refresh action clears only the currently selected session

### 2. Backend (`/backend`)

**Technology Stack:**

- FastAPI (async web framework)
- Python 3.11+
- LangGraph (agent orchestration)
- OpenAI Python SDK
- Pydantic (data validation)
- Uvicorn (ASGI server)

**Directory Structure:**

```
backend/
├── app/
│   ├── main.py              # FastAPI app initialization
│   ├── config.py            # Environment configuration
│   ├── api/
│   │   └── routes_aria.py   # REST API endpoints
│   ├── core/
│   │   ├── models.py        # Pydantic data models
│   │   └── runtime.py       # InMemoryRuntime state manager
│   ├── orchestration/
│   │   └── graph.py         # LangGraph agent workflow
│   └── ws/
│       └── live_feed.py     # WebSocket event broadcaster
└── requirements.txt         # Python dependencies
```

### 3. State Management (`InMemoryRuntime`)

**Location:** `backend/app/core/runtime.py`

**Responsibilities:**

- Maintain multiple `ARIAState` sessions in memory (`run_id -> ARIAState`)
- Track and switch active session
- Thread-safe state updates via `asyncio.Lock`
- Event publishing to WebSocket subscribers
- OpenAI-powered strategy seed generation during initialization

**Key Methods:**

- `init_run(request: InitRequest)` - Initialize new ARIA run with AI-generated strategy
- `list_sessions()` - List available sessions with metadata (run_id, iteration, active flag)
- `set_active_run(run_id)` - Make a session active
- `get_state(run_id: str | None = None)` - Retrieve active or specific session state
- `clear_state(run_id: str | None = None)` - Clear a specific session (or active session)
- `patch_state(run_id: str | None = None, **kwargs)` - Apply partial state updates
- `publish_event(event: AgentEvent)` - Broadcast event to live feed

**State Schema:**

```python
class ARIAState(BaseModel):
    run_id: str                          # Unique run identifier
    iteration: int                       # Current iteration number
    brand: BrandInput                    # Brand configuration
    memory: SharedMemory                 # Shared agent memory
    hypotheses: list[Hypothesis]         # Active hypotheses
    experiments: list[Experiment]        # Running experiments
    performance_history: list[...]       # Historical metrics
    budget_plan: dict                    # Budget allocation
    agent_states: dict[AgentName, AgentState]  # Agent statuses
    evaluation: EvaluationVerdict | None # Latest evaluation
    paused: bool                         # Pause flag
    events: list[AgentEvent]             # Event log
```

### 4. Agent Orchestration (`LangGraph`)

**Location:** `backend/app/orchestration/graph.py`

**Graph Structure:**

```
START
  ↓
observe_signals (market/competitor analysis)
  ↓
growth_strategist_agent (hypothesis generation)
  ↓
creative_generation_agent (ad creative)
  ↓
audience_optimization_agent (targeting)
  ↓
budget_allocation_agent (budget distribution)
  ↓
composio_execution_layer (campaign launch)
  ↓
experiment_evaluation_agent (performance analysis)
  ↓
route_after_eval (conditional routing)
  ├─→ KILL_AND_RERUN → strategist (restart)
  ├─→ SCALE_WINNER → budget_allocation (scale)
  ├─→ INCONCLUSIVE → strategist (continue)
  └─→ COMPLETE → write_to_shared_memory
       ↓
     slack_notification
       ↓
      END
```

**Agent Descriptions:**

1. **observe_signals** (`AgentName.OBSERVE`)
   - Analyzes market trends, competitor activity, platform changes
   - Uses OpenAI to generate insights from brand context
   - Updates shared memory with observations

2. **growth_strategist_agent** (`AgentName.STRATEGIST`)
   - Generates testable hypotheses based on observations
   - Creates experiment plans with success criteria
   - Role: "Staff marketing and strategy lead"

3. **creative_generation_agent** (`AgentName.CREATIVE`)
   - Produces ad creative variations (copy, visuals, CTAs)
   - Aligns with brand voice and hypothesis
   - Generates multiple variants for testing

4. **audience_optimization_agent** (`AgentName.AUDIENCE`)
   - Refines targeting parameters
   - Identifies high-value audience segments
   - Optimizes demographic/interest targeting

5. **budget_allocation_agent** (`AgentName.BUDGET`)
   - Distributes budget across platforms and experiments
   - Balances exploration vs exploitation
   - Adjusts based on performance signals

6. **composio_execution_layer** (`AgentName.EXECUTE`)
   - Interfaces with ad platform APIs
   - Launches campaigns on Google/Meta/TikTok
   - Monitors execution status

7. **experiment_evaluation_agent** (`AgentName.EVALUATE`)
   - Analyzes experiment results
   - Determines statistical significance
   - Recommends next action (kill/scale/continue)

8. **write_to_shared_memory** (`AgentName.LEARN`)
   - Persists learnings to shared memory
   - Updates performance history
   - Refines brand DNA based on results

9. **slack_notification** (`AgentName.NOTIFY`)
   - Sends alerts to stakeholders
   - Reports key milestones and decisions

**State Merging:**
Each agent returns a partial state update that is merged with the current state using the `_merge_state` helper to prevent key loss during graph execution.

## API Surface

### Session Routing Rules

- All stateful REST endpoints can target a specific session via either:
  - `X-Run-Id` request header, or
  - `?run_id=<run_id>` query parameter
- If neither is provided, backend uses the active session.
- `POST /aria/reset` clears only the targeted session (not all sessions).

### REST Endpoints

#### `GET /aria/sessions`

List all in-memory sessions.

#### `POST /aria/sessions/{run_id}/activate`

Set the active session.

#### `DELETE /aria/sessions/{run_id}`

Delete one session by run ID.

#### `POST /aria/init`

Initialize a new ARIA run with brand configuration.

**Request:**

```json
{
  "url": "https://brand.com",
  "goal": "purchases",
  "budget_daily": 1000,
  "business_type": "B2C",
  "brand_name": "Brand Name"
}
```

**Response:**

```json
{
  "run_id": "run_xxxxxxxx",
  "message": "ARIA initialized"
}
```

**Behavior:**

- Calls OpenAI to generate initial strategy seed (product info, platform context, audience, generations, performance history)
- Creates `ARIAState` with seeded `SharedMemory`
- Publishes initialization event
- **Critical**: Must be called before any other endpoints

#### `GET /aria/status`

Retrieve current run status and agent states.

**Response:**

```json
{
  "run_id": "uuid",
  "iteration": 5,
  "paused": false,
  "goal": "purchases",
  "budget_daily": 1000,
  "agent_states": {
    "observe": { "status": "idle", "last_action": "..." },
    "strategist": { "status": "thinking", "last_action": "..." }
  }
}
```

#### `GET /aria/memory`

Fetch shared memory (brand DNA, audience, creatives, etc.).

**Response:**

```json
{
  "brand_dna": {...},
  "production_information": {...},
  "platform_context": {...},
  "target_audience": {...},
  "generations": [...],
  "performance_history": [...]
}
```

#### `GET /aria/strategy`

Get focused strategy snapshot (product, platform, audience).

**Response:**

```json
{
  "production_information": {
    "product_name": "...",
    "product_category": "...",
    "offer_summary": "...",
    "price_point": "...",
    "brand_url": "..."
  },
  "platform": {
    "channels": ["webads", "images", "videos"],
    "images_required": 5,
    "videos_required": 2
  },
  "target_audience": {...}
}
```

**Note:** Returns 404 if the targeted session is not initialized.

#### `GET /aria/hypotheses`

List active hypotheses.

**Response:**

```json
[
  {
    "hypothesis_id": "hyp_xxxxxxxx",
    "statement": "...",
    "rationale": "...",
    "confidence": 0.82,
    "success_metric": "roas",
    "target_lift_percent": 15.0,
    "priority": 1
  }
]
```

#### `GET /aria/experiments`

List running experiments.

**Response:**

```json
[
  {
    "experiment_id": "exp_xxxxxxxx",
    "hypothesis_id": "hyp_xxxxxxxx",
    "status": "running",
    "channels": ["meta", "google"],
    "metrics": {
      "impressions": 0,
      "clicks": 0,
      "spend": 0.0,
      "conversions": 0,
      "roas": 0.0,
      "cpa": 0.0,
      "ctr": 0.0,
      "cvr": 0.0
    }
  }
]
```

#### `GET /aria/performance`

Get performance metrics.

**Response:**

```json
{
  "unified_roas": 3.2,
  "meta_roas": 3.5,
  "google_roas": 2.9,
  "cpa": 25.5,
  "ctr": 0.035,
  "cvr": 0.028
}
```

#### `POST /aria/step`

Execute one full agent cycle (all agents sequentially).

**Response:**

```json
{
  "run_id": "uuid",
  "iteration": 6,
  "hypotheses": [...],
  "evaluation": {...}
}
```

**Behavior:**

- Runs `build_aria_graph()` and invokes all agents
- Updates state with results
- Publishes events for each agent action
- Returns updated hypotheses and evaluation

#### `POST /aria/pause`

Pause ARIA execution.

**Request:**

```json
{
  "reason": "Manual intervention required"
}
```

#### `POST /aria/reset`

Clear one session.

**Behavior:**

- Clears targeted session (`X-Run-Id` / `run_id` / active session)
- If other sessions remain, they are preserved
- If no sessions remain, runtime event queue is drained

#### `PATCH /aria/memory`

Update shared memory fields.

**Request:**

```json
{
  "brand_dna": {...},
  "target_audience": {...}
}
```

#### `POST /aria/compare`

**NEW:** Platform comparison with OpenAI analysis.

**Request:**

```json
{
  "total_budget": 1000,
  "goal": "purchases",
  "allocations": [
    { "platform": "google", "percentage": 40 },
    { "platform": "meta", "percentage": 40 },
    { "platform": "tiktok", "percentage": 20 }
  ]
}
```

**Response:**

```json
{
  "total_budget": 1000,
  "platform_metrics": [
    {
      "platform": "google",
      "estimated_reach": 50000,
      "estimated_cpa": 25.50,
      "estimated_ctr": 0.035,
      "estimated_cvr": 0.028,
      "audience_fit_score": 0.85,
      "creative_format_score": 0.78,
      "competitive_intensity": "high",
      "recommendation": "..."
    }
  ],
  "overall_recommendation": "...",
  "risk_assessment": "...",
  "optimization_tips": [...]
}
```

**Behavior:**

- Validates allocations sum to 100%
- Requires initialized ARIA state for context
- Calls OpenAI GPT-4o with brand/audience/product context
- Returns AI-generated platform analysis

#### `POST /aria/compare/save`

Persist a human-selected platform allocation to shared memory (`strategy_memory.human_decisions`).

### WebSocket Endpoint

#### `WS /aria/live`

Real-time event stream.

**Connection:**

```javascript
const ws = new WebSocket("ws://localhost:8000/aria/live");
// Optional session scoping:
// const ws = new WebSocket('ws://localhost:8000/aria/live?run_id=run_xxxxxxxx');
ws.onmessage = (event) => {
  const agentEvent = JSON.parse(event.data);
  // { run_id, iteration, agent, action, reason, confidence, diff }
};
```

**Behavior:**

- On connect: sends last 50 events from the selected session
- On agent action: broadcasts new event to all connected clients
- Auto-reconnect on disconnect

## Data Flow

### Initialization Flow

```
User → POST /aria/init
  ↓
InMemoryRuntime.init_run()
  ↓
OpenAI API (generate strategy seed)
  ↓
Create ARIAState with:
  - BrandInput (url, goal, budget)
  - SharedMemory (seeded with AI-generated data)
  - Empty hypotheses/experiments
  - Idle agent states
  ↓
Publish "init" event
  ↓
Return InitResponse
```

### Agent Execution Flow

```
User → POST /aria/step
  ↓
build_aria_graph()
  ↓
LangGraph invokes agents sequentially:
  1. observe_signals
     - OpenAI call with brand context
     - Returns observations
     - Publishes event
  2. growth_strategist_agent
     - OpenAI call with observations
     - Generates hypotheses
     - Publishes event
  3. creative_generation_agent
     - OpenAI call with hypothesis
     - Creates ad variants
     - Publishes event
  4. audience_optimization_agent
     - Refines targeting
     - Publishes event
  5. budget_allocation_agent
     - Distributes budget
     - Publishes event
  6. composio_execution_layer
     - Launches campaigns
     - Publishes event
  7. experiment_evaluation_agent
     - Analyzes results
     - Determines route
     - Publishes event
  8. Conditional routing:
     - KILL_AND_RERUN → restart from strategist
     - SCALE_WINNER → adjust budget
     - INCONCLUSIVE → continue iteration
     - COMPLETE → finalize
  9. write_to_shared_memory
     - Persist learnings
     - Publishes event
  10. slack_notification
     - Send alerts
     - Publishes event
  ↓
Update InMemoryRuntime state
  ↓
Return updated state
```

### Platform Comparison Flow

```
User → POST /aria/compare
  ↓
Validate allocations sum to 100%
  ↓
Fetch ARIAState (brand, audience, product)
  ↓
Build OpenAI prompt with:
  - Brand context
  - Campaign goal
  - Budget allocations
  - Target audience
  - Product info
  ↓
OpenAI API (GPT-4o, JSON mode)
  ↓
Parse response into PlatformMetrics
  ↓
Return ComparisonResponse
```

## Specific Workflows

### Workflow 1: First-Time Campaign Setup

**User Goal:** Launch first ARIA-managed campaign

**Steps:**

1. **Initialize ARIA**

   ```bash
   POST /aria/init
   {
     "url": "https://mybrand.com",
     "goal": "purchases",
     "budget_daily": 500,
     "business_type": "B2C",
     "brand_name": "MyBrand"
   }
   ```

   - Backend calls OpenAI to analyze brand website
   - Generates initial product info, platform context, target audience
   - Seeds shared memory with AI insights

2. **Review Strategy**

   ```bash
   GET /aria/strategy
   ```

   - User reviews AI-generated product description, audience, platform recommendations
   - Can manually adjust via `PATCH /aria/memory` if needed

3. **Run Platform Comparison** (Optional)
   - Navigate to `/compare` in frontend
   - Set budget to $500
   - Adjust allocations (e.g., 50% Meta, 30% Google, 20% TikTok)
   - Click "Run AI Comparison"
   - Review platform-specific recommendations
   - Adjust allocations based on insights

4. **Execute First Cycle**

   ```bash
   POST /aria/step
   ```

   - Agents run sequentially:
     - Observe: Analyze market signals
     - Strategist: Generate hypothesis (e.g., "Video ads outperform static on Meta")
     - Creative: Create video + static variants
     - Audience: Target 25-34 female, fitness interest
     - Budget: Allocate $250 to video, $250 to static
     - Execute: Launch campaigns via Composio
     - Evaluate: Monitor for 24-48 hours
   - Frontend live feed shows real-time agent actions

5. **Monitor Progress**
   - WebSocket `/aria/live` streams events
   - Dashboard shows:
     - Agent statuses (thinking/running/idle)
     - Active hypotheses
     - Running experiments
     - Performance metrics

6. **Iterate**
   - After evaluation period, call `POST /aria/step` again
   - Evaluation agent determines outcome:
     - If video wins: Scale budget to video
     - If inconclusive: Continue testing
     - If both fail: Kill and generate new hypothesis

### Workflow 2: Budget Reallocation Based on Performance

**User Goal:** Shift budget from underperforming to winning platform

**Steps:**

1. **Check Current Performance**

   ```bash
   GET /aria/performance
   ```

   - Review ROAS by platform:
     - Meta: 4.2
     - Google: 2.1
     - TikTok: 1.8

2. **Run Comparison Analysis**
   - Navigate to `/compare`
   - Current allocation: 33/33/33
   - Proposed allocation: 50/30/20 (favor Meta)
   - Run AI comparison
   - Review risk assessment and optimization tips

3. **Update Memory** (if needed)

   ```bash
   PATCH /aria/memory
   {
     "platform_context": {
       "primary_platform": "meta",
       "secondary_platforms": ["google"]
     }
   }
   ```

4. **Execute Reallocation Cycle**

   ```bash
   POST /aria/step
   ```

   - Budget agent adjusts allocation based on performance
   - Execute agent updates campaigns
   - Evaluation agent monitors new allocation

5. **Monitor Impact**
   - Track unified ROAS over next 7 days
   - Compare to baseline

### Workflow 3: Hypothesis Testing

**User Goal:** Test specific marketing hypothesis

**Steps:**

1. **Manual Hypothesis Injection** (via memory patch)

   ```bash
   PATCH /aria/memory
   {
     "custom_hypothesis": "Urgency-driven copy (24hr sale) increases CVR by 20%"
   }
   ```

2. **Run Agent Cycle**

   ```bash
   POST /aria/step
   ```

   - Strategist incorporates custom hypothesis
   - Creative generates urgency variants
   - Audience targets high-intent segments
   - Execute launches A/B test

3. **Review Experiments**

   ```bash
   GET /aria/experiments
   ```

   - Check experiment status
   - View variant performance

4. **Evaluate Results**
   - Wait for statistical significance
   - Next `POST /aria/step` triggers evaluation
   - Evaluation agent determines outcome:
     - CONFIRMED: Scale urgency copy
     - REJECTED: Revert to evergreen copy
     - INCONCLUSIVE: Extend test duration

5. **Check Learnings**

   ```bash
   GET /aria/memory
   ```

   - Review updated `performance_history`
   - See confirmed/rejected hypotheses

### Workflow 4: Deployment to Production

**User Goal:** Deploy ARIA to Vercel (frontend) and Render (backend)

**Steps:**

1. **Backend Deployment (Render/Railway/Fly)**
   - Create new web service
   - Connect GitHub repo
   - Set environment variables:
     - `OPENAI_API_KEY=sk-...`
   - Set build command: `pip install -r backend/requirements.txt`
   - Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend`
   - Deploy
   - Note backend URL: `https://aria-backend.onrender.com`

2. **Frontend Deployment (Vercel)**
   - Import repo in Vercel dashboard
   - Set environment variable:
     - `VITE_API_BASE=https://aria-backend.onrender.com`
   - Deploy
   - Vercel auto-detects Vite config from `vercel.json`

3. **Post-Deployment Initialization**

   ```bash
   curl -X POST https://aria-backend.onrender.com/aria/init \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://mybrand.com",
       "goal": "purchases",
       "budget_daily": 1000,
       "business_type": "B2C",
       "brand_name": "MyBrand"
     }'
   ```

   - **Critical**: Backend state is in-memory
   - After restart/redeploy, must re-initialize via `POST /aria/init`

4. **Access Frontend**
   - Visit `https://aria-xyz.vercel.app`
   - Click "Initialize" to start new run
   - Use platform comparison at `/compare`

### Workflow 5: Multi-Session Operations

**User Goal:** Run and compare multiple ARIA sessions in parallel.

**Steps:**

1. **Create sessions**
   - Initialize session A via `POST /aria/init`
   - Initialize session B via `POST /aria/init`

2. **List available sessions**

   ```bash
   GET /aria/sessions
   ```

3. **Switch active session**

   ```bash
   POST /aria/sessions/{run_id}/activate
   ```

   - Frontend also sets `X-Run-Id` automatically after selection.

4. **Run cycle on selected session**

   ```bash
   POST /aria/step
   ```

   - Targets selected run via `X-Run-Id` or `?run_id=`.

5. **Clear or delete a session**
   ```bash
   POST /aria/reset           # clear selected session
   DELETE /aria/sessions/{run_id}
   ```

## Configuration

### Environment Variables

**Backend:**

- `OPENAI_API_KEY` - OpenAI API key (required)
- `PORT` - Server port (default: 8000)

**Frontend:**

- `VITE_API_BASE` - Backend API URL (e.g., `https://aria-backend.onrender.com`)

### Files

- `backend/app/config.py` - Backend configuration
- `frontend/.env.example` - Frontend env template
- `vercel.json` - Vercel deployment config
- `render.yaml` - Render deployment config

## Deployment Architecture

### Development

```
Frontend: http://localhost:5173
Backend: http://127.0.0.1:8000
```

### Production (Recommended)

```
Frontend: Vercel (static hosting, CDN, auto-scaling)
Backend: Render/Railway/Fly (stateful service, persistent process)
```

**Why Separate Hosting:**

- Frontend is stateless, benefits from CDN
- Backend is stateful (in-memory runtime), needs persistent process
- Backend has WebSocket connections, not ideal for serverless
- Allows independent scaling

## State Persistence

**Current:** In-memory only (volatile)

- State lost on backend restart
- Must re-initialize sessions after deployment
- Multiple sessions are supported in-memory during a process lifetime

**Future Enhancements:**

- PostgreSQL for state persistence
- Redis for event caching
- S3 for creative asset storage

## Security Considerations

1. **API Key Management**
   - Never commit `OPENAI_API_KEY` to git
   - Use environment variables only
   - Rotate keys regularly

2. **CORS Configuration**
   - Backend allows all origins in development
   - Restrict to frontend domain in production

3. **Input Validation**
   - All endpoints use Pydantic models
   - Budget constraints enforced (> 0)
   - URL validation via `HttpUrl` type

4. **Rate Limiting**
   - Not currently implemented
   - Recommended: Add rate limiting middleware for production

## Performance Characteristics

- **Initialization:** ~3-5 seconds (OpenAI API call)
- **Agent Cycle:** ~10-20 seconds (multiple OpenAI calls)
- **Platform Comparison:** ~5-8 seconds (single OpenAI call)
- **WebSocket Latency:** <100ms (local broadcast)

## Error Handling

- **Uninitialized State:** Returns 404 for stateful endpoints requiring existing session (`/aria/step`, `/aria/memory` patch, etc.)
- **Status Before Init:** `GET /aria/status` returns a default `uninitialized` payload
- **OpenAI Failures:** Returns 500 with error details
- **Invalid Allocations:** Returns 400 with validation error
- **WebSocket Disconnect:** Auto-cleanup, no memory leak

## Testing Strategy

**Unit Tests:** (Not yet implemented)

- Test individual agent functions
- Mock OpenAI responses
- Validate state merging logic

**Integration Tests:** (Not yet implemented)

- Test full agent cycles
- Verify event publishing
- Check state consistency

**Manual Testing:**

- Initialize ARIA with test brand
- Run multiple cycles
- Verify event stream
- Test platform comparison
- Check memory updates

## Future Roadmap

1. **State Persistence**
   - PostgreSQL backend
   - State snapshots
   - Historical run tracking

2. **Advanced Visualization**
   - 3D platform comparison
   - Performance trend charts
   - Hypothesis success rates

3. **Multi-Tenant Support**
   - User authentication
   - Multiple concurrent runs (basic in-memory session management is now implemented)
   - Team collaboration

4. **Enhanced AI**
   - Fine-tuned models for ad copy
   - Image generation integration
   - Predictive budget optimization

5. **Platform Expansion**
   - LinkedIn Ads
   - Twitter/X Ads
   - Snapchat Ads

6. **Automation**
   - Scheduled agent cycles
   - Auto-scaling based on performance
   - Anomaly detection and alerts

## Glossary

- **ARIA:** Autonomous Revenue Intelligence Agent
- **LangGraph:** Framework for building stateful agent workflows
- **Hypothesis:** Testable marketing assumption
- **Experiment:** A/B test validating a hypothesis
- **Agent:** Specialized AI component (observe, strategist, creative, etc.)
- **Shared Memory:** Persistent knowledge base across agents
- **ROAS:** Return on Ad Spend
- **CPA:** Cost Per Acquisition
- **CTR:** Click-Through Rate
- **CVR:** Conversion Rate

## References

- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **OpenAI API:** https://platform.openai.com/docs/api-reference
- **Vercel Deployment:** https://vercel.com/docs
- **Render Deployment:** https://render.com/docs
