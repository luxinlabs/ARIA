import { useEffect, useMemo, useRef, useState } from "react";

import { apiBase, ariaApi, setActiveRunId } from "./api";

const wsBase = apiBase.replace("http", "ws");

const initialInitPayload = {
  url: "https://example.com",
  goal: "purchases",
  budget_daily: 500,
  business_type: "B2C",
  brand_name: "NovaSkin",
};

function safeValue(input, fallback = "--") {
  if (input === undefined || input === null || input === "") return fallback;
  return input;
}

export default function App() {
  const [mode, setMode] = useState("agent");
  const [status, setStatus] = useState(null);
  const [memory, setMemory] = useState(null);
  const [hypotheses, setHypotheses] = useState([]);
  const [experiments, setExperiments] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [events, setEvents] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");

  const [patchInput, setPatchInput] = useState({
    product_name: "",
    primary_segment: "",
    copies_per_cycle: 5,
    images_required: 5,
    videos_required: 2,
  });

  const [initInput, setInitInput] = useState({
    url: "https://example.com",
    goal: "purchases",
    budget_daily: 500,
    business_type: "B2C",
    brand_name: "NovaSkin",
  });

  const keepaliveRef = useRef(null);
  const reconnectRef = useRef(null);
  const wsRef = useRef(null);
  const seenEventIdsRef = useRef(new Set());

  const summaryStats = useMemo(() => {
    const confirmed = memory?.experiment_log?.filter((x) => x.result === "CONFIRMED").length || 0;
    const rejected = memory?.experiment_log?.filter((x) => x.result === "REJECTED").length || 0;
    const inconclusive = memory?.experiment_log?.filter((x) => x.result === "INCONCLUSIVE").length || 0;
    return {
      confirmed,
      rejected,
      inconclusive,
      patterns: memory?.experiment_log?.length || 0,
    };
  }, [memory]);

  async function refreshAll(preferredRunId) {
    const sessionsPayload = await ariaApi.sessions();
    const nextSessions = sessionsPayload?.sessions || [];
    setSessions(nextSessions);

    const activeSession = nextSessions.find((session) => session.is_active);
    const hasPreferred = preferredRunId && nextSessions.some((session) => session.run_id === preferredRunId);
    const hasSelected = selectedRunId && nextSessions.some((session) => session.run_id === selectedRunId);
    const effectiveRunId = hasPreferred
      ? preferredRunId
      : hasSelected
        ? selectedRunId
        : activeSession?.run_id || null;

    setActiveRunId(effectiveRunId);
    setSelectedRunId(effectiveRunId);

    const [nextStatus, nextMemory, nextHyp, nextExp, nextPerf] = await Promise.all([
      ariaApi.status(),
      ariaApi.memory(),
      ariaApi.hypotheses(),
      ariaApi.experiments(),
      ariaApi.performance(),
    ]);
    setStatus(nextStatus);
    setMemory(nextMemory);
    setHypotheses(nextHyp);
    setExperiments(nextExp);
    setPerformance(nextPerf);

    setPatchInput((prev) => ({
      ...prev,
      product_name: nextMemory?.production_information?.product_name || "",
      primary_segment: nextMemory?.target_audience?.primary_segment || "",
      copies_per_cycle: nextMemory?.generations?.copies_per_cycle || 5,
      images_required: nextMemory?.platform_context?.images_required || 5,
      videos_required: nextMemory?.platform_context?.videos_required || 2,
    }));
  }

  function initializeRun() {
    const budgetDaily = Number(initInput.budget_daily);
    if (!Number.isFinite(budgetDaily) || budgetDaily <= 0) {
      throw new Error("Daily budget must be greater than 0");
    }

    return ariaApi.init({
      ...initInput,
      budget_daily: budgetDaily,
    });
  }

  async function clearSession() {
    await ariaApi.reset();
    seenEventIdsRef.current.clear();
    setEvents([]);
  }

  async function switchSession(runId) {
    if (!runId) {
      setActiveRunId(null);
      setSelectedRunId(null);
      seenEventIdsRef.current.clear();
      setEvents([]);
      return;
    }
    await ariaApi.activateSession(runId);
    setActiveRunId(runId);
    setSelectedRunId(runId);
    seenEventIdsRef.current.clear();
    setEvents([]);
  }

  async function deleteCurrentSession() {
    if (!selectedRunId) return;
    await ariaApi.deleteSession(selectedRunId);
    setActiveRunId(null);
    setSelectedRunId(null);
    seenEventIdsRef.current.clear();
    setEvents([]);
  }

  async function withLoader(task, successMessage) {
    try {
      setLoading(true);
      const result = await task();
      if (successMessage) setToast(successMessage);
      await refreshAll(result?.run_id || null);
      return result;
    } catch (error) {
      setToast(`Error: ${String(error.message || error)}`);
    } finally {
      setLoading(false);
    }
  }

  function connectLiveFeed() {
    const wsUrl = selectedRunId
      ? `${wsBase}/aria/live?run_id=${encodeURIComponent(selectedRunId)}`
      : `${wsBase}/aria/live`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        if (selectedRunId && parsed?.run_id && parsed.run_id !== selectedRunId) return;
        const eventId = parsed?.event_id;
        if (eventId && seenEventIdsRef.current.has(eventId)) return;
        if (eventId) seenEventIdsRef.current.add(eventId);
        setEvents((prev) => [parsed, ...prev].slice(0, 120));
        
        // Update agent status in real-time
        if (parsed?.agent && parsed?.action) {
          setStatus((prevStatus) => {
            if (!prevStatus) return prevStatus;
            
            const newAgentStates = { ...prevStatus.agent_states };
            
            // Determine status based on action
            let newStatus = "running";
            
            if (parsed.action.includes("thinking") || parsed.action.includes("analyzing") || parsed.action.includes("generating")) {
              newStatus = "thinking";
            } else if (parsed.action.includes("waiting") || parsed.action.includes("pending")) {
              newStatus = "waiting";
            } else {
              // For completed actions, show running briefly then return to idle
              newStatus = "running";
              
              // Set all other agents to idle (only current agent is running)
              Object.keys(newAgentStates).forEach(agentName => {
                if (agentName !== parsed.agent) {
                  newAgentStates[agentName] = {
                    ...newAgentStates[agentName],
                    status: "idle"
                  };
                }
              });
            }
            
            newAgentStates[parsed.agent] = {
              status: newStatus,
              last_update: parsed.timestamp || new Date().toISOString()
            };
            
            return {
              ...prevStatus,
              agent_states: newAgentStates,
              iteration: parsed.iteration ?? prevStatus.iteration
            };
          });
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onopen = () => {
      keepaliveRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
      }, 12000);
    };

    ws.onclose = () => {
      if (keepaliveRef.current) clearInterval(keepaliveRef.current);
      reconnectRef.current = setTimeout(connectLiveFeed, 1500);
    };
  }

  useEffect(() => {
    connectLiveFeed();
    return () => {
      if (keepaliveRef.current) clearInterval(keepaliveRef.current);
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      if (wsRef.current && wsRef.current.readyState <= 1) wsRef.current.close();
    };
  }, [selectedRunId]);

  useEffect(() => {
    refreshAll().catch(() => {
      // allow app to load before init exists
    });
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3000);
    return () => clearTimeout(timer);
  }, [toast]);

  return (
    <div className="app-shell">
      <div className="aurora aurora-a" />
      <div className="aurora aurora-b" />

      <header className="topbar glass">
        <div>
          <p className="eyebrow">Autonomous Reasoning & Intelligence for Ads</p>
          <h1>ARIA Control Room</h1>
        </div>
        <div className="mode-switch">
          <button className={mode === "agent" ? "active" : ""} onClick={() => setMode("agent")}>Dashboard for Agent</button>
          <button className={mode === "customer" ? "active" : ""} onClick={() => setMode("customer")}>Dashboard for Customer</button>
        </div>
      </header>

      <section className="control-row glass">
        <div className="init-inputs">
          <select
            value={selectedRunId || ""}
            onChange={(e) => withLoader(() => switchSession(e.target.value || null), "Session switched")}
          >
            <option value="">Use active session</option>
            {sessions.map((session) => (
              <option key={session.run_id} value={session.run_id}>
                {session.brand_name || "Unnamed"} · {session.run_id.slice(0, 8)} · iter {session.iteration}
              </option>
            ))}
          </select>
          <input
            type="url"
            placeholder="Brand URL"
            value={initInput.url}
            onChange={(e) => setInitInput({ ...initInput, url: e.target.value })}
          />
          <select
            value={initInput.goal}
            onChange={(e) => setInitInput({ ...initInput, goal: e.target.value })}
          >
            <option value="purchases">Purchases</option>
            <option value="leads">Leads</option>
            <option value="signups">Signups</option>
            <option value="awareness">Awareness</option>
          </select>
          <input
            type="number"
            placeholder="Daily Budget"
            value={initInput.budget_daily}
            min="1"
            step="1"
            onChange={(e) => setInitInput({ ...initInput, budget_daily: e.target.value })}
          />
          <input
            type="text"
            placeholder="Brand Name"
            value={initInput.brand_name}
            onChange={(e) => setInitInput({ ...initInput, brand_name: e.target.value })}
          />
        </div>
        <button disabled={loading} onClick={() => withLoader(() => initializeRun(), "Run initialized")}>Initialize</button>
        <button disabled={loading} onClick={() => withLoader(() => ariaApi.step(), "Cycle executed")}>Run 1 Cycle</button>
        <button disabled={loading} onClick={() => withLoader(() => ariaApi.pause("Paused from dashboard"), "Run paused")}>Emergency Pause</button>
        <button disabled={loading || !selectedRunId} onClick={() => withLoader(() => deleteCurrentSession(), "Session deleted")}>Delete Session</button>
        <button disabled={loading} onClick={() => withLoader(() => clearSession(), "Session cleared")}>Refresh</button>
        <span className="status-pill">{status?.paused ? "PAUSED" : "LIVE"}</span>
      </section>

      {mode === "agent" ? (
        <AgentDashboard
          status={status}
          hypotheses={hypotheses}
          experiments={experiments}
          events={events}
          performance={performance}
          summaryStats={summaryStats}
        />
      ) : (
        <CustomerDashboard
          status={status}
          memory={memory}
          performance={performance}
          patchInput={patchInput}
          setPatchInput={setPatchInput}
          onPatch={() =>
            withLoader(
              () =>
                ariaApi.patchMemory({
                  production_information: {
                    product_name: patchInput.product_name,
                  },
                  target_audience: {
                    primary_segment: patchInput.primary_segment,
                  },
                  generations: {
                    copies_per_cycle: Number(patchInput.copies_per_cycle),
                  },
                  platform_context: {
                    images_required: Number(patchInput.images_required),
                    videos_required: Number(patchInput.videos_required),
                  },
                }),
              "Memory updated"
            )
          }
        />
      )}

      {toast ? <div className="toast">{toast}</div> : null}
    </div>
  );
}

function AgentDashboard({ status, hypotheses, experiments, events, performance, summaryStats }) {
  const getStatusColor = (status) => {
    switch (status) {
      case 'thinking': return '#f59e0b'; // amber
      case 'running': return '#10b981'; // green
      case 'waiting': return '#3b82f6'; // blue
      case 'idle': return '#6b7280'; // gray
      default: return '#6b7280';
    }
  };

  return (
    <main className="grid">
      <article className="glass panel">
        <h2>Agent Status</h2>
        <div className="agent-grid">
          {Object.entries(status?.agent_states || {}).map(([agent, state]) => (
            <div key={agent} className="agent-card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: getStatusColor(state.status),
                  animation: state.status !== 'idle' ? 'pulse 2s infinite' : 'none'
                }} />
                <span>{agent}</span>
              </div>
              <b style={{ color: getStatusColor(state.status) }}>{state.status}</b>
            </div>
          ))}
        </div>
      </article>

      <article className="glass panel">
        <h2>Loop Snapshot</h2>
        <div className="kpi-row">
          <Kpi label="Cycle" value={`#${safeValue(status?.iteration, 0)}`} />
          <Kpi label="ROAS" value={`${safeValue(performance?.unified_roas, 0)}x`} />
          <Kpi label="Confirmed" value={summaryStats.confirmed} />
          <Kpi label="Patterns" value={summaryStats.patterns} />
        </div>
      </article>

      <article className="glass panel span-2">
        <h2>Live Reasoning Feed</h2>
        <div className="feed">
          {events.length === 0 ? <p>No events yet. Initialize and run a cycle.</p> : null}
          {events.map((evt) => (
            <div key={evt.event_id} className="feed-line">
              <span>[{evt.agent}]</span>
              <p>{evt.reason}</p>
              <small>{new Date(evt.timestamp).toLocaleTimeString()}</small>
            </div>
          ))}
        </div>
      </article>

      <article className="glass panel">
        <h2>Hypotheses Queue</h2>
        <div className="list">
          {hypotheses.length === 0 ? <p>Run a cycle to generate hypotheses.</p> : null}
          {hypotheses.map((h) => (
            <div key={h.hypothesis_id} className="list-item">
              <p>{h.statement}</p>
              <small>conf {h.confidence}</small>
            </div>
          ))}
        </div>
      </article>

      <article className="glass panel">
        <h2>Experiments</h2>
        <div className="list">
          {experiments.length === 0 ? <p>No experiments yet.</p> : null}
          {experiments.map((exp) => (
            <div key={exp.experiment_id} className="list-item">
              <p>{exp.experiment_id}</p>
              <small>{exp.status}</small>
            </div>
          ))}
        </div>
      </article>
    </main>
  );
}

function CustomerDashboard({ status, memory, performance, patchInput, setPatchInput, onPatch }) {
  return (
    <main className="grid customer-grid">
      <article className="glass panel span-2">
        <h2>Business Overview</h2>
        <div className="kpi-row">
          <Kpi label="Brand" value={safeValue(memory?.production_information?.product_name)} />
          <Kpi label="Primary Segment" value={safeValue(memory?.target_audience?.primary_segment)} />
          <Kpi label="Unified ROAS" value={`${safeValue(performance?.unified_roas, 0)}x`} />
          <Kpi label="Paused" value={status?.paused ? "Yes" : "No"} />
        </div>
      </article>

      <article className="glass panel">
        <h2>Creative Capacity</h2>
        <div className="kpi-row vertical">
          <Kpi label="Copies / Cycle" value={safeValue(memory?.generations?.copies_per_cycle, 0)} />
          <Kpi label="Images Required" value={safeValue(memory?.platform_context?.images_required, 0)} />
          <Kpi label="Videos Required" value={safeValue(memory?.platform_context?.videos_required, 0)} />
          <Kpi label="Channels" value={(memory?.platform_context?.channels || []).join(", ")} />
        </div>
      </article>

      <article className="glass panel">
        <h2>Performance History</h2>
        <div className="list">
          {(memory?.performance_history?.platform_user_click_history || []).map((row) => (
            <div key={row.platform} className="list-item">
              <p>{row.platform.toUpperCase()}</p>
              <small>
                clicks: {row.user_clicks} · conversions: {row.paid_conversions} · conv rate: {row.conversion_rate}
              </small>
            </div>
          ))}
        </div>
      </article>

      <article className="glass panel span-2">
        <h2>Update Shared Intelligence Layer</h2>
        <p className="sub">This writes to PATCH /aria/memory.</p>
        <div className="form-grid">
          <label>
            Product Name
            <input
              value={patchInput.product_name}
              onChange={(e) => setPatchInput((p) => ({ ...p, product_name: e.target.value }))}
            />
          </label>
          <label>
            Primary Segment
            <input
              value={patchInput.primary_segment}
              onChange={(e) => setPatchInput((p) => ({ ...p, primary_segment: e.target.value }))}
            />
          </label>
          <label>
            Copies / Cycle
            <input
              type="number"
              min="1"
              value={patchInput.copies_per_cycle}
              onChange={(e) => setPatchInput((p) => ({ ...p, copies_per_cycle: e.target.value }))}
            />
          </label>
          <label>
            Images Required
            <input
              type="number"
              min="0"
              value={patchInput.images_required}
              onChange={(e) => setPatchInput((p) => ({ ...p, images_required: e.target.value }))}
            />
          </label>
          <label>
            Videos Required
            <input
              type="number"
              min="0"
              value={patchInput.videos_required}
              onChange={(e) => setPatchInput((p) => ({ ...p, videos_required: e.target.value }))}
            />
          </label>
        </div>
        <button className="primary" onClick={onPatch}>Save to Memory</button>
      </article>
    </main>
  );
}

function Kpi({ label, value }) {
  return (
    <div className="kpi">
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}
