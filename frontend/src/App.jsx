import { useEffect, useMemo, useRef, useState } from "react";

import { apiBase, ariaApi } from "./api";

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
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");

  const [patchInput, setPatchInput] = useState({
    product_name: "",
    primary_segment: "",
    copies_per_cycle: 5,
    images_required: 5,
    videos_required: 2,
  });

  const keepaliveRef = useRef(null);

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

  async function refreshAll() {
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

  async function withLoader(task, successMessage) {
    try {
      setLoading(true);
      await task();
      if (successMessage) setToast(successMessage);
      await refreshAll();
    } catch (error) {
      setToast(`Error: ${String(error.message || error)}`);
    } finally {
      setLoading(false);
    }
  }

  function connectLiveFeed() {
    const ws = new WebSocket(`${wsBase}/aria/live`);

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        setEvents((prev) => [parsed, ...prev].slice(0, 120));
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
      setTimeout(connectLiveFeed, 1500);
    };
  }

  useEffect(() => {
    connectLiveFeed();
  }, []);

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
        <button disabled={loading} onClick={() => withLoader(() => ariaApi.init(initialInitPayload), "Run initialized")}>Initialize</button>
        <button disabled={loading} onClick={() => withLoader(() => ariaApi.step(), "Cycle executed")}>Run 1 Cycle</button>
        <button disabled={loading} onClick={() => withLoader(() => ariaApi.pause("Paused from dashboard"), "Run paused")}>Emergency Pause</button>
        <button disabled={loading} onClick={() => withLoader(() => refreshAll(), "Refreshed")}>Refresh</button>
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
  return (
    <main className="grid">
      <article className="glass panel">
        <h2>Agent Status</h2>
        <div className="agent-grid">
          {Object.entries(status?.agent_states || {}).map(([agent, state]) => (
            <div key={agent} className="agent-card">
              <span>{agent}</span>
              <b>{state.status}</b>
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
