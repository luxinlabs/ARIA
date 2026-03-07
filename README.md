# ARIA (Autonomous Reasoning & Intelligence for Ads)

ARIA is a FastAPI + LangGraph backend with a React dashboard frontend.

## Quick Start

### 1) Backend
From project root (`ARIA`):

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000 --app-dir backend
```

Backend URLs:
- API root: `http://127.0.0.1:8000/`
- OpenAPI docs: `http://127.0.0.1:8000/docs`

### 2) Frontend
In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:
- `http://localhost:5173` (or next available port)

---

## How to Use ARIA Dashboard

At the top control bar, fill:
- **Brand URL** (must be a valid URL)
- **Goal** (purchases/leads/signups/awareness)
- **Daily Budget** (**must be > 0**)
- **Brand Name**

Then click:
1. **Initialize**: creates a new ARIA run and seeds shared memory.
2. **Run 1 Cycle**: executes one full agent loop.
3. **Refresh**: reloads all current state.
4. **Emergency Pause**: pauses the run.

---

## What Happens After Initialization

When you click **Initialize** (`POST /aria/init`):
1. Backend creates `ARIAState` with your brand input.
2. Shared memory is seeded (production info, target audience, generations, performance history).
3. An initial event is emitted: `"ARIA run initialized"`.
4. Frontend refreshes:
   - `/aria/status`
   - `/aria/memory`
   - `/aria/hypotheses`
   - `/aria/experiments`
   - `/aria/performance`

No optimization cycle runs automatically on init; you trigger it with **Run 1 Cycle**.

---

## Why You Could See "ARIA run initialized" More Than Once

Two common sources:
1. **Toast + live event are separate UI surfaces**
   - Toast shows `Run initialized`
   - Live feed shows event reason `ARIA run initialized`
2. **Dev-mode duplicate websocket behavior (React StrictMode)**
   - React dev mode can mount/unmount effects twice
   - This can duplicate streamed events if not deduplicated

The frontend now deduplicates live-feed events by `event_id` and cleans websocket connections on unmount.

---

## Main API Endpoints

- `POST /aria/init`
- `POST /aria/step`
- `GET /aria/status`
- `GET /aria/memory`
- `PATCH /aria/memory`
- `GET /aria/hypotheses`
- `GET /aria/experiments`
- `GET /aria/performance`
- `POST /aria/pause`
- `GET /aria/learnings`
- `WS /aria/live`

---

## Troubleshooting

### `No module named 'app'`
Run backend from project root with `--app-dir backend`:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000 --app-dir backend
```

### Port 8000 already in use

```bash
lsof -ti:8000 | xargs kill -9
```

### `422` on `/aria/init` (`budget_daily`)
Ensure **Daily Budget > 0**.

### Security note
Do not hardcode API keys in source files. Prefer environment variables (e.g., `OPENAI_API_KEY`).
